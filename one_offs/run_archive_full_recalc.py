"""
TrendSignal - Archive Teljes Újrakalkuláció

1. lépés: archive_signals SL/TP/score újrakalkulálása a jelenlegi
          _calculate_levels logikával (ugyanaz, mint a live recalculate_signals.py)

2. lépés: archive_simulated_trades teljes törlése + újraszimulálás az
          ArchiveBacktestService-szel (ugyanaz a trade_simulator_core, mint a live)

Usage:
    python one_offs/run_archive_full_recalc.py           # interaktív megerősítés
    python one_offs/run_archive_full_recalc.py --confirm  # prompt nélkül
    python one_offs/run_archive_full_recalc.py --dry-run  # csak signal recalc preview
    python one_offs/run_archive_full_recalc.py --ticker AAPL  # csak egy ticker
    python one_offs/run_archive_full_recalc.py --skip-signals  # csak trade resim
"""

import sys
import os
import io
import json
import logging
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# RÉSZ 1: ARCHIVE SIGNAL RECALC
# Ugyanaz a logika, mint a src/recalculate_signals.py — de archive_signals-en fut,
# sqlite3-on keresztül (nincs ORM model az archive táblákra).
# ─────────────────────────────────────────────────────────────────────────────

def recalculate_archive_signals(
    db_path: str,
    dry_run: bool = False,
    ticker_filter: str = None,
) -> dict:
    import sqlite3
    from src.config import get_config
    from src.signal_generator import SignalGenerator

    generator = SignalGenerator()
    config    = get_config()

    stats = {
        "total":            0,
        "updated":          0,
        "unchanged":        0,
        "skipped":          0,
        "errors":           0,
        "score_changed":    0,
        "decision_changed": 0,
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        where = "WHERE decision IN ('BUY','SELL')"
        params = []
        if ticker_filter:
            where += " AND ticker_symbol = ?"
            params.append(ticker_filter.upper())

        rows = conn.execute(
            f"SELECT * FROM archive_signals {where} ORDER BY id ASC",
            params,
        ).fetchall()

        stats["total"] = len(rows)
        print(f"\n{'='*70}")
        print(f"  ARCHIVE SIGNAL RECALC  {'[DRY RUN] ' if dry_run else ''}— {len(rows)} signal")
        print(f"{'='*70}")

        for row in rows:
            sig_id  = row["id"]
            ticker  = row["ticker_symbol"]
            dec     = row["decision"]
            strength = row["strength"] or ""

            entry_price = row["entry_price"] or row["close_price"]
            if not entry_price:
                print(f"  ⚠️  #{sig_id} {ticker} — nincs entry_price, skip")
                stats["skipped"] += 1
                continue

            atr     = row["atr"]
            atr_pct = row["atr_pct"]
            if not atr or not atr_pct:
                print(f"  ⚠️  #{sig_id} {ticker} — hiányzó ATR, skip")
                stats["skipped"] += 1
                continue

            # Ugyanaz a technical_data struktúra, mint a live recalcban
            technical_data = {
                "current_price":      entry_price,
                "atr":                atr,
                "atr_pct":            atr_pct,
                "overall_confidence": row["overall_confidence"] or 0.60,
            }

            # risk_data — archive_signals-nek nincs risk_details JSON-je,
            # csak flat nearest_support / nearest_resistance mezők (pontosan
            # mint a live recalc fallback ágán)
            risk_data = {
                "score":              row["risk_score"]      or 0,
                "volatility":         None,
                "confidence":         row["risk_confidence"] or 0.5,
                "nearest_support":    row["nearest_support"],
                "nearest_resistance": row["nearest_resistance"],
            }

            # Reasoning JSON-ból a régi rr_correction kinyerése
            old_rr_correction = 0.0
            old_alignment     = row["alignment_bonus"] or 0
            try:
                if row["reasoning_json"]:
                    rj = json.loads(row["reasoning_json"])
                    old_rr_correction = float(rj.get("rr_correction") or 0)
            except Exception:
                pass

            # _calculate_levels — ugyanaz a függvény, mint a live-ban
            try:
                levels = generator._calculate_levels(
                    decision=dec,
                    current_price=entry_price,
                    technical_data=technical_data,
                    risk_data=risk_data,
                )
            except Exception as e:
                print(f"  ❌ #{sig_id} {ticker} — _calculate_levels hiba: {e}")
                stats["errors"] += 1
                continue

            if levels[0] is None:
                print(f"  ⚠️  #{sig_id} {ticker} — _calculate_levels None, skip")
                stats["skipped"] += 1
                continue

            new_entry, new_sl, new_tp, new_rr, sl_method, tp_method = levels

            # combined_score újrakalkulálása — archive_signals tartalmazza
            # a base_combined_score-t közvetlenül, nincs szükség visszaszámolásra
            base_score = row["base_combined_score"]
            if base_score is None:
                # Fallback: régi rr_correction + alignment eltávolítása
                base_score = (row["combined_score"] or 0) - old_alignment - old_rr_correction

            score_with_alignment = base_score + old_alignment

            HOLD_ZONE = config.hold_zone_threshold
            new_rr_correction = 0
            direction = 1 if dec == "BUY" else -1

            if tp_method == "rr_target":
                new_rr_correction = -3 * direction
            elif new_rr >= 3.0:
                new_rr_correction = 3 * direction
            elif new_rr >= 2.5:
                new_rr_correction = 2 * direction
            elif new_rr >= 2.0:
                new_rr_correction = 1 * direction

            new_combined_score = score_with_alignment + new_rr_correction
            forced_hold = abs(new_combined_score) < HOLD_ZONE

            if forced_hold:
                new_decision = "HOLD"
                new_strength = "NEUTRAL"
                new_sl = new_tp = new_rr = None
            else:
                new_decision, new_strength = generator._determine_decision(
                    new_combined_score, row["overall_confidence"] or 0.60
                )

            # Változás-ellenőrzés
            old_sl    = row["stop_loss"]
            old_tp    = row["take_profit"]
            old_rr_v  = row["risk_reward_ratio"]
            old_score = row["combined_score"] or 0
            old_dec   = row["decision"]
            old_str   = row["strength"] or ""

            sl_changed    = new_sl is not None and (old_sl is None or abs((new_sl - old_sl) / old_sl) > 0.0001)
            tp_changed    = new_tp is not None and (old_tp is None or abs((new_tp - old_tp) / old_tp) > 0.0001)
            rr_changed    = new_rr is not None and (old_rr_v is None or abs(new_rr - old_rr_v) > 0.001)
            score_changed = abs(new_combined_score - old_score) > 0.01
            dec_changed   = (new_decision != old_dec) or (new_strength != old_str)

            if not (sl_changed or tp_changed or rr_changed or score_changed):
                stats["unchanged"] += 1
                continue

            if score_changed:
                stats["score_changed"] += 1
                print(f"  #{sig_id} {ticker} {strength} {dec}  "
                      f"score: {old_score:.2f}→{new_combined_score:.2f}  "
                      f"SL: {old_sl}→{new_sl}  TP: {old_tp}→{new_tp}  R:R: {old_rr_v}→{new_rr}")
            if dec_changed:
                stats["decision_changed"] += 1
                print(f"    Decision: {old_str} {old_dec} → {new_strength} {new_decision}")

            if not dry_run:
                conn.execute("""
                    UPDATE archive_signals
                    SET entry_price       = ?,
                        stop_loss         = ?,
                        take_profit       = ?,
                        risk_reward_ratio = ?,
                        combined_score    = ?,
                        decision          = ?,
                        strength          = ?,
                        rr_correction     = ?
                    WHERE id = ?
                """, (
                    new_entry,
                    new_sl,
                    new_tp,
                    round(new_rr, 4) if new_rr else None,
                    round(new_combined_score, 2),
                    new_decision,
                    new_strength,
                    new_rr_correction,
                    sig_id,
                ))

            stats["updated"] += 1

        if not dry_run:
            conn.commit()
            print(f"\n  ✅ Archive signal változások mentve.")
        else:
            print(f"\n  [DRY RUN] Nincs DB-írás.")

    except Exception as e:
        conn.rollback()
        print(f"\n  ❌ Fatális hiba: {e}")
        import traceback; traceback.print_exc()
        raise
    finally:
        conn.close()

    print(f"\n{'='*70}")
    print(f"  ARCHIVE SIGNAL RECALC ÖSSZEFOGLALÓ")
    print(f"{'='*70}")
    print(f"  Összes:            {stats['total']}")
    print(f"  Frissítve:         {stats['updated']}")
    print(f"  Változatlan:       {stats['unchanged']}")
    print(f"  Skip:              {stats['skipped']}")
    print(f"  Hiba:              {stats['errors']}")
    print(f"  Score változott:   {stats['score_changed']}")
    print(f"  Decision változott:{stats['decision_changed']}")
    print(f"{'='*70}\n")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# RÉSZ 2: ARCHIVE TRADE RESZIMULÁCIÓ
# ArchiveBacktestService.run() — ugyanaz a trade_simulator_core, mint a live
# ─────────────────────────────────────────────────────────────────────────────

def run_archive_trade_resim(db_path: str, ticker_filter: str = None) -> dict:
    from src.archive_backtest_service import ArchiveBacktestService

    symbols = [ticker_filter.upper()] if ticker_filter else None

    print(f"\n{'='*70}")
    print(f"  ARCHIVE TRADE ÚJRASZIMULÁCIÓ")
    if symbols:
        print(f"  Ticker(ek): {', '.join(symbols)}")
    else:
        print(f"  Összes ticker")
    print(f"{'='*70}\n")

    service = ArchiveBacktestService(db_path)
    stats   = service.run(symbols=symbols)

    print(f"\n{'='*70}")
    print(f"  ARCHIVE TRADE RESIM ÖSSZEFOGLALÓ")
    print(f"{'='*70}")
    print(f"  Tickers:           {stats['tickers']}")
    print(f"  Feldolgozott sig:  {stats['signals_processed']}")
    print(f"  Létrehozott trade: {stats['trades_created']}")
    print(f"  ├─ TP hit:         {stats['tp_hit']}")
    print(f"  ├─ SL hit:         {stats['sl_hit']}")
    print(f"  ├─ Stagnation:     {stats['stagnation']}")
    print(f"  ├─ Opposing sig:   {stats['opposing']}")
    print(f"  ├─ EOD close:      {stats['eod']}")
    print(f"  ├─ Max hold:       {stats['max_hold']}")
    print(f"  ├─ Open:           {stats['open']}")
    print(f"  └─ Skip:           {stats['skipped']}")
    print(f"{'='*70}\n")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    auto_confirm  = "--confirm"      in args
    dry_run       = "--dry-run"      in args
    skip_signals  = "--skip-signals" in args

    ticker_filter = None
    for i, a in enumerate(args):
        if a == "--ticker" and i + 1 < len(args):
            ticker_filter = args[i + 1]

    from src.database import DATABASE_PATH
    db_path = str(DATABASE_PATH)

    print(f"\n{'='*70}")
    print(f"  ARCHIVE TELJES ÚJRAKALKULÁCIÓ")
    print(f"{'='*70}")
    print(f"  DB:      {db_path}")
    if ticker_filter:
        print(f"  Ticker:  {ticker_filter.upper()}")
    if skip_signals:
        print(f"  Mód:     csak trade resim (signal recalc kihagyva)")
    elif dry_run:
        print(f"  Mód:     dry-run (signal recalc preview, trade resim NEM fut)")
    else:
        print(f"  Mód:     teljes (signal recalc + trade resim)")
    print(f"{'='*70}\n")

    if not auto_confirm and not dry_run:
        confirm = input("Folytatod? [igen/nem]: ").strip().lower()
        if confirm != "igen":
            print("Megszakítva.")
            return

    # 1. Signal recalc
    if not skip_signals:
        recalculate_archive_signals(
            db_path=db_path,
            dry_run=dry_run,
            ticker_filter=ticker_filter,
        )

    # 2. Trade resim (csak ha nem dry-run)
    if not dry_run:
        run_archive_trade_resim(
            db_path=db_path,
            ticker_filter=ticker_filter,
        )
    else:
        print("  [DRY RUN] Trade reszimuláció kihagyva.\n")


if __name__ == "__main__":
    main()
