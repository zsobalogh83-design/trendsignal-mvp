"""
TrendSignal MVP - Signal Recalculation Script
Regenerates SL/TP/RR for all existing BUY/SELL signals using the CURRENT
_calculate_levels logic and updates both `signals` and `signal_calculations`.

Usage:
    python -m src.recalculate_signals
    python -m src.recalculate_signals --dry-run
    python -m src.recalculate_signals --ticker AAPL
    python -m src.recalculate_signals --status active
"""

import sys
import os
import io
import json
import argparse
from datetime import datetime, timezone

# Force UTF-8 output on Windows to avoid cp1250 encode errors
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import Signal, SignalCalculation
from src.signal_generator import (
    SignalGenerator, parse_support_resistance,
    calculate_sma_component_score,
    calculate_rsi_component_score,
    calculate_macd_component_score,
    calculate_bollinger_component_score,
    calculate_stochastic_component_score,
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _extract_old_rr_correction(signal: Signal) -> float:
    """Extract old R:R correction from reasoning_json (0 if not found)."""
    try:
        if signal.reasoning_json:
            r = json.loads(signal.reasoning_json)
            return float(r.get("rr_correction") or 0)
    except Exception:
        pass
    return 0.0


def _extract_old_alignment_bonus(signal: Signal) -> float:
    """Extract old alignment bonus from reasoning_json (0 if not found)."""
    try:
        if signal.reasoning_json:
            r = json.loads(signal.reasoning_json)
            return float(r.get("alignment_bonus") or 0)
    except Exception:
        pass
    return 0.0


def _update_reasoning_json(signal: Signal, new_sl: float, new_tp: float, new_rr: float,
                            sl_method: str, tp_method: str, new_score: float):
    """Patch reasoning_json with updated SL/TP/RR metadata and recalc timestamp."""
    try:
        if signal.reasoning_json:
            r = json.loads(signal.reasoning_json)
        else:
            r = {}

        # Update levels_meta
        r["levels_meta"] = {
            "sl_method": sl_method,
            "tp_method": tp_method,
            "recalculated_at": datetime.utcnow().isoformat()
        }
        # Update top-level combined_score
        r["combined_score"] = round(new_score, 2)

        # Update components/alignment if present
        if "components" in r and "alignment" in r.get("components", {}):
            r["components"]["alignment"]["rr_correction_new"] = None  # will be set below
            r["components"]["alignment"]["final_score"] = round(new_score, 2)

        signal.reasoning_json = json.dumps(r, default=str)
    except Exception as e:
        print(f"    ⚠️  Could not patch reasoning_json: {e}")


# ─────────────────────────────────────────────
# MAIN RECALCULATION
# ─────────────────────────────────────────────

def recalculate_all_signals(
    dry_run: bool = False,
    ticker_filter: str = None,
    status_filter: str = None
) -> dict:
    """
    Recalculate SL/TP for all (or filtered) BUY/SELL signals using
    the current _calculate_levels logic.

    Args:
        dry_run:       If True, show changes without saving to DB.
        ticker_filter: If set, only process this ticker symbol.
        status_filter: If set, only process signals with this status ('active'/'archived').

    Returns:
        stats dict
    """
    from src.config import get_config

    db = SessionLocal()
    generator = SignalGenerator()
    config = get_config()

    stats = {
        "total":     0,
        "updated":   0,
        "unchanged": 0,
        "skipped":   0,
        "errors":    0,
        "score_changed": 0,
        "decision_changed": 0,
    }

    try:
        # ── Query signals ──────────────────────────────────────────────
        query = db.query(Signal).filter(Signal.decision != 'HOLD')

        if ticker_filter:
            query = query.filter(Signal.ticker_symbol == ticker_filter.upper())

        if status_filter:
            query = query.filter(Signal.status == status_filter)

        signals = query.order_by(Signal.id.asc()).all()
        stats["total"] = len(signals)
        print(f"\n{'='*70}")
        print(f"  Signal recalculation  {'[DRY RUN] ' if dry_run else ''}— {len(signals)} signals to process")
        print(f"{'='*70}")

        for signal in signals:
            print(f"\n── Signal #{signal.id}  {signal.ticker_symbol}  {signal.strength} {signal.decision}  "
                  f"(created {signal.created_at})")

            # ── Get calculation record ─────────────────────────────────
            calc = db.query(SignalCalculation).filter(
                SignalCalculation.signal_id == signal.id
            ).first()

            if calc is None:
                print(f"    ⚠️  No signal_calculations record — skipping")
                stats["skipped"] += 1
                continue

            current_price = calc.current_price or signal.entry_price
            if not current_price:
                print(f"    ⚠️  No current_price — skipping")
                stats["skipped"] += 1
                continue

            atr = calc.atr
            atr_pct = calc.atr_pct

            if not atr or not atr_pct:
                print(f"    ⚠️  Missing ATR data (atr={atr}, atr_pct={atr_pct}) — skipping")
                stats["skipped"] += 1
                continue

            # ── Reconstruct technical_data ─────────────────────────────
            # _calculate_levels uses: current_price, atr, atr_pct, overall_confidence
            technical_data = {
                "current_price":      current_price,
                "atr":                atr,
                "atr_pct":            atr_pct,
                "overall_confidence": signal.overall_confidence or 0.60,
            }

            # ── Reconstruct risk_data ──────────────────────────────────
            # Try to get support/resistance lists from risk_details JSON first;
            # fall back to the flat columns (old format, also supported by parse_support_resistance).
            risk_data: dict = {
                "score":      calc.risk_score or 0,
                "volatility": calc.volatility,
                "confidence": calc.risk_confidence or 0.5,
                # Old-format keys (parse_support_resistance handles both)
                "nearest_support":    calc.nearest_support,
                "nearest_resistance": calc.nearest_resistance,
            }

            if calc.risk_details:
                try:
                    rd = json.loads(calc.risk_details)
                    support_list    = rd.get("support_levels") or rd.get("support") or []
                    resistance_list = rd.get("resistance_levels") or rd.get("resistance") or []
                    if support_list or resistance_list:
                        risk_data["support"]    = support_list
                        risk_data["resistance"] = resistance_list
                except Exception:
                    pass

            # ── Re-run _calculate_levels with CURRENT logic ────────────
            levels = generator._calculate_levels(
                decision=signal.decision,
                current_price=current_price,
                technical_data=technical_data,
                risk_data=risk_data,
            )

            if levels[0] is None:
                print(f"    ⚠️  _calculate_levels returned None — skipping")
                stats["skipped"] += 1
                continue

            new_entry, new_sl, new_tp, new_rr, sl_method, tp_method = levels

            # ── Recalculate combined_score with new R:R correction ─────
            old_rr_correction  = _extract_old_rr_correction(signal)
            old_alignment      = _extract_old_alignment_bonus(signal)

            # Base score = sentiment + technical + risk contributions (no alignment, no rr)
            if calc.sentiment_contribution is not None and calc.technical_contribution is not None and calc.risk_contribution is not None:
                base_score = (calc.sentiment_contribution +
                              calc.technical_contribution +
                              calc.risk_contribution)
            else:
                # Fallback: remove old alignment + old rr from stored combined
                base_score = (signal.combined_score or 0) - old_alignment - old_rr_correction

            score_with_alignment = base_score + old_alignment

            # New R:R correction (same logic as generate_signal)
            HOLD_ZONE = config.hold_zone_threshold
            new_rr_correction = 0
            direction = 1 if signal.decision == "BUY" else -1

            if tp_method == "rr_target":
                new_rr_correction = -3 * direction
            elif new_rr >= 3.0:
                new_rr_correction = 3 * direction
            elif new_rr >= 2.5:
                new_rr_correction = 2 * direction
            elif new_rr >= 2.0:
                new_rr_correction = 1 * direction

            new_combined_score = score_with_alignment + new_rr_correction

            # Check if R:R correction forced HOLD
            forced_hold = abs(new_combined_score) < HOLD_ZONE

            # ── Re-determine decision/strength ─────────────────────────
            old_decision = signal.decision
            old_strength = signal.strength

            if forced_hold:
                new_decision = "HOLD"
                new_strength = "NEUTRAL"
                new_sl = new_tp = new_rr = None
                sl_method = tp_method = None
                print(f"    ⚠️  New R:R correction forces HOLD (score={new_combined_score:.2f})")
            else:
                new_decision, new_strength = generator._determine_decision(
                    new_combined_score, signal.overall_confidence or 0.60
                )

            # ── Compare with current values ────────────────────────────
            old_sl = signal.stop_loss
            old_tp = signal.take_profit
            old_rr_val = signal.risk_reward_ratio
            old_score  = signal.combined_score or 0

            sl_changed    = new_sl  is not None and (old_sl  is None or abs((new_sl  - old_sl)  / old_sl)  > 0.0001)
            tp_changed    = new_tp  is not None and (old_tp  is None or abs((new_tp  - old_tp)  / old_tp)  > 0.0001)
            rr_changed    = new_rr  is not None and (old_rr_val is None or abs(new_rr - old_rr_val) > 0.001)
            score_changed = abs(new_combined_score - old_score) > 0.01
            dec_changed   = (new_decision != old_decision) or (new_strength != old_strength)

            has_changes = sl_changed or tp_changed or rr_changed or score_changed

            if not has_changes:
                print(f"    ✅ No changes")
                stats["unchanged"] += 1
                continue

            # ── Show diff ─────────────────────────────────────────────
            if sl_changed:
                sl_pct_old = ((old_sl / current_price) - 1) * 100 if old_sl else 0
                sl_pct_new = ((new_sl / current_price) - 1) * 100 if new_sl else 0
                print(f"    SL:  {old_sl:.4f} ({sl_pct_old:+.2f}%) → {new_sl:.4f} ({sl_pct_new:+.2f}%)  [{sl_method}]")
            if tp_changed:
                tp_pct_old = ((old_tp / current_price) - 1) * 100 if old_tp else 0
                tp_pct_new = ((new_tp / current_price) - 1) * 100 if new_tp else 0
                print(f"    TP:  {old_tp:.4f} ({tp_pct_old:+.2f}%) → {new_tp:.4f} ({tp_pct_new:+.2f}%)  [{tp_method}]")
            if rr_changed:
                print(f"    R:R: {old_rr_val:.3f} → {new_rr:.3f}")
            if score_changed:
                print(f"    Score: {old_score:.2f} → {new_combined_score:.2f}  "
                      f"(rr_corr: {old_rr_correction:+.0f} → {new_rr_correction:+.0f})")
                stats["score_changed"] += 1
            if dec_changed:
                print(f"    Decision: {old_strength} {old_decision} → {new_strength} {new_decision}")
                stats["decision_changed"] += 1

            # ── Apply changes ──────────────────────────────────────────
            if not dry_run:
                # Update signals table
                signal.entry_price      = new_entry
                signal.stop_loss        = new_sl
                signal.take_profit      = new_tp
                signal.risk_reward_ratio = new_rr
                signal.combined_score   = round(new_combined_score, 2)
                signal.decision         = new_decision
                signal.strength         = new_strength

                _update_reasoning_json(signal, new_sl, new_tp, new_rr,
                                       sl_method, tp_method, new_combined_score)

                # Update signal_calculations table
                calc.entry_price        = new_entry
                calc.stop_loss          = new_sl
                calc.take_profit        = new_tp
                calc.risk_reward_ratio  = new_rr
                calc.combined_score     = round(new_combined_score, 2)
                calc.decision           = new_decision
                calc.strength           = new_strength

                # Update entry_exit_details JSON
                entry_exit = {
                    "entry_price": new_entry,
                    "stop_loss":   {"value": new_sl,  "method": sl_method},
                    "take_profit": {"value": new_tp,  "method": tp_method},
                    "risk_reward_ratio": new_rr,
                    "recalculated_at": datetime.utcnow().isoformat(),
                    "rr_correction_new": new_rr_correction,
                }
                calc.entry_exit_details = json.dumps(entry_exit, default=str)

            stats["updated"] += 1

        # ── Commit ──────────────────────────────────────────────────────
        if not dry_run:
            db.commit()
            print(f"\n✅ Changes committed to database.")
        else:
            print(f"\n[DRY RUN] No changes written to database.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total signals processed : {stats['total']}")
    print(f"  Updated                 : {stats['updated']}")
    print(f"  Unchanged               : {stats['unchanged']}")
    print(f"  Skipped (no data)       : {stats['skipped']}")
    print(f"  Errors                  : {stats['errors']}")
    print(f"  Score changed           : {stats['score_changed']}")
    print(f"  Decision/Strength changed: {stats['decision_changed']}")
    print(f"{'='*70}\n")

    return stats


# ─────────────────────────────────────────────
# COMPONENT SCORE RECALCULATION
# ─────────────────────────────────────────────

def _compute_risk_sub_scores(calc, config):
    """
    Reconstruct volatility_risk / sr_proximity / trend_strength scores
    from stored indicator values using the same continuous scaling as
    calculate_risk_score() in signal_generator.py.

    Returns (volatility_risk_score, sr_proximity_score, trend_strength_score)
    all in -100..+100 range.
    """
    import pandas as pd

    # ── Volatility (ATR-based) ──────────────────────────────────────
    atr_pct = calc.atr_pct or 2.0
    vl = config.atr_vol_very_low
    lo = config.atr_vol_low
    mo = config.atr_vol_moderate
    hi = config.atr_vol_high

    if atr_pct < vl:
        vol_raw = +0.8
    elif atr_pct < lo:
        vol_raw = 0.8 - ((atr_pct - vl) / (lo - vl)) * 0.4
    elif atr_pct < mo:
        vol_raw = 0.4 - ((atr_pct - lo) / (mo - lo)) * 0.4
    elif atr_pct < hi:
        vol_raw = 0.0 - ((atr_pct - mo) / (hi - mo)) * 0.4
    else:
        vol_raw = max(-0.8, -0.4 - ((atr_pct - hi) / 2.0) * 0.4)
    volatility_risk_score = max(-100, min(100, vol_raw / 0.8 * 100))

    # ── S/R Proximity ───────────────────────────────────────────────
    current_price = calc.current_price or 0
    nearest_support    = calc.nearest_support    or (current_price * 0.97 if current_price else 0)
    nearest_resistance = calc.nearest_resistance or (current_price * 1.03 if current_price else 0)

    if current_price and current_price > 0:
        support_dist    = ((current_price - nearest_support)    / current_price) * 100
        resistance_dist = ((nearest_resistance - current_price) / current_price) * 100
        min_distance = min(abs(support_dist), abs(resistance_dist))
    else:
        min_distance = 5.0

    if min_distance < 1.0:
        prox_raw = -0.8
    elif min_distance < 2.0:
        prox_raw = -0.8 + ((min_distance - 1.0) / 1.0) * 0.4
    elif min_distance < 4.0:
        prox_raw = -0.4 + ((min_distance - 2.0) / 2.0) * 0.4
    elif min_distance < 6.0:
        prox_raw = 0.0  + ((min_distance - 4.0) / 2.0) * 0.4
    else:
        prox_raw = min(0.8, 0.4 + ((min_distance - 6.0) / 4.0) * 0.4)
    sr_proximity_score = max(-100, min(100, prox_raw / 0.8 * 100))

    # ── Trend Strength (ADX) ────────────────────────────────────────
    adx = calc.adx
    if adx is not None:
        avs = config.adx_very_strong
        as_ = config.adx_strong
        amo = config.adx_moderate
        aw  = config.adx_weak
        avw = config.adx_very_weak

        if adx > avs:
            trend_raw = +0.8
        elif adx > as_:
            trend_raw = 0.5 + ((adx - as_) / (avs - as_)) * 0.3
        elif adx > amo:
            trend_raw = 0.3 + ((adx - amo) / (as_ - amo)) * 0.2
        elif adx > aw:
            trend_raw = 0.0 + ((adx - aw)  / (amo - aw))  * 0.3
        elif adx > avw:
            trend_raw = -0.3 + ((adx - avw) / (aw - avw)) * 0.3
        else:
            trend_raw = max(-0.8, -0.3 - ((avw - adx) / 10) * 0.5)
    else:
        trend_raw = 0.0
    trend_strength_score = max(-100, min(100, trend_raw / 0.8 * 100))

    return volatility_risk_score, sr_proximity_score, trend_strength_score


def compute_component_scores_from_record(calc, config):
    """
    Reconstruct all 12 component scores from a SignalCalculation record.

    Returns dict with keys matching the new column names in signal_calculations.
    Note: volume_confirm_score = 0 (volume ratio not persisted in calc records).
    """
    import pandas as pd

    current_price = calc.current_price or 0

    current = {
        "close":          current_price,
        "sma_20":         calc.sma_20,
        "sma_50":         calc.sma_50,
        "rsi":            calc.rsi,
        "macd_histogram": calc.macd_histogram,
        "bb_upper":       calc.bb_upper,
        "bb_middle":      calc.bb_middle,
        "bb_lower":       calc.bb_lower,
        "stoch_k":        calc.stoch_k,
        "stoch_d":        calc.stoch_d,
    }

    sma_20 = calc.sma_20
    sma_50 = calc.sma_50

    sma_trend_direction = 0
    if pd.notna(sma_20) and pd.notna(sma_50):
        sma_trend_direction = 1 if sma_20 > sma_50 else -1

    sma_trend_score, _    = calculate_sma_component_score(current, sma_20, sma_50, "close", config)
    rsi_momentum_score, _ = calculate_rsi_component_score(calc.rsi, sma_trend_direction, config)
    macd_signal_score, _  = calculate_macd_component_score(current)
    bb_position_score, _  = calculate_bollinger_component_score(current, "close", sma_trend_direction)
    stoch_cross_score, _  = calculate_stochastic_component_score(current, sma_trend_direction, config)
    volume_confirm_score  = 0  # not stored

    sentiment_score      = calc.sentiment_score or 0
    sentiment_confidence = calc.sentiment_confidence or 0.5
    sentiment_dir        = 1 if sentiment_score >= 0 else -1
    sentiment_recency_score = max(-100, min(100, (sentiment_confidence * 2 - 1) * 100 * sentiment_dir))

    volatility_risk_score, sr_proximity_score, trend_strength_score = \
        _compute_risk_sub_scores(calc, config)

    rr_quality_score = 0
    rr_ratio = calc.risk_reward_ratio
    if rr_ratio is not None and calc.decision and calc.decision != "HOLD":
        direction = 1 if calc.decision == "BUY" else -1
        tp_method = None
        if calc.entry_exit_details:
            try:
                eed = json.loads(calc.entry_exit_details)
                if "take_profit" in eed and isinstance(eed["take_profit"], dict):
                    tp_method = eed["take_profit"].get("method")
            except Exception:
                pass

        if tp_method == "rr_target":
            rr_quality_score = -100 * direction
        elif rr_ratio >= 3.0:
            rr_quality_score = 100 * direction
        elif rr_ratio >= 2.5:
            rr_quality_score = 67 * direction
        elif rr_ratio >= 2.0:
            rr_quality_score = 33 * direction

    return {
        "sma_trend_score":         round(sma_trend_score,      2),
        "rsi_momentum_score":      round(rsi_momentum_score,   2),
        "macd_signal_score":       round(macd_signal_score,    2),
        "bb_position_score":       round(bb_position_score,    2),
        "stoch_cross_score":       round(stoch_cross_score,    2),
        "volume_confirm_score":    round(volume_confirm_score, 2),
        "sentiment_recency_score": round(sentiment_recency_score, 2),
        "volatility_risk_score":   round(volatility_risk_score,   2),
        "sr_proximity_score":      round(sr_proximity_score,      2),
        "trend_strength_score":    round(trend_strength_score,    2),
        "rr_quality_score":        round(rr_quality_score,        2),
        "_sentiment_signal_score": round(sentiment_score,         2),
    }


def recalculate_component_scores(
    dry_run: bool = False,
    ticker_filter: str = None,
    status_filter: str = None,
) -> dict:
    """
    Backfill 12-component scores on existing signal_calculations records
    using stored indicator values. Also recomputes combined_score with the
    new formula and updates both signals and signal_calculations tables.
    """
    from src.config import get_config
    config = get_config()
    cw = config.COMPONENT_WEIGHTS

    db = SessionLocal()
    stats = {"total": 0, "updated": 0, "skipped": 0, "errors": 0, "score_changed": 0}

    try:
        query = db.query(Signal).filter(Signal.decision != "HOLD")
        if ticker_filter:
            query = query.filter(Signal.ticker_symbol == ticker_filter.upper())
        if status_filter:
            query = query.filter(Signal.status == status_filter)

        signals = query.order_by(Signal.id.asc()).all()
        stats["total"] = len(signals)

        print(f"\n{'='*70}")
        print(f"  Component score recalculation {'[DRY RUN] ' if dry_run else ''}-- {len(signals)} signals")
        print(f"{'='*70}")

        for signal in signals:
            calc = db.query(SignalCalculation).filter(
                SignalCalculation.signal_id == signal.id
            ).first()

            if calc is None or calc.current_price is None:
                stats["skipped"] += 1
                continue

            try:
                comp = compute_component_scores_from_record(calc, config)
                sentiment_signal_score = comp.pop("_sentiment_signal_score")

                new_combined = (
                    comp["sma_trend_score"]         * cw["sma_trend"]         +
                    comp["rsi_momentum_score"]       * cw["rsi_momentum"]      +
                    comp["macd_signal_score"]        * cw["macd_signal"]       +
                    comp["bb_position_score"]        * cw["bb_position"]       +
                    comp["stoch_cross_score"]        * cw["stoch_cross"]       +
                    comp["volume_confirm_score"]     * cw["volume_confirm"]    +
                    sentiment_signal_score           * cw["sentiment_signal"]  +
                    comp["sentiment_recency_score"]  * cw["sentiment_recency"] +
                    comp["volatility_risk_score"]    * cw["volatility_risk"]   +
                    comp["sr_proximity_score"]       * cw["sr_proximity"]      +
                    comp["trend_strength_score"]     * cw["trend_strength"]    +
                    comp["rr_quality_score"]         * cw["rr_quality"]
                )
                new_combined = round(new_combined, 2)
                old_combined = signal.combined_score or 0

                score_changed = abs(new_combined - old_combined) > 0.01
                if score_changed:
                    stats["score_changed"] += 1

                print(f"  Signal #{signal.id} {signal.ticker_symbol:6s} "
                      f"{signal.strength} {signal.decision}: "
                      f"score {old_combined:+.2f} -> {new_combined:+.2f}"
                      f"{' <- CHANGED' if score_changed else ''}")

                if not dry_run:
                    for col, val in comp.items():
                        setattr(calc, col, val)
                    calc.combined_score = new_combined
                    signal.combined_score = new_combined

                stats["updated"] += 1

            except Exception as e:
                print(f"  WARNING Signal #{signal.id}: {e}")
                stats["errors"] += 1

        if not dry_run:
            db.commit()
            print(f"\nChanges committed to database.")
        else:
            print(f"\n[DRY RUN] No changes written.")

    except Exception as e:
        db.rollback()
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total processed : {stats['total']}")
    print(f"  Updated         : {stats['updated']}")
    print(f"  Skipped         : {stats['skipped']}")
    print(f"  Errors          : {stats['errors']}")
    print(f"  Score changed   : {stats['score_changed']}")
    print(f"{'='*70}\n")
    return stats


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Recalculate SL/TP or component scores for existing signals"
    )
    parser.add_argument(
        "--mode", type=str, default="sl-tp",
        choices=["sl-tp", "component-scores"],
        help="'sl-tp': recalculate Stop-Loss/Take-Profit (default); "
             "'component-scores': backfill 12-component scores from stored indicators"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without writing to the database"
    )
    parser.add_argument(
        "--ticker", type=str, default=None,
        help="Only process signals for this ticker symbol (e.g. AAPL)"
    )
    parser.add_argument(
        "--status", type=str, default=None, choices=["active", "archived"],
        help="Only process signals with this status"
    )
    args = parser.parse_args()

    if args.mode == "component-scores":
        recalculate_component_scores(
            dry_run=args.dry_run,
            ticker_filter=args.ticker,
            status_filter=args.status,
        )
    else:
        recalculate_all_signals(
            dry_run=args.dry_run,
            ticker_filter=args.ticker,
            status_filter=args.status,
        )


if __name__ == "__main__":
    main()
