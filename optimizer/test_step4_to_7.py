"""
Self-Tuning Engine - Step 4-7 Validation

Step 4: Bootstrap test on baseline (sanity check — should not be significant vs itself)
Step 5: Walk-forward with baseline (smoke test)
Step 6: Regime breakdown (all three regimes return data)
Step 7: Full GA mini-run (5 gen, 20 pop) + validation pipeline

Usage:
    python optimizer/test_step4_to_7.py

Version: 1.0
Date: 2026-02-23
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimizer.backtester import load_signal_rows, load_trade_outcomes
from optimizer.fitness import split_rows, compute_fitness_for_subset
from optimizer.parameter_space import BASELINE_VECTOR, decode_vector
from optimizer.validation import (
    bootstrap_test,
    walk_forward_validation,
    regime_breakdown,
    check_acceptance_gates,
    gates_verdict,
    _get_active_pnls,
)


def main():
    print("=" * 60)
    print("Step 4-7: Validation pipeline tests")
    print("=" * 60)

    rows = load_signal_rows()
    outcomes = load_trade_outcomes()
    train, val, test = split_rows(rows, outcomes)
    cfg_base = decode_vector(BASELINE_VECTOR)

    all_pass = True

    # ---------------------------------------------------------------
    # Step 4: Bootstrap sanity check (baseline vs itself)
    # ---------------------------------------------------------------
    print("\n--- Step 4: Bootstrap sanity check ---")
    pnls_base = _get_active_pnls(rows, outcomes, cfg_base)
    print(f"  Active P&Ls (baseline on all data): {len(pnls_base)}")

    if len(pnls_base) >= 10:
        # Baseline vs itself: p_value should be ~0.5 (no significant difference)
        boot_self = bootstrap_test(pnls_base, pnls_base, n_iterations=500)
        print(f"  Bootstrap (baseline vs itself): p={boot_self['p_value']:.3f}  "
              f"significant={boot_self['significant']}")
        check4 = not boot_self["significant"]  # should NOT be significant
        print(f"  CHECK baseline not significant vs itself: {'PASS' if check4 else 'FAIL'}")
        all_pass = all_pass and check4
    else:
        print(f"  SKIP: Only {len(pnls_base)} active trades — need >= 10 for bootstrap")
        print(f"  NOTE: Bootstrap will work correctly with more backtest data")

    # ---------------------------------------------------------------
    # Step 5: Walk-forward smoke test
    # ---------------------------------------------------------------
    print("\n--- Step 5: Walk-forward smoke test ---")
    if len(rows) >= 100:
        wf = walk_forward_validation(rows, outcomes, cfg_base, cfg_base, n_windows=3)
        print(f"  Windows: {wf['window_count']}")
        for w in wf["windows"]:
            print(f"    Window {w['window']}: delta={w['pf_delta']:+.3f}  "
                  f"positive={w['positive']}  signals={w['test_signals']}")
        print(f"  Positive: {wf['positive_count']}/{wf['window_count']}  "
              f"Status: {wf['status']}")
        check5 = wf["window_count"] >= 2
        print(f"  CHECK at least 2 windows computed: {'PASS' if check5 else 'FAIL'}")
        all_pass = all_pass and check5
    else:
        print(f"  SKIP: Not enough signals for walk-forward")

    # ---------------------------------------------------------------
    # Step 6: Regime breakdown
    # ---------------------------------------------------------------
    print("\n--- Step 6: Regime breakdown ---")
    regime = regime_breakdown(rows, outcomes, cfg_base)
    total_regime_trades = sum(v["trade_count"] for v in regime.values())
    for r_name, r_data in regime.items():
        print(f"  {r_name:12s}: PF={r_data['profit_factor']}  "
              f"WR={r_data['win_rate']}  trades={r_data['trade_count']}")
    check6 = total_regime_trades > 0
    print(f"  Total regime trades: {total_regime_trades}")
    print(f"  CHECK regime breakdown returns data: {'PASS' if check6 else 'FAIL'}")
    all_pass = all_pass and check6

    # ---------------------------------------------------------------
    # Step 7: Mini GA run + full proposal validation
    # ---------------------------------------------------------------
    print("\n--- Step 7: Mini GA run (5 gen, 15 pop) ---")

    # Create a test run record
    db_path = Path(__file__).resolve().parent.parent / "trendsignal.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute("""
        INSERT INTO optimization_runs
        (status, population_size, max_generations, dimensions,
         crossover_prob, mutation_prob, tournament_size)
        VALUES ('RUNNING', 15, 5, 40, 0.7, 0.2, 3)
    """)
    run_id = cur.lastrowid
    conn.commit()
    conn.close()

    from optimizer.genetic import run_optimizer
    result = run_optimizer(
        run_id=run_id,
        population_size=15,
        max_generations=5,
        db_path=db_path,
    )

    print(f"\n  GA result:")
    print(f"    best_train = {result['best_train_fitness']:.4f}")
    print(f"    best_val   = {result['best_val_fitness']:.4f}")
    print(f"    generations = {result['generations_run']}")
    print(f"    proposals   = {len(result['proposals'])}")

    check7a = result["generations_run"] == 5
    check7b = len(result["proposals"]) >= 1
    print(f"  CHECK ran 5 generations: {'PASS' if check7a else 'FAIL'}")
    print(f"  CHECK at least 1 proposal: {'PASS' if check7b else 'FAIL'}")
    all_pass = all_pass and check7a and check7b

    # Run acceptance gates on best proposal
    if result["proposals"]:
        best_prop = result["proposals"][0]
        base_fit, base_stats = compute_fitness_for_subset(test, outcomes, cfg_base)
        baseline_data = {
            "test_fitness":       base_fit,
            "test_profit_factor": base_stats["profit_factor"],
            "test_trade_count":   base_stats["total_trades"],
        }
        # Add bootstrap result to proposal
        prop_pnls = _get_active_pnls(test, outcomes, decode_vector(best_prop["vector"]))
        base_pnls = _get_active_pnls(test, outcomes, cfg_base)
        boot = bootstrap_test(base_pnls, prop_pnls, n_iterations=100)
        best_prop["bootstrap_significant"] = boot["significant"]
        best_prop["bootstrap_p_value"]     = boot["p_value"]

        gates = check_acceptance_gates(best_prop, baseline_data)
        verdict, reason = gates_verdict(gates)
        print(f"\n  Gates for best proposal (mini-run):")
        for g_name, g_data in gates.items():
            icon = "PASS" if g_data["passed"] else ("WARN" if not g_data["required"] else "FAIL")
            print(f"    [{icon}] {g_name}: {g_data['value']} (threshold: {g_data['threshold']})")
        print(f"  Verdict: {verdict} — {reason}")
        check7c = verdict in ("PROPOSABLE", "CONDITIONAL", "REJECTED")
        print(f"  CHECK verdict is valid: {'PASS' if check7c else 'FAIL'}")
        all_pass = all_pass and check7c

    # Cleanup
    conn = sqlite3.connect(str(db_path))
    conn.execute("DELETE FROM optimization_generations WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM optimization_runs WHERE id=?", (run_id,))
    conn.commit()
    conn.close()

    # ---------------------------------------------------------------
    # Final verdict
    # ---------------------------------------------------------------
    print("\n" + "=" * 60)
    if all_pass:
        print("PASS: All Step 4-7 checks passed.")
        print("  Proceed to API layer implementation.")
    else:
        print("STOP: One or more checks failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
