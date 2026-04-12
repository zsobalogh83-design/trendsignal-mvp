"""
Retroactive sentiment score recalculation
==========================================
Recalculates sentiment_score for all signals where sentiment_score = 0.0,
using the news items that were available at the time of signal generation.

Three phases:
  Phase 0 – Re-score news_items with active_score=0 using FinBERT
             (only where finbert_score and sentiment_score are also 0)
  Phase 1 – Recalculate sentiment for `signals` table (live signals)
  Phase 2 – Recalculate sentiment for `archive_signals` table

Key design decisions:
  - Decay is calculated relative to the signal's own timestamp (not now),
    so historical news gets the correct weight it had at generation time.
  - Lookback window: 48h before signal timestamp (collect_news used 24h,
    but 48h is safer to catch any news that arrived slightly before collection).
  - Only news published within 24h before signal time gets non-zero decay weight
    (matching the original decay config: >24h → 0.0).
  - active_score priority: active_score → finbert_score → sentiment_score → FinBERT re-run
  - archive_news_items credibility defaults to 0.8 (no FK to news_sources).

Usage:
    python one_offs/recalc_sentiment_scores.py [--dry-run] [--phase 0|1|2|all]
    python one_offs/recalc_sentiment_scores.py --phase all
    python one_offs/recalc_sentiment_scores.py --dry-run --phase 1
"""

import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal
from sqlalchemy import text

# ──────────────────────────────────────────────────────────────────────────────
# Config – decay / duration weights (matches config.json + signal_generator defaults)
# ──────────────────────────────────────────────────────────────────────────────

def _load_weights() -> tuple[dict, dict]:
    """Load decay and duration weights from config.json (with hardcoded fallback)."""
    try:
        import json
        cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        with open(cfg_path) as f:
            cfg = json.load(f)
        decay = cfg.get('DECAY_WEIGHTS', cfg.get('decay_weights', None))
    except Exception:
        decay = None

    if not decay:
        decay = {'0-2h': 1.0, '2-6h': 0.57, '6-12h': 0.25, '12-24h': 0.24}

    duration = {'hours': 0.6, 'days': 1.0, 'weeks': 1.4, 'permanent': 1.8}
    return decay, duration


DECAY_WEIGHTS, DURATION_WEIGHTS = _load_weights()


# ──────────────────────────────────────────────────────────────────────────────
# Core aggregation (time-relative version)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NewsRow:
    """Lightweight news item for aggregation."""
    published_at: datetime
    active_score: float
    sentiment_confidence: float
    credibility: float
    llm_impact_duration: Optional[str]


def _decay(age_hours: float) -> float:
    dw = DECAY_WEIGHTS
    if age_hours < 2:
        return dw.get('0-2h', 1.0)
    elif age_hours < 6:
        return dw.get('2-6h', 0.57)
    elif age_hours < 12:
        return dw.get('6-12h', 0.25)
    elif age_hours < 24:
        return dw.get('12-24h', 0.24)
    else:
        return 0.0  # excluded – same as original logic


def aggregate(news_rows: List[NewsRow], reference_time: datetime) -> Dict[str, Any]:
    """
    Aggregate sentiment scores relative to reference_time (signal generation time).
    Mirrors the logic in signal_generator.aggregate_sentiment_from_news().
    """
    if not news_rows:
        return {'weighted_avg': 0.0, 'confidence': 0.5, 'news_count': 0}

    ref = reference_time
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)

    weighted_scores = []
    weights_sum = 0.0
    confidences = []

    for row in news_rows:
        pub = row.published_at
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)

        age_hours = (ref - pub).total_seconds() / 3600.0
        if age_hours < 0:
            age_hours = 0.0  # future-published news (clock skew) gets full weight

        d = _decay(age_hours)
        if d == 0.0:
            continue  # outside 24h window

        dur = DURATION_WEIGHTS.get(row.llm_impact_duration or 'days', 1.0)
        weight = d * row.credibility * dur
        weighted_scores.append(row.active_score * weight)
        weights_sum += weight
        confidences.append(row.sentiment_confidence)

    if weights_sum == 0.0:
        return {'weighted_avg': 0.0, 'confidence': 0.5, 'news_count': len(news_rows)}

    weighted_avg = sum(weighted_scores) / weights_sum

    # Confidence
    finbert_conf = min((sum(confidences) / len(confidences)) * 0.85, 0.90) if confidences else 0.5
    vol = min(len(news_rows) / 10.0, 1.0)
    volume_factor = 0.40 + 0.60 * vol
    signs = [s for s in weighted_scores]
    pos = sum(1 for s in signs if s > 0)
    neg = sum(1 for s in signs if s < 0)
    majority = max(pos, neg)
    consistency = majority / len(signs) if signs else 0.5
    confidence = finbert_conf * 0.40 + volume_factor * 0.35 + consistency * 0.25

    return {
        'weighted_avg': weighted_avg,
        'confidence': min(confidence, 0.99),
        'news_count': len(news_rows),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Phase 0 – Re-score news_items with FinBERT
# ──────────────────────────────────────────────────────────────────────────────

def phase0_rescore_news_items(db, dry_run: bool = False):
    """Re-run FinBERT on news_items where active_score, finbert_score, sentiment_score are all 0."""
    print("\n" + "=" * 70)
    print("PHASE 0 – Re-score news_items with FinBERT")
    print("=" * 70)

    rows = db.execute(text("""
        SELECT id, title, description
        FROM news_items
        WHERE (active_score IS NULL OR active_score = 0.0)
          AND (finbert_score IS NULL OR finbert_score = 0.0)
          AND (sentiment_score IS NULL OR sentiment_score = 0.0)
          AND title IS NOT NULL AND title != ''
    """)).fetchall()

    print(f"  Items needing FinBERT re-score: {len(rows):,}")
    if not rows:
        print("  Nothing to do.")
        return 0

    # Load FinBERT
    try:
        from finbert_analyzer import get_global_finbert
        fb = get_global_finbert()
        print("  [OK] FinBERT loaded")
    except Exception as e:
        print(f"  [ERROR] FinBERT unavailable: {e}")
        print("  Skipping Phase 0 – news_items will use sentiment_score=0 as fallback")
        return 0

    updated = 0
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        for row_id, title, desc in batch:
            text_input = f"{title}. {desc or ''}".strip()
            try:
                result = fb.analyze(text_input[:512])
                score = result.get('score', 0.0)
                conf = result.get('confidence', 0.5)
                if not dry_run:
                    db.execute(text("""
                        UPDATE news_items
                        SET finbert_score = :score,
                            sentiment_score = :score,
                            sentiment_confidence = :conf,
                            active_score = :score,
                            active_score_source = 'finbert'
                        WHERE id = :id
                    """), {'score': score, 'conf': conf, 'id': row_id})
                updated += 1
            except Exception as e:
                pass  # leave as 0

        if not dry_run:
            db.commit()
        pct = min((i + batch_size) / len(rows) * 100, 100)
        print(f"  Progress: {min(i + batch_size, len(rows)):,}/{len(rows):,} ({pct:.0f}%)", end='\r')

    print(f"\n  [OK] Re-scored {updated:,} news_items" + (" (dry-run)" if dry_run else ""))
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1 – Recalculate sentiment for `signals` table
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_news_for_signal(db, ticker_symbol: str, ref_time: datetime) -> List[NewsRow]:
    """Fetch news_items for a ticker within 48h before ref_time via news_tickers junction."""
    cutoff = ref_time - timedelta(hours=48)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    rows = db.execute(text("""
        SELECT
            n.published_at,
            COALESCE(
                CASE WHEN n.active_score IS NOT NULL AND n.active_score != 0.0
                     THEN n.active_score ELSE NULL END,
                CASE WHEN n.finbert_score IS NOT NULL AND n.finbert_score != 0.0
                     THEN n.finbert_score ELSE NULL END,
                n.sentiment_score,
                0.0
            ) AS score,
            COALESCE(n.sentiment_confidence, 0.5) AS conf,
            COALESCE(s.credibility_weight, 0.8) AS cred,
            n.llm_impact_duration
        FROM news_items n
        JOIN news_tickers nt ON n.id = nt.news_id
        JOIN tickers t ON nt.ticker_id = t.id
        LEFT JOIN news_sources s ON n.source_id = s.id
        WHERE t.symbol = :sym
          AND n.published_at >= :cutoff
          AND n.published_at <= :ref
    """), {'sym': ticker_symbol, 'cutoff': cutoff, 'ref': ref_time}).fetchall()

    return [
        NewsRow(
            published_at=r[0] if isinstance(r[0], datetime) else datetime.fromisoformat(str(r[0])),
            active_score=float(r[1] or 0.0),
            sentiment_confidence=float(r[2] or 0.5),
            credibility=float(r[3] or 0.8),
            llm_impact_duration=r[4],
        )
        for r in rows
    ]


def phase1_recalc_signals(db, dry_run: bool = False):
    """Recalculate sentiment_score for signals table entries with sentiment_score = 0."""
    print("\n" + "=" * 70)
    print("PHASE 1 – Recalculate `signals` table")
    print("=" * 70)

    signals = db.execute(text("""
        SELECT id, ticker_symbol, created_at, status
        FROM signals
        WHERE sentiment_score = 0.0
        ORDER BY created_at DESC
    """)).fetchall()

    print(f"  Signals with sentiment=0: {len(signals):,}")
    if not signals:
        print("  Nothing to do.")
        return 0

    updated = 0
    skipped_no_news = 0

    for sig_id, ticker, created_at_raw, status in signals:
        created_at = created_at_raw
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        news = _fetch_news_for_signal(db, ticker, created_at)
        result = aggregate(news, created_at)
        weighted_avg = result['weighted_avg']
        confidence = result['confidence']

        if weighted_avg == 0.0 and not news:
            skipped_no_news += 1
            continue

        sentiment_score = weighted_avg * 100.0  # scale to -100..+100

        if not dry_run:
            db.execute(text("""
                UPDATE signals
                SET sentiment_score = :score,
                    sentiment_confidence = :conf
                WHERE id = :id
            """), {'score': sentiment_score, 'conf': confidence, 'id': sig_id})

        updated += 1

    if not dry_run:
        db.commit()

    print(f"  Updated:          {updated:,}" + (" (dry-run)" if dry_run else ""))
    print(f"  Skipped (no news):{skipped_no_news:,}")
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 – Recalculate sentiment for `archive_signals` table
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_archive_news(db, ticker_symbol: str, ref_time: datetime) -> List[NewsRow]:
    """Fetch archive_news_items for a ticker within 48h before ref_time."""
    cutoff = ref_time - timedelta(hours=48)

    rows = db.execute(text("""
        SELECT
            published_at,
            COALESCE(
                CASE WHEN active_score IS NOT NULL AND active_score != 0.0
                     THEN active_score ELSE NULL END,
                CASE WHEN finbert_score IS NOT NULL AND finbert_score != 0.0
                     THEN finbert_score ELSE NULL END,
                overall_sentiment_score,
                0.0
            ) AS score,
            COALESCE(sentiment_confidence, 0.5) AS conf,
            0.8 AS cred,
            llm_impact_duration
        FROM archive_news_items
        WHERE ticker_symbol = :sym
          AND published_at >= :cutoff
          AND published_at <= :ref
    """), {'sym': ticker_symbol, 'cutoff': cutoff, 'ref': ref_time}).fetchall()

    result = []
    for r in rows:
        pub = r[0]
        if isinstance(pub, str):
            pub = datetime.fromisoformat(pub)
        if pub and pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub:
            result.append(NewsRow(
                published_at=pub,
                active_score=float(r[1] or 0.0),
                sentiment_confidence=float(r[2] or 0.5),
                credibility=float(r[3] or 0.8),
                llm_impact_duration=r[4],
            ))
    return result


def phase2_recalc_archive_signals(db, dry_run: bool = False):
    """Recalculate sentiment_score for archive_signals with sentiment_score = 0."""
    print("\n" + "=" * 70)
    print("PHASE 2 – Recalculate `archive_signals` table")
    print("=" * 70)

    signals = db.execute(text("""
        SELECT id, ticker_symbol, signal_timestamp
        FROM archive_signals
        WHERE sentiment_score = 0.0
        ORDER BY signal_timestamp DESC
    """)).fetchall()

    print(f"  Archive signals with sentiment=0: {len(signals):,}")
    if not signals:
        print("  Nothing to do.")
        return 0

    updated = 0
    skipped_no_news = 0
    batch_size = 500

    for i, (sig_id, ticker, ts_raw) in enumerate(signals):
        ts = ts_raw
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        news = _fetch_archive_news(db, ticker, ts)
        result = aggregate(news, ts)
        weighted_avg = result['weighted_avg']
        confidence = result['confidence']

        if weighted_avg == 0.0 and not news:
            skipped_no_news += 1
            continue

        sentiment_score = weighted_avg * 100.0

        if not dry_run:
            db.execute(text("""
                UPDATE archive_signals
                SET sentiment_score = :score,
                    sentiment_confidence = :conf
                WHERE id = :id
            """), {'score': sentiment_score, 'conf': confidence, 'id': sig_id})

        updated += 1

        # Commit in batches
        if not dry_run and (i + 1) % batch_size == 0:
            db.commit()
            print(f"  Progress: {i+1:,}/{len(signals):,} ({(i+1)/len(signals)*100:.0f}%)", end='\r')

    if not dry_run:
        db.commit()

    print(f"\n  Updated:          {updated:,}" + (" (dry-run)" if dry_run else ""))
    print(f"  Skipped (no news):{skipped_no_news:,}")
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Retroactive sentiment score recalculation')
    parser.add_argument('--dry-run', action='store_true',
                        help='Calculate but do not write to DB')
    parser.add_argument('--phase', default='all',
                        choices=['0', '1', '2', 'all'],
                        help='Which phase to run (default: all)')
    args = parser.parse_args()

    dry_run = args.dry_run
    phase = args.phase

    print("=" * 70)
    print("Retroactive Sentiment Score Recalculation")
    print(f"  dry-run: {dry_run}")
    print(f"  phase:   {phase}")
    print(f"  decay:   {DECAY_WEIGHTS}")
    print("=" * 70)

    db = SessionLocal()
    try:
        if phase in ('0', 'all'):
            phase0_rescore_news_items(db, dry_run)

        if phase in ('1', 'all'):
            phase1_recalc_signals(db, dry_run)

        if phase in ('2', 'all'):
            phase2_recalc_archive_signals(db, dry_run)

        # Final summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        s_total = db.execute(text("SELECT COUNT(*) FROM signals")).scalar()
        s_zero = db.execute(text("SELECT COUNT(*) FROM signals WHERE sentiment_score = 0.0")).scalar()
        a_total = db.execute(text("SELECT COUNT(*) FROM archive_signals")).scalar()
        a_zero = db.execute(text("SELECT COUNT(*) FROM archive_signals WHERE sentiment_score = 0.0")).scalar()
        print(f"  signals:         {s_total:>10,} total  |  sentiment=0: {s_zero:>6,} ({s_zero/s_total*100:.1f}%)")
        print(f"  archive_signals: {a_total:>10,} total  |  sentiment=0: {a_zero:>6,} ({a_zero/a_total*100:.1f}%)")
        if dry_run:
            print("\n  [DRY-RUN] No changes written to database.")

    finally:
        db.close()


if __name__ == '__main__':
    main()
