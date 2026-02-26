#!/usr/bin/env python3
"""
TrendSignal - Retroactive R:R Score Correction Script

Applies the direction-aware R:R score correction (introduced in commit 872a491)
to all historical signals that were stored without it.

Correction logic (mirrors signal_generator.py):
  - tp_method == "rr_target"  -> penalty:  -3 * direction
  - natural rr_ratio >= 2.0   -> reward:   +1 * direction
  - natural rr_ratio >= 2.5   -> reward:   +2 * direction
  - natural rr_ratio >= 3.0   -> reward:   +3 * direction
  direction = +1 for BUY, -1 for SELL (determined from pre-correction score)

Updates:
  - signals.combined_score, decision, strength, reasoning_json
  - signals.entry_price, stop_loss, take_profit, risk_reward_ratio (NULL on forced HOLD)
  - signal_calculations.combined_score, decision, strength

Usage:
  python one_offs/retroactive_rr_correction.py           # apply changes
  python one_offs/retroactive_rr_correction.py --dry-run  # stats only, no writes
"""

import sqlite3
import json
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

DATABASE_PATH = r"..\trendsignal.db"

# Decision / strength thresholds (from config.json)
HOLD_ZONE        = 15
STRONG_BUY_SCORE = 55
MODERATE_BUY_SCORE = 35
STRONG_SELL_SCORE  = -65
MODERATE_SELL_SCORE = -35

STRONG_BUY_CONF   = 0.75
MODERATE_BUY_CONF = 0.65
STRONG_SELL_CONF  = 0.75
MODERATE_SELL_CONF = 0.65

# ============================================================================
# HELPERS
# ============================================================================

def classify(combined_score: float, confidence: float):
    """Return (decision, strength) from final combined_score + confidence."""
    if combined_score >= STRONG_BUY_SCORE and confidence >= STRONG_BUY_CONF:
        return "BUY", "STRONG"
    elif combined_score >= MODERATE_BUY_SCORE and confidence >= MODERATE_BUY_CONF:
        return "BUY", "MODERATE"
    elif combined_score >= HOLD_ZONE:
        return "BUY", "WEAK"
    elif combined_score <= STRONG_SELL_SCORE and confidence >= STRONG_SELL_CONF:
        return "SELL", "STRONG"
    elif combined_score <= MODERATE_SELL_SCORE and confidence >= MODERATE_SELL_CONF:
        return "SELL", "MODERATE"
    elif combined_score <= -HOLD_ZONE:
        return "SELL", "WEAK"
    else:
        return "HOLD", "NEUTRAL"


def compute_rr_correction(pre_rr_score: float, rr_ratio, tp_method) -> int:
    """
    Compute direction-aware R:R correction.
    Returns 0 if the pre-correction score is in the HOLD zone or data is missing.
    """
    if abs(pre_rr_score) < HOLD_ZONE:
        return 0  # was/is HOLD — no correction applicable

    direction = 1 if pre_rr_score >= HOLD_ZONE else -1

    if tp_method == "rr_target":
        return -3 * direction

    if rr_ratio is None:
        return 0

    if rr_ratio >= 3.0:
        return 3 * direction
    elif rr_ratio >= 2.5:
        return 2 * direction
    elif rr_ratio >= 2.0:
        return 1 * direction

    return 0


def update_reasoning_json(reasoning_json_str: str,
                          new_combined_score: float,
                          new_rr_correction: int,
                          new_decision: str,
                          new_strength: str) -> str:
    """
    Update reasoning_json fields in-place:
      - combined_score, rr_correction, decision, strength (top level)
      - components.alignment.rr_correction, final_score (if structure exists)
    Returns updated JSON string; on parse error returns original.
    """
    if not reasoning_json_str:
        return reasoning_json_str
    try:
        rj = json.loads(reasoning_json_str)
    except (json.JSONDecodeError, TypeError):
        return reasoning_json_str

    rj["combined_score"] = new_combined_score
    rj["rr_correction"]  = new_rr_correction if new_rr_correction != 0 else None
    rj["decision"]       = new_decision
    rj["strength"]       = new_strength

    comp = rj.get("components")
    if isinstance(comp, dict):
        aln = comp.get("alignment")
        if isinstance(aln, dict):
            aln["rr_correction"] = new_rr_correction
            aln["final_score"]   = round(new_combined_score, 2)

    return json.dumps(rj)


# ============================================================================
# MAIN
# ============================================================================

def main(dry_run: bool = False):
    db_path = Path(DATABASE_PATH)
    if not db_path.exists():
        print(f"ERROR: Database not found: {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    mode_label = "DRY-RUN" if dry_run else "LIVE"
    print("=" * 80)
    print(f"TrendSignal - Retroactive R:R Score Correction  [{mode_label}]")
    print("=" * 80)

    # ------------------------------------------------------------------
    # Step 1: Load all signals
    # ------------------------------------------------------------------
    print("\nStep 1: Loading signals...")
    cur.execute("""
        SELECT id, ticker_symbol, created_at,
               combined_score, overall_confidence,
               decision, strength,
               risk_reward_ratio, reasoning_json,
               entry_price, stop_loss, take_profit
        FROM signals
        ORDER BY id
    """)
    signals = cur.fetchall()
    print(f"  Loaded {len(signals)} signals")

    # ------------------------------------------------------------------
    # Step 2: Compute corrections
    # ------------------------------------------------------------------
    print("\nStep 2: Computing corrections...")

    updates      = []   # signals that actually change
    unchanged    = 0
    skipped_hold = 0

    # Stats counters
    decision_shifts = {}   # (old_decision, new_decision) -> count
    strength_shifts = {}   # (old_strength, new_strength) -> count
    forced_hold_count = 0
    score_deltas = []      # (id, ticker, delta) for top-N report

    for row in signals:
        sid       = row["id"]
        ticker    = row["ticker_symbol"]
        cur_score = row["combined_score"] or 0.0
        confidence = row["overall_confidence"] or 0.5
        rr_ratio  = row["risk_reward_ratio"]
        old_dec   = row["decision"]
        old_str   = row["strength"]
        rj_str    = row["reasoning_json"]

        # --- extract old rr_correction and tp_method from reasoning_json ---
        old_rr_correction = 0
        tp_method = None
        if rj_str:
            try:
                rj = json.loads(rj_str)
                # "rr_correction" key present -> signal was already processed
                if "rr_correction" in rj:
                    old_rr_correction = rj["rr_correction"] or 0
                lm = rj.get("levels_meta") or {}
                tp_method = lm.get("tp_method")
            except (json.JSONDecodeError, TypeError):
                pass

        # --- restore pre-R:R score ---
        pre_rr_score = cur_score - old_rr_correction

        # --- skip pure HOLD signals (no levels, no direction) ---
        if abs(pre_rr_score) < HOLD_ZONE and rr_ratio is None:
            skipped_hold += 1
            continue

        # --- compute new correction ---
        new_rr_correction = compute_rr_correction(pre_rr_score, rr_ratio, tp_method)

        # --- new combined score ---
        new_combined_score = pre_rr_score + new_rr_correction

        # --- forced HOLD? ---
        force_hold = abs(new_combined_score) < HOLD_ZONE

        if force_hold:
            new_dec, new_str = "HOLD", "NEUTRAL"
            new_entry = new_sl = new_tp = new_rr = None
            forced_hold_count += 1
        else:
            new_dec, new_str = classify(new_combined_score, confidence)
            new_entry = row["entry_price"]
            new_sl    = row["stop_loss"]
            new_tp    = row["take_profit"]
            new_rr    = rr_ratio

        # --- check if anything actually changed ---
        score_changed   = abs(new_combined_score - cur_score) > 1e-6
        dec_changed     = new_dec != old_dec
        str_changed     = new_str != old_str
        levels_changed  = force_hold and (row["entry_price"] is not None)

        if not (score_changed or dec_changed or str_changed or levels_changed):
            unchanged += 1
            continue

        # --- build updated reasoning_json ---
        new_rj_str = update_reasoning_json(
            rj_str, new_combined_score, new_rr_correction, new_dec, new_str
        )

        updates.append({
            "id":                sid,
            "ticker":            ticker,
            "old_score":         cur_score,
            "new_score":         new_combined_score,
            "old_dec":           old_dec,
            "new_dec":           new_dec,
            "old_str":           old_str,
            "new_str":           new_str,
            "new_rj":            new_rj_str,
            "new_entry":         new_entry,
            "new_sl":            new_sl,
            "new_tp":            new_tp,
            "new_rr":            new_rr,
            "new_rr_correction": new_rr_correction,
        })

        # stats
        shift_key = (old_dec, new_dec)
        decision_shifts[shift_key] = decision_shifts.get(shift_key, 0) + 1
        str_key = (old_str, new_str)
        strength_shifts[str_key] = strength_shifts.get(str_key, 0) + 1
        score_deltas.append((sid, ticker, new_combined_score - cur_score))

    print(f"  Total signals:      {len(signals)}")
    print(f"  HOLD (skipped):     {skipped_hold}")
    print(f"  Unchanged:          {unchanged}")
    print(f"  To update:          {len(updates)}")
    print(f"  Forced to HOLD:     {forced_hold_count}")

    # ------------------------------------------------------------------
    # Step 3: Print stats
    # ------------------------------------------------------------------
    print("\nStep 3: Statistics")

    if decision_shifts:
        print("\n  Decision shifts (old -> new):")
        for (old_d, new_d), cnt in sorted(decision_shifts.items()):
            marker = " !" if old_d != new_d else ""
            print(f"    {old_d:4s} -> {new_d:4s} : {cnt:5d}{marker}")

    if strength_shifts:
        print("\n  Strength shifts (old -> new):")
        for (old_s, new_s), cnt in sorted(strength_shifts.items()):
            marker = " !" if old_s != new_s else ""
            print(f"    {old_s:8s} -> {new_s:8s} : {cnt:5d}{marker}")

    if score_deltas:
        top10 = sorted(score_deltas, key=lambda x: abs(x[2]), reverse=True)[:10]
        print("\n  Top 10 largest score changes:")
        print(f"    {'ID':>6}  {'Ticker':6}  {'Delta':>8}")
        for sid, ticker, delta in top10:
            print(f"    {sid:>6}  {ticker:6}  {delta:>+8.2f}")

    # ------------------------------------------------------------------
    # Step 4: Apply to DB (unless dry-run)
    # ------------------------------------------------------------------
    if dry_run:
        print("\n[DRY-RUN] No changes written to database.")
        conn.close()
        return

    print(f"\nStep 4: Writing {len(updates)} updates to database...")

    try:
        for u in updates:
            # Update signals table
            cur.execute("""
                UPDATE signals
                SET combined_score  = ?,
                    decision        = ?,
                    strength        = ?,
                    entry_price     = ?,
                    stop_loss       = ?,
                    take_profit     = ?,
                    risk_reward_ratio = ?,
                    reasoning_json  = ?
                WHERE id = ?
            """, (
                round(u["new_score"], 6),
                u["new_dec"],
                u["new_str"],
                u["new_entry"],
                u["new_sl"],
                u["new_tp"],
                u["new_rr"],
                u["new_rj"],
                u["id"],
            ))

            # Update signal_calculations table (same signal_id)
            cur.execute("""
                UPDATE signal_calculations
                SET combined_score = ?,
                    decision       = ?,
                    strength       = ?
                WHERE signal_id = ?
            """, (
                round(u["new_score"], 6),
                u["new_dec"],
                u["new_str"],
                u["id"],
            ))

        conn.commit()
        print(f"  Committed {len(updates)} signals + matching signal_calculations rows.")

    except Exception as e:
        conn.rollback()
        print(f"  ERROR — rolled back: {e}")
        raise

    # ------------------------------------------------------------------
    # Step 5: Verification
    # ------------------------------------------------------------------
    print("\nStep 5: Verification")

    cur.execute("""
        SELECT decision, strength, COUNT(*) as cnt
        FROM signals
        GROUP BY decision, strength
        ORDER BY decision, strength
    """)
    print("\n  Decision / Strength distribution (post-update):")
    total = 0
    for r in cur.fetchall():
        print(f"    {r['decision']:4s}  {r['strength']:8s}  {r['cnt']:5d}")
        total += r["cnt"]
    print(f"    {'TOTAL':13s}  {total:5d}")

    conn.close()

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
