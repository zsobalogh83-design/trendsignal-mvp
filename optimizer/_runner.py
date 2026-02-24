"""
TrendSignal Self-Tuning Engine - Subprocess Runner

This script is launched as an isolated subprocess by optimizer_api.py.
It runs the full optimization pipeline and saves results to the DB.

Usage (called by optimizer_api.py, not directly):
    python optimizer/_runner.py
        --run-id      <int>
        --population  <int>
        --generations <int>
        --crossover   <float>
        --mutation    <float>
        --stop-flag   <path>

Version: 1.0
Date: 2026-02-23
"""

import argparse
import json
import sqlite3
import sys
import traceback
from pathlib import Path

# Project root on path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from optimizer.backtester import load_signal_rows, load_trade_outcomes
from optimizer.fitness import split_rows, compute_fitness_for_subset
from optimizer.genetic import run_optimizer
from optimizer.parameter_space import decode_vector, vector_to_config_diff, BASELINE_VECTOR
from optimizer.validation import (
    bootstrap_test,
    walk_forward_validation,
    regime_breakdown,
    check_acceptance_gates,
    gates_verdict,
    _get_active_pnls,
)

DATABASE_PATH = BASE_DIR / "trendsignal.db"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _mark_run_complete(run_id: int, elapsed: float, proposals_count: int, db_path: Path):
    conn = _db(db_path)
    conn.execute("""
        UPDATE optimization_runs SET
            status              = 'COMPLETED',
            completed_at        = CURRENT_TIMESTAMP,
            duration_seconds    = ?,
            proposals_generated = ?
        WHERE id = ?
    """, (elapsed, proposals_count, run_id))
    conn.commit()
    conn.close()


def _mark_run_stopped(run_id: int, elapsed: float, proposals_count: int, db_path: Path):
    conn = _db(db_path)
    conn.execute("""
        UPDATE optimization_runs SET
            status              = 'STOPPED',
            completed_at        = CURRENT_TIMESTAMP,
            duration_seconds    = ?,
            proposals_generated = ?
        WHERE id = ?
    """, (elapsed, proposals_count, run_id))
    conn.commit()
    conn.close()


def _mark_run_failed(run_id: int, error_msg: str, db_path: Path):
    conn = _db(db_path)
    conn.execute("""
        UPDATE optimization_runs SET
            status        = 'FAILED',
            completed_at  = CURRENT_TIMESTAMP,
            error_message = ?
        WHERE id = ?
    """, (error_msg[:2000], run_id))
    conn.commit()
    conn.close()


def _save_proposal(run_id: int, proposal: dict, validation: dict, db_path: Path) -> int:
    """
    Insert one fully-validated proposal into config_proposals.
    Returns the new proposal id.
    """
    boot   = validation.get("bootstrap", {})
    wf     = validation.get("walk_forward", {})
    regime = validation.get("regime", {})
    gates  = validation.get("gates", {})
    verdict_str, verdict_reason = validation.get("verdict", ("REJECTED", "No verdict"))

    # Regime PF values
    regime_trending = regime.get("trending", {})
    regime_sideways = regime.get("sideways", {})
    regime_highvol  = regime.get("high_vol", {})

    # Gate booleans
    def gate_ok(name):
        g = gates.get(name, {})
        return 1 if g.get("passed", False) else 0

    conn = _db(db_path)
    cur = conn.execute("""
        INSERT INTO config_proposals (
            run_id, rank,
            train_fitness, val_fitness, test_fitness,
            baseline_fitness, fitness_improvement_pct,
            test_trade_count, test_win_rate, test_profit_factor, baseline_profit_factor,
            train_val_gap, overfitting_ok,
            bootstrap_p_value, bootstrap_significant, bootstrap_iterations,
            wf_window_count, wf_positive_count, wf_result_json, wf_consistent,
            regime_trending_pf, regime_trending_trades,
            regime_sideways_pf, regime_sideways_trades,
            regime_highvol_pf,  regime_highvol_trades,
            gate_min_trades_ok, gate_fitness_improvement_ok,
            gate_bootstrap_ok, gate_overfitting_ok, gate_profit_factor_ok, gate_sideways_pf_ok,
            verdict, verdict_reason,
            config_vector_json, config_diff_json
        ) VALUES (
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?,
            ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?
        )
    """, (
        run_id,
        proposal["rank"],
        proposal["train_fitness"],
        proposal["val_fitness"],
        proposal["test_fitness"],
        proposal["baseline_fitness"],
        proposal["fitness_improvement_pct"],
        proposal["test_trade_count"],
        proposal.get("test_win_rate"),
        proposal["test_profit_factor"],
        proposal["baseline_profit_factor"],
        proposal["train_val_gap"],
        proposal["overfitting_ok"],
        # Bootstrap
        boot.get("p_value"),
        1 if boot.get("significant", False) else 0,
        boot.get("n_iterations", 1000),
        # Walk-forward
        wf.get("window_count"),
        wf.get("positive_count"),
        json.dumps(wf.get("windows", [])),
        1 if wf.get("consistent", False) else 0,
        # Regime
        regime_trending.get("profit_factor"),
        regime_trending.get("trade_count"),
        regime_sideways.get("profit_factor"),
        regime_sideways.get("trade_count"),
        regime_highvol.get("profit_factor"),
        regime_highvol.get("trade_count"),
        # Gates
        gate_ok("min_trades"),
        gate_ok("fitness_improvement"),
        gate_ok("bootstrap"),
        gate_ok("overfitting"),
        gate_ok("profit_factor"),
        gate_ok("sideways_regime"),
        # Verdict
        verdict_str,
        verdict_reason,
        # Config
        json.dumps(proposal["vector"]),
        json.dumps(proposal.get("config_diff", {})),
    ))
    proposal_id = cur.lastrowid
    conn.commit()
    conn.close()
    return proposal_id


# ---------------------------------------------------------------------------
# Proposal validation
# ---------------------------------------------------------------------------

def _validate_and_save_proposals(
    result: dict,
    run_id: int,
    all_rows,
    score_timeline: dict,
    test_rows,
    db_path: Path,
) -> int:
    """
    Run full validation pipeline on each proposal from the GA result,
    save to config_proposals table. Returns count of saved proposals.
    Uses v2 SignalSimRow pipeline throughout.
    """
    cfg_baseline = decode_vector(BASELINE_VECTOR)
    baseline_pnls_test = _get_active_pnls(test_rows, score_timeline, cfg_baseline)

    saved = 0
    for proposal in result.get("proposals", []):
        print(f"\n[Runner] Validating proposal rank={proposal['rank']}...")

        prop_vector = proposal["vector"]
        prop_cfg    = decode_vector(prop_vector)

        # --- Bootstrap ---
        prop_pnls = _get_active_pnls(test_rows, score_timeline, prop_cfg)
        boot = bootstrap_test(baseline_pnls_test, prop_pnls, n_iterations=1000)
        print(f"  Bootstrap: p={boot['p_value']:.4f}  significant={boot['significant']}")

        # --- Walk-forward (on full dataset) ---
        wf = {}
        if len(all_rows) >= 100:
            wf = walk_forward_validation(
                all_rows, score_timeline, prop_cfg, cfg_baseline, n_windows=5
            )
            print(f"  Walk-forward: {wf['positive_count']}/{wf['window_count']} positive  "
                  f"status={wf.get('status', '?')}")
        else:
            print(f"  Walk-forward: SKIP (only {len(all_rows)} rows)")

        # --- Regime breakdown ---
        regime = regime_breakdown(all_rows, score_timeline, prop_cfg)
        for rname, rdata in regime.items():
            print(f"  Regime {rname}: PF={rdata['profit_factor']}  "
                  f"trades={rdata['trade_count']}")

        # --- Enrich proposal with bootstrap results ---
        proposal["bootstrap_significant"] = boot["significant"]
        proposal["bootstrap_p_value"]     = boot["p_value"]
        proposal["regime_sideways_pf"]    = regime.get("sideways", {}).get("profit_factor")

        # --- Acceptance gates ---
        baseline_data = {
            "test_fitness":       proposal["baseline_fitness"],
            "test_profit_factor": proposal["baseline_profit_factor"],
            "test_trade_count":   proposal.get("test_trade_count", 0),
        }
        gates = check_acceptance_gates(proposal, baseline_data)
        verdict_str, verdict_reason = gates_verdict(gates)

        print(f"  Gates:")
        for gname, gdata in gates.items():
            icon = "PASS" if gdata["passed"] else ("WARN" if not gdata["required"] else "FAIL")
            print(f"    [{icon}] {gname}: {gdata['value']} (threshold: {gdata['threshold']})")
        print(f"  Verdict: {verdict_str} -- {verdict_reason}")

        # --- Save to DB ---
        validation = {
            "bootstrap":    boot,
            "walk_forward": wf,
            "regime":       regime,
            "gates":        gates,
            "verdict":      (verdict_str, verdict_reason),
        }

        proposal_id = _save_proposal(run_id, proposal, validation, db_path)
        print(f"  Saved as config_proposals.id={proposal_id}")
        saved += 1

    return saved


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _create_run_record(db_path: Path, population: int, generations: int,
                       crossover: float, mutation: float) -> int:
    """
    Insert a new RUNNING record into optimization_runs and return its id.
    Used when _runner.py is launched manually (without --run-id).
    """
    conn = _db(db_path)
    cur = conn.execute("""
        INSERT INTO optimization_runs
            (status, population_size, max_generations, dimensions,
             crossover_prob, mutation_prob, tournament_size)
        VALUES ('RUNNING', ?, ?, 46, ?, ?, 3)
    """, (population, generations, crossover, mutation))
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def main():
    parser = argparse.ArgumentParser(description="TrendSignal Optimizer Runner")
    parser.add_argument("--run-id",      type=int,   default=None,
                        help="DB run id (auto-created if omitted — use for manual launch)")
    parser.add_argument("--population",  type=int,   default=80)
    parser.add_argument("--generations", type=int,   default=100)
    parser.add_argument("--crossover",   type=float, default=0.70)
    parser.add_argument("--mutation",    type=float, default=0.20)
    parser.add_argument("--stop-flag",   type=str,   default=None)
    parser.add_argument("--db-path",     type=str,   default=str(DATABASE_PATH))
    args = parser.parse_args()

    db_path   = Path(args.db_path)
    stop_flag = Path(args.stop_flag) if args.stop_flag else None

    # Auto-create DB record when launched manually (no --run-id supplied)
    if args.run_id is None:
        run_id = _create_run_record(
            db_path, args.population, args.generations,
            args.crossover, args.mutation,
        )
        print(f"[Runner] Created new optimization_runs record: id={run_id}")
    else:
        run_id = args.run_id

    print("=" * 60)
    print(f"TrendSignal Optimizer - run_id={run_id}")
    print(f"  Population:  {args.population}")
    print(f"  Generations: {args.generations}")
    print(f"  Crossover:   {args.crossover}")
    print(f"  Mutation:    {args.mutation}")
    print(f"  DB:          {db_path}")
    print(f"  Stop flag:   {stop_flag}")
    print("=" * 60)

    import time
    t_start = time.time()

    try:
        # Run genetic optimizer
        result = run_optimizer(
            run_id=run_id,
            population_size=args.population,
            max_generations=args.generations,
            crossover_prob=args.crossover,
            mutation_prob=args.mutation,
            stop_flag_path=stop_flag,
            db_path=db_path,
        )

        elapsed = time.time() - t_start

        print(f"\n[Runner] GA complete in {elapsed:.0f}s")
        print(f"  Best train fitness: {result['best_train_fitness']:.4f}")
        print(f"  Best val fitness:   {result['best_val_fitness']:.4f}")
        print(f"  Generations run:    {result['generations_run']}")
        print(f"  Proposals to save:  {len(result['proposals'])}")

        # Load split data for validation (reuse the same split, v2 pipeline)
        from optimizer.signal_data import load_all_sim_data
        all_rows, score_timeline = load_all_sim_data(db_path)
        _, _, test_rows = split_rows(all_rows)

        # Validate and save proposals
        saved = _validate_and_save_proposals(
            result, run_id, all_rows, score_timeline, test_rows, db_path
        )
        print(f"\n[Runner] Saved {saved} proposal(s) to config_proposals.")

        # Check if run was stopped vs completed
        was_stopped = stop_flag and stop_flag.exists()
        if was_stopped:
            _mark_run_stopped(run_id, elapsed, saved, db_path)
            print(f"[Runner] Run {run_id} marked STOPPED.")
        else:
            _mark_run_complete(run_id, elapsed, saved, db_path)
            print(f"[Runner] Run {run_id} marked COMPLETED.")

        # Update baseline fitness on run record
        conn = _db(db_path)
        conn.execute(
            "UPDATE optimization_runs SET baseline_fitness=?, best_test_fitness=? WHERE id=?",
            (result.get("baseline_fitness"), result.get("best_train_fitness"), run_id)
        )
        conn.commit()
        conn.close()

        print("\n[Runner] Done.")
        sys.exit(0)

    except Exception as exc:
        elapsed = time.time() - t_start
        tb = traceback.format_exc()
        print(f"\n[Runner] FATAL ERROR after {elapsed:.0f}s:\n{tb}", file=sys.stderr)
        try:
            _mark_run_failed(run_id, str(exc), db_path)
        except Exception as db_exc:
            print(f"[Runner] Failed to mark run as FAILED: {db_exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
