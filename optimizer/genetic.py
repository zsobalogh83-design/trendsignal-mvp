"""
TrendSignal Self-Tuning Engine - Genetic Algorithm

Uses DEAP to evolve the 46-dimensional parameter vector.
Writes generation-level metrics to the DB for live progress polling.

Algorithm parameters:
  Population:    80 individuals
  Generations:   100
  Crossover:     0.7 (two-point)
  Mutation:      0.2 (Gaussian, sigma=0.05 of range)
  Selection:     Tournament (k=3)
  Elitism:       Top 2 preserved each generation

v2 changes:
  - Uses load_all_sim_data() instead of load_signal_rows() + load_trade_outcomes()
  - Evaluates via replay_and_simulate() — full trade simulation per config
  - compute_fitness_for_subset() now takes score_timeline instead of trade_outcomes
  - 46-dim parameter space (added ATR SL/TP and SR blend params)

Version: 2.0
Date: 2026-02-24
"""

import json
import random
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from deap import base, creator, tools, algorithms

from optimizer.signal_data import load_all_sim_data
from optimizer.backtester import load_signal_rows, load_trade_outcomes, SignalRow  # backward compat
from optimizer.fitness import (
    compute_fitness,
    compute_fitness_for_subset,
    split_rows,
    MIN_TRADES,
)
from optimizer.parameter_space import (
    PARAM_DEFS,
    N_DIMS,
    LOWER_BOUNDS,
    UPPER_BOUNDS,
    BASELINE_VECTOR,
    decode_vector,
    vector_to_config_diff,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"

# ---------------------------------------------------------------------------
# DEAP setup — must be done once at module level
# ---------------------------------------------------------------------------

# Avoid re-registering if module is reimported
if not hasattr(creator, "FitnessMax"):
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMax)


def _make_toolbox(
    lower: np.ndarray,
    upper: np.ndarray,
    mutation_sigma_frac: float = 0.05,
) -> base.Toolbox:
    """Build and return a configured DEAP Toolbox."""
    toolbox = base.Toolbox()

    # Attribute generator: uniform random within bounds per dimension
    def random_attr(lo, hi):
        return random.uniform(lo, hi)

    toolbox.register("individual", tools.initIterate, creator.Individual,
                     lambda: [random_attr(lo, hi)
                              for lo, hi in zip(lower, upper)])
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Crossover: two-point
    toolbox.register("mate", tools.cxTwoPoint)

    # Mutation: Gaussian with per-dimension sigma
    sigmas = [(hi - lo) * mutation_sigma_frac for lo, hi in zip(lower, upper)]

    def mutate_individual(individual):
        for i in range(len(individual)):
            if random.random() < (1.0 / N_DIMS):  # per-gene probability
                individual[i] += random.gauss(0, sigmas[i])
                individual[i] = float(np.clip(individual[i], lower[i], upper[i]))
        return (individual,)

    toolbox.register("mutate", mutate_individual)

    # Selection: tournament
    toolbox.register("select", tools.selTournament, tournsize=3)

    return toolbox


# ---------------------------------------------------------------------------
# Main optimizer entry point
# ---------------------------------------------------------------------------

def run_optimizer(
    run_id: int,
    population_size: int = 80,
    max_generations: int = 100,
    crossover_prob: float = 0.70,
    mutation_prob: float = 0.20,
    stop_flag_path: Optional[Path] = None,
    db_path: Path = DATABASE_PATH,
) -> dict:
    """
    Run the genetic optimizer and return results.

    Parameters
    ----------
    run_id : int
        DB id of the optimization_runs record (already inserted by caller).
    population_size : int
    max_generations : int
    crossover_prob : float
    mutation_prob : float
    stop_flag_path : Path, optional
        If this file exists, the optimizer stops gracefully.
    db_path : Path
        SQLite database path.

    Returns
    -------
    dict with keys: best_vector, best_train_fitness, best_val_fitness,
                    generations_run, proposals (list of dicts)
    """
    t_start = time.time()

    # --- Load data (v2: single pass, includes price candles for full sim) ---
    print(f"[GA] Loading signal data for run_id={run_id}...")
    all_rows, score_timeline = load_all_sim_data(db_path)
    print(f"[GA] {len(all_rows)} signals loaded with price data")

    train, val, test = split_rows(all_rows)
    print(f"[GA] Split: train={len(train)}, val={len(val)}, test={len(test)}")

    # Update run record with split info
    _update_run_splits(run_id, train, val, test, db_path)

    # --- Toolbox ---
    toolbox = _make_toolbox(LOWER_BOUNDS, UPPER_BOUNDS)

    # Fitness evaluation function (v2: uses score_timeline, no trade_outcomes)
    def evaluate(individual):
        cfg = decode_vector(individual)
        fitness, _ = compute_fitness_for_subset(train, score_timeline, cfg)
        return (fitness,)

    toolbox.register("evaluate", evaluate)

    # --- Initialize population ---
    rng_seed = int(time.time()) % 100000
    random.seed(rng_seed)
    np.random.seed(rng_seed)

    pop = toolbox.population(n=population_size)

    # Seed population with baseline vector (individual 0)
    pop[0][:] = list(BASELINE_VECTOR)
    pop[0].fitness.values = evaluate(pop[0])

    # Evaluate initial population
    print(f"[GA] Evaluating initial population ({population_size} individuals)...")
    fitnesses = list(map(toolbox.evaluate, pop[1:]))
    for ind, fit in zip(pop[1:], fitnesses):
        ind.fitness.values = fit

    # Hall of fame: top 3 individuals
    hof = tools.HallOfFame(3)
    hof.update(pop)

    # Stats
    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("best",  max)
    stats.register("avg",   np.mean)
    stats.register("worst", min)

    best_train_fitness = max(ind.fitness.values[0] for ind in pop)
    best_val_fitness   = 0.0
    generations_run    = 0

    print(f"[GA] Initial best fitness: {best_train_fitness:.4f}")

    # --- Evolution loop ---
    for gen in range(1, max_generations + 1):
        generations_run = gen

        # Check stop flag
        if stop_flag_path and stop_flag_path.exists():
            print(f"[GA] Stop flag detected at generation {gen}. Stopping.")
            break

        # Elitism: preserve top 2
        elite = tools.selBest(pop, 2)
        elite = [toolbox.clone(e) for e in elite]

        # Select next generation
        offspring = toolbox.select(pop, len(pop) - 2)
        offspring = [toolbox.clone(o) for o in offspring]

        # Crossover
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < crossover_prob:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values

        # Mutation
        for mutant in offspring:
            if random.random() < mutation_prob:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        # Evaluate offspring
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = list(map(toolbox.evaluate, invalid))
        for ind, fit in zip(invalid, fitnesses):
            ind.fitness.values = fit

        # Replace population (elitism)
        pop[:] = elite + offspring
        hof.update(pop)

        # Generation stats
        gen_best  = max(ind.fitness.values[0] for ind in pop)
        gen_avg   = np.mean([ind.fitness.values[0] for ind in pop])
        gen_worst = min(ind.fitness.values[0] for ind in pop)

        # Validate best individual on validation set
        best_ind = tools.selBest(pop, 1)[0]
        cfg_best = decode_vector(best_ind)
        val_fit, _ = compute_fitness_for_subset(val, score_timeline, cfg_best)

        train_val_gap = (gen_best - val_fit) / gen_best if gen_best > 0 else 0.0

        best_train_fitness = gen_best
        best_val_fitness   = val_fit

        # Write generation record to DB
        _write_generation(
            run_id=run_id,
            generation=gen,
            best_train=gen_best,
            avg_train=gen_avg,
            worst_train=gen_worst,
            best_val=val_fit,
            train_val_gap=train_val_gap,
            db_path=db_path,
        )

        if gen % 10 == 0 or gen <= 5:
            print(f"[GA] Gen {gen:3d}/{max_generations}: "
                  f"best={gen_best:.4f}  avg={gen_avg:.4f}  "
                  f"val={val_fit:.4f}  gap={train_val_gap*100:.1f}%")

    # --- Compute test fitness for top-3 individuals ---
    print(f"\n[GA] Evaluating top-3 candidates on test set...")
    proposals = []
    cfg_baseline = decode_vector(BASELINE_VECTOR)
    baseline_fit, baseline_stats = compute_fitness_for_subset(test, score_timeline, cfg_baseline)
    baseline_train_fit, _ = compute_fitness_for_subset(train, score_timeline, cfg_baseline)

    for rank, ind in enumerate(hof, start=1):
        cfg = decode_vector(ind)
        train_fit, train_stats = compute_fitness_for_subset(train, score_timeline, cfg)
        val_fit,   val_stats   = compute_fitness_for_subset(val,   score_timeline, cfg)
        test_fit,  test_stats  = compute_fitness_for_subset(test,  score_timeline, cfg)

        improvement_pct = (
            (test_fit - baseline_fit) / baseline_fit * 100
            if baseline_fit > 0 else 0.0
        )
        train_val_gap = (
            (train_fit - val_fit) / train_fit * 100
            if train_fit > 0 else 0.0
        )
        overfitting_ok = train_val_gap <= 20.0

        print(f"  Rank {rank}: train={train_fit:.4f}  val={val_fit:.4f}  "
              f"test={test_fit:.4f}  improvement={improvement_pct:+.1f}%  "
              f"gap={train_val_gap:.1f}%")

        proposals.append({
            "rank":                   rank,
            "vector":                 list(ind),
            "config":                 cfg,
            "train_fitness":          round(train_fit, 6),
            "val_fitness":            round(val_fit, 6),
            "test_fitness":           round(test_fit, 6),
            "baseline_fitness":       round(baseline_fit, 6),
            "fitness_improvement_pct":round(improvement_pct, 2),
            "test_trade_count":       test_stats["total_trades"],
            "test_win_rate":          test_stats["win_rate"],
            "test_profit_factor":     test_stats["profit_factor"],
            "baseline_profit_factor": baseline_stats["profit_factor"],
            "train_val_gap":          round(train_val_gap, 2),
            "overfitting_ok":         1 if overfitting_ok else 0,
            "config_diff":            vector_to_config_diff(ind),
        })

    elapsed = time.time() - t_start
    print(f"\n[GA] Done in {elapsed:.0f}s ({elapsed/60:.1f} min). "
          f"Generations: {generations_run}/{max_generations}")

    return {
        "best_vector":         list(hof[0]) if hof else BASELINE_VECTOR,
        "best_train_fitness":  best_train_fitness,
        "best_val_fitness":    best_val_fitness,
        "baseline_fitness":    baseline_fit,
        "generations_run":     generations_run,
        "proposals":           proposals,
        "elapsed_seconds":     round(elapsed, 1),
        "train_count":         len(train),
        "val_count":           len(val),
        "test_count":          len(test),
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _update_run_splits(run_id, train, val, test, db_path):
    """Write split sizes to optimization_runs record."""
    # v2: trade counts are not known upfront (generated per-config)
    # Store signal counts; trade_counts will be 0 until first evaluation
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            UPDATE optimization_runs SET
                train_signal_count = ?,
                val_signal_count   = ?,
                test_signal_count  = ?,
                total_signal_count = ?,
                train_trade_count  = 0,
                val_trade_count    = 0,
                test_trade_count   = 0
            WHERE id = ?
        """, (
            len(train), len(val), len(test),
            len(train) + len(val) + len(test),
            run_id,
        ))
        conn.commit()
    except Exception as e:
        print(f"[GA] DB split update warning: {e}")
    finally:
        conn.close()


def _write_generation(run_id, generation, best_train, avg_train, worst_train,
                      best_val, train_val_gap, db_path):
    """Insert one row into optimization_generations."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            INSERT INTO optimization_generations
                (run_id, generation, best_train_fitness, avg_train_fitness,
                 worst_train_fitness, best_val_fitness, train_val_gap)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, generation, best_train, avg_train, worst_train,
              best_val, train_val_gap))
        # Also update best fitness in run record
        conn.execute("""
            UPDATE optimization_runs SET
                best_train_fitness = ?,
                best_val_fitness   = ?,
                generations_run    = ?
            WHERE id = ?
        """, (best_train, best_val, generation, run_id))
        conn.commit()
    except Exception as e:
        print(f"[GA] DB write warning (gen {generation}): {e}")
    finally:
        conn.close()
