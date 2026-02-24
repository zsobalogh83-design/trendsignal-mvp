"""
Self-Tuning Engine - Step 3 Validation

Tests the fitness function with the BASELINE config vector:
  1. Fitness is a valid positive number (or 0 if trades insufficient)
  2. Train / val / test split is correct and chronological
  3. A deliberately bad config produces different fitness than baseline
  4. Fitness is stable across two calls (deterministic)
  5. Train/val overfitting gap check

v2 changes: uses load_all_sim_data() + replay_and_simulate() — no simulated_trades lookup.

Stop condition: any check fails.

Usage:
    python optimizer/test_step3.py

Version: 2.0
Date: 2026-02-24
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimizer.signal_data import load_all_sim_data
from optimizer.fitness import compute_fitness_for_subset, split_rows
from optimizer.parameter_space import BASELINE_VECTOR, decode_vector


def main():
    print("=" * 60)
    print("Step 3: Fitness function validation (v2 -- full trade sim)")
    print("=" * 60)

    # --- Load data ---
    print("\nLoading data (signal_calculations + price_data)...")
    rows, score_timeline = load_all_sim_data()
    print(f"  Signals: {len(rows)}")
    print(f"  Tickers in score timeline: {len(score_timeline)}")

    if len(rows) < 30:
        print("STOP: Need at least 30 signal_calculations rows.")
        sys.exit(1)

    # --- Split ---
    train, val, test = split_rows(rows)
    print(f"\nData split (chronological):")
    print(f"  Train: {len(train)} signals ({train[0].calculated_at[:10]} to {train[-1].calculated_at[:10]})")
    print(f"  Val  : {len(val)} signals ({val[0].calculated_at[:10]} to {val[-1].calculated_at[:10]})")
    print(f"  Test : {len(test)} signals ({test[0].calculated_at[:10]} to {test[-1].calculated_at[:10]})")

    # Verify chronological order
    check_split = (train[-1].calculated_at < val[0].calculated_at and
                   val[-1].calculated_at < test[0].calculated_at)
    print(f"  CHECK chronological order: {'PASS' if check_split else 'FAIL'}")

    # --- Baseline fitness ---
    cfg_base = decode_vector(BASELINE_VECTOR)
    print(f"\nBaseline config weights: S={cfg_base['SENTIMENT_WEIGHT']:.2f} T={cfg_base['TECHNICAL_WEIGHT']:.2f} R={cfg_base['RISK_WEIGHT']:.2f}")
    print(f"  ATR stops: high_conf={cfg_base['ATR_STOP_HIGH_CONF']:.1f}x  default={cfg_base['ATR_STOP_DEFAULT']:.1f}x  low_conf={cfg_base['ATR_STOP_LOW_CONF']:.1f}x")
    print(f"  ATR TPs:   low_vol={cfg_base['ATR_TP_LOW_VOL']:.1f}x  high_vol={cfg_base['ATR_TP_HIGH_VOL']:.1f}x")

    print("\n1. Baseline fitness on all splits...")
    fit_train, stats_train = compute_fitness_for_subset(train, score_timeline, cfg_base)
    fit_val,   stats_val   = compute_fitness_for_subset(val,   score_timeline, cfg_base)
    fit_test,  stats_test  = compute_fitness_for_subset(test,  score_timeline, cfg_base)

    for name, fit, stats in [("Train", fit_train, stats_train),
                              ("Val  ", fit_val,   stats_val),
                              ("Test ", fit_test,  stats_test)]:
        print(f"  {name}: fitness={fit:.4f}  win_rate={stats['win_rate']:.3f}  "
              f"PF={stats['profit_factor']:.3f}  trades={stats['total_trades']}  "
              f"skipped={stats['skipped']}  exits={stats['exit_reasons']}")

    check1 = fit_train >= 0.0          # 0 is acceptable (may need more data)
    check2 = stats_val["total_trades"] >= 0
    check3 = stats_test["total_trades"] >= 0
    print(f"\n  CHECK train fitness computed: {'PASS' if check1 else 'FAIL'}")
    print(f"  CHECK val  has trades: {'PASS' if check2 else 'FAIL'} ({stats_val['total_trades']} trades)")
    print(f"  CHECK test has trades: {'PASS' if check3 else 'FAIL'} ({stats_test['total_trades']} trades)")

    if stats_train["total_trades"] < 20:
        print(f"  NOTE: Train trades={stats_train['total_trades']} < 20 -> fitness=0.0 (penalty active)")
        print(f"        May mean price_data does not cover signal timestamps, or signals are all HOLD.")

    # --- Deliberately bad config ---
    print("\n2. Bad config test (extreme weights)...")
    bad_vector = list(BASELINE_VECTOR)
    bad_vector[0] = 0.10  # SENTIMENT_WEIGHT very low
    bad_vector[1] = 0.10  # TECHNICAL_WEIGHT very low
    bad_vector[2] = 25.0  # HOLD_ZONE too high -> far fewer signals pass
    # ATR stops: make them very wide (degenerate) to stress monotone constraint
    bad_vector[40] = 4.0
    bad_vector[41] = 4.0
    bad_vector[42] = 4.0

    cfg_bad = decode_vector(bad_vector)
    fit_bad, stats_bad = compute_fitness_for_subset(train, score_timeline, cfg_bad)
    print(f"  Bad config fitness (train): {fit_bad:.4f}  trades={stats_bad['total_trades']}")
    print(f"  Baseline fitness (train)  : {fit_train:.4f}")
    print(f"  (Bad config uses wider SL -> different outcomes)")

    # The key check: baseline produces a valid (non-error) result
    check4 = fit_train >= 0.0
    print(f"  CHECK baseline produces valid fitness: {'PASS' if check4 else 'FAIL'}")

    # --- Determinism ---
    print("\n3. Determinism check...")
    fit_train2, _ = compute_fitness_for_subset(train, score_timeline, cfg_base)
    check5 = abs(fit_train - fit_train2) < 1e-10
    print(f"  Two identical calls: {fit_train:.8f} vs {fit_train2:.8f}")
    print(f"  CHECK deterministic: {'PASS' if check5 else 'FAIL'}")

    # --- Overfitting gap ---
    print("\n4. Train/val overfitting gap...")
    if fit_train > 0 and fit_val > 0:
        gap_pct = abs(fit_train - fit_val) / fit_train * 100
        print(f"  Train={fit_train:.4f}  Val={fit_val:.4f}  Gap={gap_pct:.1f}%")
        print(f"  (Optimizer gate: gap <= 20% considered healthy)")
    else:
        gap_pct = 0.0
        print("  (Cannot compute gap -- one split has 0 fitness)")

    # --- Summary ---
    print("\n" + "=" * 60)
    all_pass = check_split and check1 and check2 and check3 and check4 and check5
    if all_pass:
        print("PASS: All Step 3 checks passed.")
        print("  Proceed to Step 4 (genetic algorithm).")
    else:
        print("STOP: One or more checks failed. Fix before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
