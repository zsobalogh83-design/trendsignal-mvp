"""
TrendSignal BCD Optimizer - Subprocess Runner

Launched as an isolated subprocess by bcd_api.py.
Runs the full BCD optimization pipeline and saves results to the DB.

Usage (called by bcd_api.py, not directly):
    python optimizer/_bcd_process.py
        --run-id      <int>
        --max-rounds  <int>       default: 60
        --max-dims    <int>       default: 7
        --patience    <int>       default: 12
        --mini-pop    <int>       default: 40
        --mini-gen    <int>       default: 60
        --stop-flag   <path>
        --db-path     <path>

Version: 1.0
Date: 2026-03-07
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

# Project root on path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from optimizer.bcd_runner import run_bcd_optimizer, _db
from optimizer.fitness import split_rows, compute_fitness_for_subset
from optimizer.parameter_space import decode_vector, BASELINE_VECTOR
from optimizer.signal_data import load_all_sim_data

# Reuse the validation + DB helpers from _runner.py
from optimizer._runner import (
    _mark_run_complete,
    _mark_run_stopped,
    _mark_run_failed,
    _validate_and_save_proposals,
)

DATABASE_PATH = BASE_DIR / "trendsignal.db"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _create_bcd_run_record(
    db_path: Path,
    max_rounds: int,
    max_dims: int,
    patience: int,
    mini_pop: int,
    mini_gen: int,
) -> int:
    """
    Insert a new RUNNING BCD record into optimization_runs.
    Used when the process is launched without --run-id (manual launch).
    """
    conn = _db(db_path)
    cur = conn.execute("""
        INSERT INTO optimization_runs
            (status, run_type, population_size, max_generations, dimensions,
             crossover_prob, mutation_prob, tournament_size)
        VALUES ('RUNNING', 'BCD', ?, ?, 52, 0.70, 0.20, 3)
    """, (mini_pop, max_rounds))
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def _save_block_impact(run_id: int, block_impact: dict, db_path: Path):
    """Persist the block impact summary as JSON in optimization_runs."""
    conn = _db(db_path)
    try:
        impact_json = json.dumps(
            {k: round(v["total_improvement"], 4) for k, v in block_impact.items()}
        )
        conn.execute(
            "UPDATE optimization_runs SET bcd_block_impact = ? WHERE id = ?",
            (impact_json, run_id),
        )
        conn.commit()
    except Exception as e:
        print(f"[BCD Runner] Block impact save warning: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TrendSignal BCD Optimizer Runner")
    parser.add_argument("--run-id",     type=int,   default=None,
                        help="DB run id (auto-created if omitted)")
    parser.add_argument("--max-rounds", type=int,   default=60,
                        help="Maximum BCD rounds (default: 60)")
    parser.add_argument("--max-dims",   type=int,   default=7,
                        help="Max active dims per round (default: 7)")
    parser.add_argument("--patience",   type=int,   default=12,
                        help="Rounds without improvement before stopping (default: 12)")
    parser.add_argument("--mini-pop",   type=int,   default=40,
                        help="Mini GA population size (default: 40)")
    parser.add_argument("--mini-gen",   type=int,   default=60,
                        help="Mini GA generations per round (default: 60)")
    parser.add_argument("--stop-flag",  type=str,   default=None,
                        help="Path to graceful-stop flag file")
    parser.add_argument("--db-path",    type=str,   default=str(DATABASE_PATH),
                        help="SQLite database path")
    args = parser.parse_args()

    db_path   = Path(args.db_path)
    stop_flag = Path(args.stop_flag) if args.stop_flag else None

    # Auto-create DB record when launched manually
    if args.run_id is None:
        run_id = _create_bcd_run_record(
            db_path,
            args.max_rounds, args.max_dims,
            args.patience, args.mini_pop, args.mini_gen,
        )
        print(f"[BCD Runner] Created new optimization_runs record: id={run_id}")
    else:
        run_id = args.run_id

    print("=" * 60)
    print(f"TrendSignal BCD Optimizer - run_id={run_id}")
    print(f"  Max rounds:  {args.max_rounds}")
    print(f"  Max dims:    {args.max_dims}")
    print(f"  Patience:    {args.patience}")
    print(f"  Mini pop:    {args.mini_pop}")
    print(f"  Mini gen:    {args.mini_gen}")
    print(f"  DB:          {db_path}")
    print(f"  Stop flag:   {stop_flag}")
    print("=" * 60)

    t_start = time.time()

    try:
        # Run BCD optimizer
        result = run_bcd_optimizer(
            run_id=run_id,
            max_rounds=args.max_rounds,
            max_dims_per_round=args.max_dims,
            patience=args.patience,
            mini_pop=args.mini_pop,
            mini_gen=args.mini_gen,
            stop_flag_path=stop_flag,
            db_path=db_path,
        )

        elapsed = time.time() - t_start

        print(f"\n[BCD Runner] BCD complete in {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"  Rounds run:        {result['rounds_run']}")
        print(f"  Baseline fitness:  {result['baseline_fitness']:.4f}")
        print(f"  Final fitness:     {result['final_fitness']:.4f}")
        print(f"  Proposals to save: {len(result['proposals'])}")

        # Full block impact summary
        print(f"\n[BCD Runner] Block impact summary:")
        for uid, st in result["block_impact"].items():
            accepted_str = f"({st['rounds_accepted']}/{st['rounds_selected']} accepted)"
            print(
                f"  {uid:8s}  {accepted_str:20s}  "
                f"cumulative={st['total_improvement']:+.3f}%"
            )

        # Save block impact to DB
        _save_block_impact(run_id, result["block_impact"], db_path)

        # Validate and save proposals (reuse _runner.py pipeline)
        all_rows, score_timeline = load_all_sim_data(db_path)
        _, _, test_rows = split_rows(all_rows)

        saved = _validate_and_save_proposals(
            result, run_id, all_rows, score_timeline, test_rows, db_path
        )
        print(f"\n[BCD Runner] Saved {saved} proposal(s) to config_proposals.")

        # Update baseline & test fitness on run record
        conn = _db(db_path)
        conn.execute(
            """UPDATE optimization_runs SET
                baseline_fitness  = ?,
                best_val_fitness  = ?,
                best_test_fitness = ?
               WHERE id = ?""",
            (
                result["baseline_fitness"],
                result["best_val_fitness"],
                result["proposals"][0]["test_fitness"] if result["proposals"] else None,
                run_id,
            ),
        )
        conn.commit()
        conn.close()

        was_stopped = stop_flag and stop_flag.exists()
        if was_stopped:
            _mark_run_stopped(run_id, elapsed, saved, db_path)
            print(f"[BCD Runner] Run {run_id} marked STOPPED.")
        else:
            _mark_run_complete(run_id, elapsed, saved, db_path)
            print(f"[BCD Runner] Run {run_id} marked COMPLETED.")

        print("\n[BCD Runner] Done.")
        sys.exit(0)

    except Exception as exc:
        elapsed = time.time() - t_start
        tb = traceback.format_exc()
        print(
            f"\n[BCD Runner] FATAL ERROR after {elapsed:.0f}s:\n{tb}",
            file=sys.stderr,
        )
        try:
            _mark_run_failed(run_id, str(exc), db_path)
        except Exception as db_exc:
            print(f"[BCD Runner] Failed to mark run as FAILED: {db_exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
