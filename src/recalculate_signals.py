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
from src.signal_generator import SignalGenerator, parse_support_resistance


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
# CLI ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Recalculate SL/TP for existing signals using current logic"
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

    recalculate_all_signals(
        dry_run=args.dry_run,
        ticker_filter=args.ticker,
        status_filter=args.status,
    )


if __name__ == "__main__":
    main()
