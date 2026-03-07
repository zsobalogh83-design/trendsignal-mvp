"""
TrendSignal BCD Optimizer - Block Coordinate Descent

Optimizes the 52-dimensional parameter space in small blocks (≤ 7 dims/round)
using a mini GA per round on randomly sampled atomic unit combinations.

Key advantages over full-space GA:
  - 7-dim search space is tractable with small pop/gen budgets
  - Block-level impact analysis shows which parameter groups matter most
  - Random atomic unit mixing avoids systematic local optima
  - Monotone convergence: current_best only updated on improvement

Algorithm:
  1. Initialize current_best = BASELINE_VECTOR
  2. Each round: sample random atomic units (≤ max_dims_per_round total dims)
  3. Run mini GA (pop=40, gen=60) on active dims only, rest frozen at current_best
  4. If improvement: update current_best, reset patience counter
  5. Stop when patience exhausted or max_rounds reached
  6. Final: evaluate on test set, run validation pipeline

Fitness formula (same as genetic.py v2.3.1):
  fitness = min(train_fit, val_fit)
  where train_fit = val_fit = win_rate × profit_factor

Version: 1.0
Date: 2026-03-07
"""

import json
import multiprocessing
import os
import random
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from deap import base, creator, tools

from optimizer.atomic_units import ATOMIC_UNITS, sample_active_dims
from optimizer.fitness import compute_fitness_for_subset, split_rows
from optimizer.parameter_space import (
    LOWER_BOUNDS, UPPER_BOUNDS, BASELINE_VECTOR, N_DIMS,
    decode_vector, vector_to_config_diff,
)
from optimizer.signal_data import load_all_sim_data

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"

_DEFAULT_WORKERS = max(1, os.cpu_count() - 1)


# ---------------------------------------------------------------------------
# DEAP setup — separate class names to avoid collision with genetic.py
# ---------------------------------------------------------------------------

if not hasattr(creator, "FitnessMaxBCD"):
    creator.create("FitnessMaxBCD", base.Fitness, weights=(1.0,))
if not hasattr(creator, "IndividualBCD"):
    creator.create("IndividualBCD", list, fitness=creator.FitnessMaxBCD)


# ---------------------------------------------------------------------------
# Worker process globals (set once per Pool creation via _bcd_worker_init)
# ---------------------------------------------------------------------------

_bcd_frozen_vector: Optional[List[float]] = None
_bcd_active_dims: Optional[List[int]] = None
_bcd_train_rows = None
_bcd_val_rows = None
_bcd_score_timeline = None


def _bcd_worker_init(frozen_vector, active_dims, train_rows, val_rows, score_timeline):
    """
    Initialise worker process globals.
    Called once per Pool creation (Windows spawn-safe pattern).

    frozen_vector : full 52-dim vector, fixed dims come from here.
    active_dims   : indices of dims the GA is allowed to vary.
    """
    global _bcd_frozen_vector, _bcd_active_dims
    global _bcd_train_rows, _bcd_val_rows, _bcd_score_timeline
    _bcd_frozen_vector  = list(frozen_vector)
    _bcd_active_dims    = list(active_dims)
    _bcd_train_rows     = train_rows
    _bcd_val_rows       = val_rows
    _bcd_score_timeline = score_timeline


def _bcd_worker_evaluate(partial_individual):
    """
    Evaluate a partial individual (active dims only).

    Reconstructs the full 52-dim vector by merging active-dim values
    from partial_individual with frozen values from _bcd_frozen_vector,
    then decodes and computes min(train_fit, val_fit).

    Returns (fitness,) tuple as required by DEAP.
    """
    from optimizer.parameter_space import decode_vector
    from optimizer.fitness import compute_fitness_for_subset

    # Reconstruct full vector
    full_vector = list(_bcd_frozen_vector)
    for i, dim_idx in enumerate(_bcd_active_dims):
        full_vector[dim_idx] = partial_individual[i]

    cfg = decode_vector(full_vector)
    train_fit, _ = compute_fitness_for_subset(_bcd_train_rows, _bcd_score_timeline, cfg)
    val_fit,   _ = compute_fitness_for_subset(_bcd_val_rows,   _bcd_score_timeline, cfg)
    return (min(train_fit, val_fit),)


# ---------------------------------------------------------------------------
# Mini GA — one BCD round
# ---------------------------------------------------------------------------

def _run_mini_ga(
    frozen_vector: List[float],
    active_dims: List[int],
    train_rows,
    val_rows,
    score_timeline,
    pop_size: int = 40,
    generations: int = 60,
    crossover_prob: float = 0.70,
    mutation_prob: float = 0.20,
    n_workers: int = 4,
    stop_flag_path: Optional[Path] = None,
) -> Tuple[List[float], float]:
    """
    Run a mini DEAP GA on active_dims only.

    The individual represents ONLY the active_dims values (not the full 52-dim
    vector). decode_vector is called after reconstruction in the worker.

    Returns
    -------
    best_partial : list of float
        Best values found for the active dims (len == len(active_dims)).
    best_fitness : float
        min(train_fit, val_fit) for the best individual.
    """
    n_active = len(active_dims)
    lower_active = np.array([LOWER_BOUNDS[d] for d in active_dims])
    upper_active = np.array([UPPER_BOUNDS[d] for d in active_dims])

    toolbox = base.Toolbox()

    toolbox.register(
        "individual", tools.initIterate, creator.IndividualBCD,
        lambda: [random.uniform(lo, hi) for lo, hi in zip(lower_active, upper_active)]
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", tools.cxTwoPoint)

    # Per-dim Gaussian sigma = 5% of range (same as genetic.py)
    sigmas = [(hi - lo) * 0.05 for lo, hi in zip(lower_active, upper_active)]

    def _mutate(individual):
        for i in range(n_active):
            if random.random() < (1.0 / n_active):  # per-gene probability
                individual[i] += random.gauss(0, sigmas[i])
                individual[i] = float(np.clip(individual[i], lower_active[i], upper_active[i]))
        return (individual,)

    toolbox.register("mutate", _mutate)
    toolbox.register("select", tools.selTournament, tournsize=3)

    # Build initial population
    pop = toolbox.population(n=pop_size)

    # Seed individual 0 with current best values for active dims
    seed = [frozen_vector[d] for d in active_dims]
    pop[0][:] = seed

    hof = tools.HallOfFame(1)

    with multiprocessing.Pool(
        processes=n_workers,
        initializer=_bcd_worker_init,
        initargs=(frozen_vector, active_dims, train_rows, val_rows, score_timeline),
    ) as pool:

        # Evaluate full initial population
        fitnesses = pool.map(_bcd_worker_evaluate, pop)
        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit
        hof.update(pop)

        for gen in range(generations):
            # Check stop flag between generations
            if stop_flag_path and stop_flag_path.exists():
                break

            # Elitism: preserve top 2
            elite = [toolbox.clone(e) for e in tools.selBest(pop, 2)]

            # Select offspring
            offspring = [toolbox.clone(o) for o in toolbox.select(pop, len(pop) - 2)]

            # Crossover
            for c1, c2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < crossover_prob:
                    toolbox.mate(c1, c2)
                    del c1.fitness.values
                    del c2.fitness.values

            # Mutation
            for mutant in offspring:
                if random.random() < mutation_prob:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            # Evaluate changed individuals
            invalid = [ind for ind in offspring if not ind.fitness.valid]
            if invalid:
                fitnesses = pool.map(_bcd_worker_evaluate, invalid)
                for ind, fit in zip(invalid, fitnesses):
                    ind.fitness.values = fit

            pop[:] = elite + offspring
            hof.update(pop)

    best = hof[0]
    return list(best), best.fitness.values[0]


# ---------------------------------------------------------------------------
# Full fitness evaluation (for current_best tracking)
# ---------------------------------------------------------------------------

def _evaluate_full(
    vector: List[float],
    train_rows,
    val_rows,
    score_timeline,
) -> Tuple[float, float, float]:
    """
    Compute min(train, val) fitness + individual components.
    Returns (combined_fitness, train_fit, val_fit).
    """
    cfg = decode_vector(vector)
    train_fit, _ = compute_fitness_for_subset(train_rows, score_timeline, cfg)
    val_fit,   _ = compute_fitness_for_subset(val_rows,   score_timeline, cfg)
    return min(train_fit, val_fit), train_fit, val_fit


# ---------------------------------------------------------------------------
# BCD main loop
# ---------------------------------------------------------------------------

def run_bcd_optimizer(
    run_id: int,
    max_rounds: int = 60,
    max_dims_per_round: int = 7,
    patience: int = 12,
    mini_pop: int = 40,
    mini_gen: int = 60,
    stop_flag_path: Optional[Path] = None,
    db_path: Path = DATABASE_PATH,
    n_workers: Optional[int] = None,
) -> dict:
    """
    Run BCD optimizer and return results dict.

    Parameters
    ----------
    run_id : int
        DB id of the optimization_runs record (already inserted by caller).
    max_rounds : int
        Maximum number of BCD rounds.
    max_dims_per_round : int
        Maximum active dimensions per round (default: 7).
    patience : int
        Stop after this many consecutive rounds without improvement.
    mini_pop : int
        GA population size per round.
    mini_gen : int
        GA generations per round.
    stop_flag_path : Path, optional
        Graceful shutdown file path.
    db_path : Path
        SQLite database path.
    n_workers : int, optional
        Parallel worker processes. Defaults to cpu_count - 1.

    Returns
    -------
    dict with keys:
        best_vector, baseline_fitness, final_fitness,
        best_train_fitness, best_val_fitness,
        rounds_run, block_history, block_impact, proposals,
        elapsed_seconds, train_count, val_count, test_count
    """
    t_start = time.time()

    n_workers = (
        int(os.environ.get("OPTIMIZER_WORKERS", _DEFAULT_WORKERS))
        if n_workers is None
        else max(1, n_workers)
    )

    # Private RNG for atomic unit sampling (reproducible within a run)
    rng = random.Random(int(time.time()) % 100000)

    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    print(f"[BCD] Loading signal data for run_id={run_id}...")
    all_rows, score_timeline = load_all_sim_data(db_path)
    print(f"[BCD] {len(all_rows)} signals loaded")

    train, val, test = split_rows(all_rows)
    print(f"[BCD] Split: train={len(train)}, val={len(val)}, test={len(test)}")

    _update_run_splits(run_id, train, val, test, db_path)

    # ------------------------------------------------------------------
    # Initialize from baseline
    # ------------------------------------------------------------------
    current_best = list(BASELINE_VECTOR)
    baseline_fitness, baseline_train, baseline_val = _evaluate_full(
        current_best, train, val, score_timeline
    )
    current_best_fitness = baseline_fitness

    print(
        f"[BCD] Baseline fitness: {baseline_fitness:.4f} "
        f"(train={baseline_train:.4f}, val={baseline_val:.4f})"
    )

    no_improve_count = 0
    block_history: List[dict] = []
    rounds_run = 0

    # ------------------------------------------------------------------
    # BCD loop
    # ------------------------------------------------------------------
    for round_idx in range(1, max_rounds + 1):
        rounds_run = round_idx

        if stop_flag_path and stop_flag_path.exists():
            print(f"[BCD] Stop flag detected at round {round_idx}. Stopping.")
            break

        t_round = time.time()

        # Sample atomic units for this round
        active_dims, unit_ids = sample_active_dims(
            max_dims=max_dims_per_round, rng=rng
        )
        n_active = len(active_dims)

        print(
            f"\n[BCD] Round {round_idx}/{max_rounds}: "
            f"units={unit_ids}  dims={active_dims}  ({n_active} active)"
        )

        # Run mini GA on the selected dims
        best_partial, round_fitness = _run_mini_ga(
            frozen_vector=current_best,
            active_dims=active_dims,
            train_rows=train,
            val_rows=val,
            score_timeline=score_timeline,
            pop_size=mini_pop,
            generations=mini_gen,
            n_workers=n_workers,
            stop_flag_path=stop_flag_path,
        )

        # Reconstruct full candidate vector
        candidate = list(current_best)
        for i, dim_idx in enumerate(active_dims):
            candidate[dim_idx] = best_partial[i]

        fitness_before = current_best_fitness
        accepted = round_fitness > current_best_fitness
        improvement_pct = (
            (round_fitness - fitness_before) / fitness_before * 100
            if fitness_before > 0 else 0.0
        )
        elapsed_round = time.time() - t_round

        if accepted:
            current_best = candidate
            current_best_fitness = round_fitness
            no_improve_count = 0
            print(
                f"  [ACCEPTED] {fitness_before:.4f} -> {round_fitness:.4f} "
                f"(+{improvement_pct:.2f}%)"
            )
        else:
            no_improve_count += 1
            print(
                f"  [REJECTED] {round_fitness:.4f} <= {fitness_before:.4f}  "
                f"(no-improve streak: {no_improve_count}/{patience})"
            )

        record = {
            "round":           round_idx,
            "unit_ids":        unit_ids,
            "active_dims":     active_dims,
            "n_active_dims":   n_active,
            "fitness_before":  round(fitness_before, 6),
            "fitness_after":   round(round_fitness, 6),
            "improvement_pct": round(improvement_pct, 4),
            "accepted":        accepted,
            "elapsed_seconds": round(elapsed_round, 1),
        }
        block_history.append(record)
        _write_bcd_round(run_id, record, db_path)
        _update_run_best(run_id, current_best_fitness, round_idx, db_path)

        if no_improve_count >= patience:
            print(
                f"[BCD] Patience exhausted ({patience} consecutive rounds "
                f"with no improvement). Stopping."
            )
            break

    # ------------------------------------------------------------------
    # Final evaluation on all splits
    # ------------------------------------------------------------------
    print(f"\n[BCD] Final evaluation...")

    _, final_train, final_val = _evaluate_full(current_best, train, val, score_timeline)

    cfg_best = decode_vector(current_best)
    test_fit, test_stats = compute_fitness_for_subset(test, score_timeline, cfg_best)

    cfg_baseline = decode_vector(BASELINE_VECTOR)
    baseline_test_fit, baseline_test_stats = compute_fitness_for_subset(
        test, score_timeline, cfg_baseline
    )

    improvement_pct_final = (
        (test_fit - baseline_test_fit) / baseline_test_fit * 100
        if baseline_test_fit > 0 else 0.0
    )
    train_val_gap = (
        (final_train - final_val) / final_train * 100
        if final_train > 0 else 0.0
    )
    overfitting_ok = train_val_gap <= 20.0

    print(f"  Baseline test fitness: {baseline_test_fit:.4f}")
    print(f"  Final train fitness:   {final_train:.4f}")
    print(f"  Final val fitness:     {final_val:.4f}")
    print(f"  Final test fitness:    {test_fit:.4f}")
    print(f"  Improvement:           {improvement_pct_final:+.2f}%")
    print(f"  Train/val gap:         {train_val_gap:.1f}%")

    proposal = {
        "rank":                    1,
        "vector":                  current_best,
        "config":                  cfg_best,
        "train_fitness":           round(final_train, 6),
        "val_fitness":             round(final_val, 6),
        "test_fitness":            round(test_fit, 6),
        "baseline_fitness":        round(baseline_test_fit, 6),
        "fitness_improvement_pct": round(improvement_pct_final, 2),
        "test_trade_count":        test_stats["total_trades"],
        "test_win_rate":           test_stats["win_rate"],
        "test_profit_factor":      test_stats["profit_factor"],
        "baseline_profit_factor":  baseline_test_stats["profit_factor"],
        "train_val_gap":           round(train_val_gap, 2),
        "overfitting_ok":          1 if overfitting_ok else 0,
        "config_diff":             vector_to_config_diff(current_best),
    }

    elapsed_total = time.time() - t_start

    # Block impact analysis
    block_impact = _compute_block_impact(block_history)

    print(f"\n[BCD] Block impact (top 5 by accumulated improvement):")
    for uid, st in list(block_impact.items())[:5]:
        print(
            f"  {uid:8s}  selected={st['rounds_selected']:2d}  "
            f"accepted={st['rounds_accepted']:2d}  "
            f"impact={st['total_improvement']:+.3f}%"
        )

    print(f"\n[BCD] Done in {elapsed_total:.0f}s ({elapsed_total/60:.1f} min). "
          f"Rounds: {rounds_run}/{max_rounds}")

    return {
        "best_vector":        current_best,
        "baseline_fitness":   baseline_fitness,
        "final_fitness":      current_best_fitness,
        "best_train_fitness": final_train,
        "best_val_fitness":   final_val,
        "rounds_run":         rounds_run,
        "block_history":      block_history,
        "block_impact":       block_impact,
        "proposals":          [proposal],
        "elapsed_seconds":    round(elapsed_total, 1),
        "train_count":        len(train),
        "val_count":          len(val),
        "test_count":         len(test),
    }


# ---------------------------------------------------------------------------
# Block impact analysis
# ---------------------------------------------------------------------------

def _compute_block_impact(block_history: List[dict]) -> Dict[str, dict]:
    """
    Per-atomic-unit impact summary across all rounds.

    Improvement is distributed equally among co-selected units in each round.
    Shows which parameter groups contributed most to fitness gains.
    """
    unit_stats: Dict[str, dict] = {}

    for record in block_history:
        n_units_in_round = len(record["unit_ids"])
        for uid in record["unit_ids"]:
            if uid not in unit_stats:
                unit_name = next(
                    (u["name"] for u in ATOMIC_UNITS if u["id"] == uid), uid
                )
                unit_stats[uid] = {
                    "unit_id":          uid,
                    "unit_name":        unit_name,
                    "rounds_selected":  0,
                    "rounds_accepted":  0,
                    "total_improvement": 0.0,
                    "best_improvement":  0.0,
                }

            st = unit_stats[uid]
            st["rounds_selected"] += 1

            if record["accepted"]:
                st["rounds_accepted"] += 1
                # Distribute improvement equally among co-selected units
                per_unit_imp = record["improvement_pct"] / n_units_in_round
                st["total_improvement"] += per_unit_imp
                st["best_improvement"] = max(st["best_improvement"], per_unit_imp)

    # Sort by total improvement descending
    return dict(
        sorted(
            unit_stats.items(),
            key=lambda x: x[1]["total_improvement"],
            reverse=True,
        )
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _update_run_splits(run_id, train, val, test, db_path: Path):
    conn = _db(db_path)
    try:
        conn.execute("""
            UPDATE optimization_runs SET
                train_signal_count = ?,
                val_signal_count   = ?,
                test_signal_count  = ?,
                total_signal_count = ?
            WHERE id = ?
        """, (len(train), len(val), len(test),
              len(train) + len(val) + len(test), run_id))
        conn.commit()
    except Exception as e:
        print(f"[BCD] DB split update warning: {e}")
    finally:
        conn.close()


def _update_run_best(run_id: int, best_fitness: float, rounds_run: int, db_path: Path):
    conn = _db(db_path)
    try:
        conn.execute("""
            UPDATE optimization_runs SET
                best_train_fitness = ?,
                generations_run    = ?
            WHERE id = ?
        """, (best_fitness, rounds_run, run_id))
        conn.commit()
    except Exception as e:
        print(f"[BCD] DB best update warning: {e}")
    finally:
        conn.close()


def _write_bcd_round(run_id: int, record: dict, db_path: Path):
    """Insert one BCD round record into bcd_rounds table."""
    conn = _db(db_path)
    try:
        conn.execute("""
            INSERT INTO bcd_rounds
                (run_id, round_number, unit_ids, active_dims, n_active_dims,
                 fitness_before, fitness_after, improvement_pct, accepted, elapsed_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            record["round"],
            json.dumps(record["unit_ids"]),
            json.dumps(record["active_dims"]),
            record["n_active_dims"],
            record["fitness_before"],
            record["fitness_after"],
            record["improvement_pct"],
            1 if record["accepted"] else 0,
            record["elapsed_seconds"],
        ))
        conn.commit()
    except Exception as e:
        print(f"[BCD] DB round write warning: {e}")
    finally:
        conn.close()
