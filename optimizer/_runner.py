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
from optimizer.parameter_space import decode_vector, vector_to_config_diff, BASELINE_VECTOR, get_current_baseline_vector
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


def _ensure_cycle_columns(db_path: Path):
    """DB migration: cycle tracking mezők hozzáadása, ha még nem léteznek."""
    conn = _db(db_path)
    for sql in [
        "ALTER TABLE optimization_runs ADD COLUMN current_cycle INTEGER DEFAULT 1",
        "ALTER TABLE optimization_runs ADD COLUMN max_cycles INTEGER DEFAULT 1",
        "ALTER TABLE config_proposals ADD COLUMN cycle INTEGER DEFAULT 1",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # mező már létezik
    conn.close()


def _update_run_cycle(run_id: int, current_cycle: int, db_path: Path):
    """Frissíti a futó ciklus számát a DB-ben (progress polling számára)."""
    conn = _db(db_path)
    conn.execute(
        "UPDATE optimization_runs SET current_cycle=? WHERE id=?",
        (current_cycle, run_id)
    )
    conn.commit()
    conn.close()


def _save_proposal(run_id: int, proposal: dict, validation: dict, db_path: Path,
                   cycle: int = 1) -> int:
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
            run_id, rank, cycle,
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
            ?, ?, ?,
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
        cycle,
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
    cycle: int = 1,
) -> tuple:
    """
    Run full validation pipeline on each proposal from the GA result,
    save to config_proposals table.
    Returns (saved_count, has_acceptable) where has_acceptable=True if
    at least one proposal has verdict PROPOSABLE or CONDITIONAL.
    Uses v2 SignalSimRow pipeline throughout.

    test_rows: gate_test_rows = val + test (50% held-out).
    A GA csak a train seten optimalizált; val+test együtt érvényes
    held-out halmaz → megbízhatóbb gate statisztikák, több trade.
    Az itt kiszámított test metrikák felülírják a genetic.py-ból jövő
    20%-os test értékeket, mivel ott csak a kis test szett szerepelt.
    """
    # Mindig az aktuális config.json-ból olvassuk a baseline-t,
    # nem a hardcoded BASELINE_VECTOR-ból (ami elavult lehet).
    current_baseline_vector = get_current_baseline_vector()
    cfg_baseline = decode_vector(current_baseline_vector)

    # Baseline metrikák a gate_test_rows-on (val+test = 50% held-out)
    baseline_pnls_test = _get_active_pnls(test_rows, score_timeline, cfg_baseline)
    baseline_gate_fit, baseline_gate_stats = compute_fitness_for_subset(
        test_rows, score_timeline, cfg_baseline
    )
    print(f"[Runner] Baseline on gate set (val+test): "
          f"fit={baseline_gate_fit:.4f}  "
          f"trades={baseline_gate_stats['total_trades']}  "
          f"PF={baseline_gate_stats['profit_factor']:.2f}")

    saved = 0
    has_acceptable = False
    for proposal in result.get("proposals", []):
        print(f"\n[Runner] Validating proposal rank={proposal['rank']} (cycle {cycle})...")

        prop_vector = proposal["vector"]
        prop_cfg    = decode_vector(prop_vector)

        # --- Gate metrikák újraszámolása val+test kombinált halmazon ---
        # A genetic.py-ból jövő test_fitness/test_trade_count csak a 20%-os
        # test szettből számolt → kis minta, nagy variancia.
        # A gate_test_rows (val+test = 50%) megbízhatóbb képet ad.
        gate_fit, gate_stats = compute_fitness_for_subset(
            test_rows, score_timeline, prop_cfg
        )
        improvement_pct = (
            (gate_fit - baseline_gate_fit) / baseline_gate_fit * 100
            if baseline_gate_fit > 0 else 0.0
        )
        print(f"  Gate set (val+test): fit={gate_fit:.4f}  "
              f"trades={gate_stats['total_trades']}  "
              f"PF={gate_stats['profit_factor']:.2f}  "
              f"improvement={improvement_pct:+.1f}%")

        # A proposal test metrikáit felülírjuk a kombinált halmaz értékeivel
        proposal["test_fitness"]            = round(gate_fit, 6)
        proposal["test_trade_count"]        = gate_stats["total_trades"]
        proposal["test_win_rate"]           = gate_stats["win_rate"]
        proposal["test_profit_factor"]      = gate_stats["profit_factor"]
        proposal["baseline_fitness"]        = round(baseline_gate_fit, 6)
        proposal["baseline_profit_factor"]  = baseline_gate_stats["profit_factor"]
        proposal["fitness_improvement_pct"] = round(improvement_pct, 2)

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

        proposal_id = _save_proposal(run_id, proposal, validation, db_path, cycle=cycle)
        print(f"  Saved as config_proposals.id={proposal_id}")
        saved += 1
        if verdict_str in ("PROPOSABLE", "CONDITIONAL"):
            has_acceptable = True

    return saved, has_acceptable


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
        VALUES ('RUNNING', ?, ?, 47, ?, ?, 3)
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
    parser.add_argument("--trade-mode",  type=str,   default="all",
                        choices=["all", "long", "short"],
                        help="all=minden irány, long=csak BUY, short=csak SELL")
    parser.add_argument("--phase",       type=str,   default="all",
                        choices=["all", "score_only", "thresholds_only"],
                        help="all=teljes tér, score_only=küszöbök befagyasztva, "
                             "thresholds_only=score-params befagyasztva")
    parser.add_argument("--include-archive", action="store_true", default=False,
                        help="Archive CLOSED trade jelzések bevonása a tanítóadatba")
    parser.add_argument("--max-cycles",  type=int, default=1,
                        help="Max ismétlési ciklus (1=nincs ismétlés, max 10). "
                             "Addig ismétli a futást, amíg PROPOSABLE vagy CONDITIONAL "
                             "javaslat születik, vagy eléri a maximumot.")
    args = parser.parse_args()

    max_cycles = max(1, min(10, args.max_cycles))
    db_path    = Path(args.db_path)
    stop_flag  = Path(args.stop_flag) if args.stop_flag else None

    # DB migration: cycle mezők hozzáadása ha szükséges
    _ensure_cycle_columns(db_path)

    # Auto-create DB record when launched manually (no --run-id supplied)
    if args.run_id is None:
        run_id = _create_run_record(
            db_path, args.population, args.generations,
            args.crossover, args.mutation,
        )
        print(f"[Runner] Created new optimization_runs record: id={run_id}")
    else:
        run_id = args.run_id

    # max_cycles mentése a DB-be (progress polling számára)
    conn = _db(db_path)
    conn.execute("UPDATE optimization_runs SET max_cycles=? WHERE id=?", (max_cycles, run_id))
    conn.commit()
    conn.close()

    print("=" * 60)
    print(f"TrendSignal Optimizer - run_id={run_id}")
    print(f"  Population:       {args.population}")
    print(f"  Generations:      {args.generations}")
    print(f"  Crossover:        {args.crossover}")
    print(f"  Mutation:         {args.mutation}")
    print(f"  Trade mode:       {args.trade_mode}")
    print(f"  Phase:            {args.phase}")
    print(f"  Include archive:  {args.include_archive}")
    print(f"  Max cycles:       {max_cycles}")
    print(f"  DB:               {db_path}")
    print(f"  Stop flag:        {stop_flag}")
    print("=" * 60)

    import time
    t_start  = time.time()
    total_saved = 0

    try:
        # Adat betöltés egyszer — minden ciklusban ugyanaz az adatkészlet
        from optimizer.signal_data import load_all_sim_data
        all_rows, score_timeline = load_all_sim_data(
            db_path,
            include_archive=args.include_archive,
            trade_mode=args.trade_mode,
        )
        _, val_rows, test_rows = split_rows(all_rows, random_seed=run_id)
        gate_test_rows = val_rows + test_rows

        last_result = None

        for cycle in range(1, max_cycles + 1):
            # Stop flag ellenőrzés ciklus előtt
            if stop_flag and stop_flag.exists():
                print(f"\n[Runner] Stop flag detected before cycle {cycle} — aborting.")
                break

            print(f"\n{'=' * 60}")
            print(f"[Runner] CYCLE {cycle}/{max_cycles}")
            print(f"{'=' * 60}")

            _update_run_cycle(run_id, cycle, db_path)

            # GA futtatás — minden ciklusban más véletlenszám mag
            result = run_optimizer(
                run_id=run_id,
                population_size=args.population,
                max_generations=args.generations,
                crossover_prob=args.crossover,
                mutation_prob=args.mutation,
                stop_flag_path=stop_flag,
                db_path=db_path,
                trade_mode=args.trade_mode,
                include_archive=args.include_archive,
                phase=args.phase,
                random_seed=run_id * 100 + cycle,
            )
            last_result = result

            elapsed = time.time() - t_start
            print(f"\n[Runner] Cycle {cycle} GA complete in {elapsed:.0f}s total")
            print(f"  Best train fitness: {result['best_train_fitness']:.4f}")
            print(f"  Best val fitness:   {result['best_val_fitness']:.4f}")
            print(f"  Generations run:    {result['generations_run']}")
            print(f"  Proposals to save:  {len(result['proposals'])}")

            # Validáció és mentés
            saved, has_acceptable = _validate_and_save_proposals(
                result, run_id, all_rows, score_timeline, gate_test_rows, db_path,
                cycle=cycle,
            )
            total_saved += saved
            print(f"\n[Runner] Cycle {cycle}: saved {saved} proposal(s), "
                  f"acceptable={'YES' if has_acceptable else 'NO'}")

            # Ha van elfogadható javaslat → megállunk
            if has_acceptable:
                print(f"[Runner] Acceptable proposal found in cycle {cycle} — stopping.")
                break

            # Ha nem az utolsó ciklus és nincs acceptable → folytatás
            if cycle < max_cycles:
                print(f"[Runner] All proposals REJECTED in cycle {cycle} — retrying "
                      f"({cycle + 1}/{max_cycles})...")

        # Futás lezárása
        elapsed = time.time() - t_start
        was_stopped = stop_flag and stop_flag.exists()

        if was_stopped:
            _mark_run_stopped(run_id, elapsed, total_saved, db_path)
            print(f"\n[Runner] Run {run_id} marked STOPPED.")
        else:
            _mark_run_complete(run_id, elapsed, total_saved, db_path)
            print(f"\n[Runner] Run {run_id} marked COMPLETED ({total_saved} proposals total).")

        # Baseline fitness frissítése az utolsó ciklus alapján
        if last_result:
            conn = _db(db_path)
            conn.execute(
                "UPDATE optimization_runs SET baseline_fitness=?, best_test_fitness=? WHERE id=?",
                (last_result.get("baseline_fitness"), last_result.get("best_train_fitness"), run_id)
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
