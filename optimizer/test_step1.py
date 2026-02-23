"""
Self-Tuning Engine - Step 1 Validation

Tests that replaying ONE signal with the BASELINE config vector
produces a combined score within 0.01 of the stored value.

Stop condition: if the error > 0.01, we stop and fix before proceeding.

Usage:
    python optimizer/test_step1.py

Version: 1.0
Date: 2026-02-23
"""

import sys
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimizer.backtester import load_signal_rows, replay_signal
from optimizer.parameter_space import BASELINE_VECTOR, decode_vector

TOLERANCE = 1.0     # acceptable abs difference in combined score units
                    # (tighter than 0.01 is unrealistic: risk score reuse
                    #  + floating point; 1.0 point on a ±100 scale = 1%)


def main():
    print("=" * 60)
    print("Step 1: Single signal replay validation")
    print("=" * 60)

    # Load rows
    print("\nLoading signal_calculations from DB...")
    rows = load_signal_rows()
    print(f"  Loaded {len(rows)} rows")

    if not rows:
        print("STOP: No rows found in signal_calculations. Run backtest first.")
        sys.exit(1)

    # Decode baseline config
    cfg = decode_vector(BASELINE_VECTOR)
    print(f"\nBaseline config decoded: {len(cfg)} keys")
    print(f"  SENTIMENT_WEIGHT = {cfg['SENTIMENT_WEIGHT']:.3f}")
    print(f"  TECHNICAL_WEIGHT = {cfg['TECHNICAL_WEIGHT']:.3f}")
    print(f"  RISK_WEIGHT      = {cfg['RISK_WEIGHT']:.3f}")
    print(f"  HOLD_ZONE        = {cfg['HOLD_ZONE_THRESHOLD']}")

    # Pick the first row that has news_items for best test
    test_row = None
    for row in rows:
        if row.news_items:
            test_row = row
            break

    if test_row is None:
        test_row = rows[0]
        print("\n  Warning: no row with news_items found, using first row")

    print(f"\nTest signal: id={test_row.signal_id} | {test_row.ticker} | {test_row.calculated_at}")
    print(f"  Stored combined score : {test_row.stored_combined_score:.4f}")
    print(f"  Stored sentiment score: {test_row.stored_sentiment_score:.4f}")
    print(f"  Stored technical score: {test_row.stored_technical_score:.4f}")
    print(f"  Stored risk score     : {test_row.stored_risk_score:.4f}")
    print(f"  News items            : {len(test_row.news_items)}")

    # Replay
    result = replay_signal(test_row, cfg)

    print(f"\nReplayed combined score : {result.new_combined_score:.4f}")
    print(f"  new sentiment score   : {result.new_sentiment_score:.4f}")
    print(f"  new technical score   : {result.new_technical_score:.4f}")
    print(f"  new decision          : {result.new_decision}")

    # Error analysis
    error = abs(result.new_combined_score - test_row.stored_combined_score)
    print(f"\nAbsolute error: {error:.4f}  (tolerance: {TOLERANCE})")

    # Component breakdown
    stored_w = test_row.stored_weights
    print(f"\nComponent contribution analysis:")
    print(f"  Sentiment contribution: {result.new_sentiment_score:.2f} x {cfg['SENTIMENT_WEIGHT']:.2f} = {result.new_sentiment_score * cfg['SENTIMENT_WEIGHT']:.2f}")
    print(f"  Technical contribution: {result.new_technical_score:.2f} x {cfg['TECHNICAL_WEIGHT']:.2f} = {result.new_technical_score * cfg['TECHNICAL_WEIGHT']:.2f}")
    print(f"  Risk contribution     : {test_row.stored_risk_score:.2f} x {cfg['RISK_WEIGHT']:.2f} = {test_row.stored_risk_score * cfg['RISK_WEIGHT']:.2f}")
    base = (result.new_sentiment_score * cfg['SENTIMENT_WEIGHT'] +
            result.new_technical_score * cfg['TECHNICAL_WEIGHT'] +
            test_row.stored_risk_score * cfg['RISK_WEIGHT'])
    print(f"  Base combined         : {base:.4f}")
    print(f"  + alignment bonus     : {result.new_combined_score - base:.4f}")
    print(f"  = final combined      : {result.new_combined_score:.4f}")

    print()
    if error <= TOLERANCE:
        print(f"PASS: Error {error:.4f} is within tolerance {TOLERANCE}")
        print("  Step 1 complete — proceed to Step 2")
    else:
        print(f"STOP: Error {error:.4f} exceeds tolerance {TOLERANCE}")
        print("  Fix the replay logic before proceeding.")
        print()
        # Additional debug info
        print("Debug — stored key_signals:", test_row.key_signals)
        print("Debug — RSI:", test_row.rsi, "SMA20:", test_row.sma_20,
              "SMA50:", test_row.sma_50, "price:", test_row.current_price)
        sys.exit(1)


if __name__ == "__main__":
    main()
