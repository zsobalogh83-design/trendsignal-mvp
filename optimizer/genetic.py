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

v2.1 changes (parallelisation):
  - Fitness evaluation uses multiprocessing.Pool (process-parallel across CPU cores)
  - Worker processes receive shared data via pool initializer (Windows spawn-safe)
  - Validation fitness computed every VAL_EVAL_EVERY generations (not every gen)

v2.2 changes (overfitting regularization):
  - REGULARIZATION_STRENGTH (default 0.4): evolúciós fitness büntetés a
    train/proxy-val gap alapján → fitness = train * (1 - 0.4 * gap)
  - PROXY_TRAIN_FRAC (default 0.75): a train utolsó 25%-a proxy-val-ként
  - split_rows: 60/20/20 → 50/30/20 (nagyobb, megbízhatóbb val szett)

v2.3 changes (actual val in evolution — root-cause fix):
  - Diagnózis: proxy-val regularizáció nem véd az igazi overfitting ellen,
    mert a proxy-val ugyanabból az időperiódusból vesz mintát mint a train.
    Run 16: gen 1-ben val=0.38 (peak), gen 100-ra val=0.21-re CSÖKKENT —
    a GA aktívan rontott a val teljesítményen.
  - Megoldás: az IGAZI val adatokat adjuk át a workereknek, és a
    fitness = VAL_BLEND_WEIGHT × val_fit + (1 - VAL_BLEND_WEIGHT) × train_fit
    (default: 0.5/0.5 blend). Így a GA nem tudja ignorálni a val periódust.
  - A proxy-val regularizáció (PROXY_TRAIN_FRAC, REGULARIZATION_STRENGTH)
    eltávolítva — feleslegessé vált.
  - VAL_BLEND_WEIGHT konstans (default 0.5) bevezetése.

Version: 2.3
Date: 2026-03-01
"""

import json
import multiprocessing
import os
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

# How many CPU cores to use for parallel fitness evaluation.
# Leave 1 core free for the OS / main process.
# Override via environment variable OPTIMIZER_WORKERS if needed.
_DEFAULT_WORKERS = max(1, os.cpu_count() - 1)

# Validate fitness on the validation set every N generations.
# In v2.3 val is evaluated for EVERY individual (part of fitness),
# so VAL_EVAL_EVERY only controls DB/display logging of the best individual's
# standalone val score (not the blended fitness used for selection).
VAL_EVAL_EVERY = 5

# Validation blend weight for the evolutionary fitness function (v2.3).
# fitness_for_selection = VAL_BLEND_WEIGHT * val_fit + (1 - VAL_BLEND_WEIGHT) * train_fit
# Értelmezés:
#   0.0 → tisztán train (v2.1 viselkedés, erős overfitting)
#   0.5 → egyenlő súly (ajánlott: a GA egyszerre optimalizál train-re és val-ra)
#   1.0 → tisztán val (nem ajánlott, train irreleváns lenne)
VAL_BLEND_WEIGHT: float = 0.5

# ---------------------------------------------------------------------------
# DEAP setup — must be done once at module level
# ---------------------------------------------------------------------------

# Avoid re-registering if module is reimported
if not hasattr(creator, "FitnessMax"):
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMax)


# ---------------------------------------------------------------------------
# Multiprocessing: worker-process globals + initializer
# ---------------------------------------------------------------------------

# These are set in each worker process by _worker_init().
# Using module-level globals is the standard Windows-safe pattern for
# sharing large read-only data with a multiprocessing.Pool.
_worker_train_rows = None
_worker_val_rows   = None   # v2.3: igazi val, nem proxy — ez kerül a fitness-be
_worker_score_timeline = None


def _worker_init(train_rows, val_rows, score_timeline):
    """
    Called once per worker process when the Pool is created.
    Stores the shared data in module-level globals so that
    _worker_evaluate() can access it without pickling per-call.

    v2.3: val_rows az igazi validációs szett (nem proxy-val a train-ből).
    Mindkét szett bekerül a fitness számításba.
    """
    global _worker_train_rows, _worker_val_rows, _worker_score_timeline
    _worker_train_rows     = train_rows
    _worker_val_rows       = val_rows
    _worker_score_timeline = score_timeline


def _worker_evaluate(individual):
    """
    Top-level (picklable) function evaluated in worker processes.
    Uses module-level globals set by _worker_init().
    Returns (fitness,) tuple as required by DEAP.

    v2.3 blended fitness:
        fitness = VAL_BLEND_WEIGHT * val_fit + (1 - VAL_BLEND_WEIGHT) * train_fit

    Ez biztosítja, hogy a GA az evolúció SORÁN is optimalizál a val-ra,
    nem csak a train-re — megakadályozza, hogy a val fitness csökkenjen
    miközben a train fitness nő (run 16-ban ez történt).
    """
    from optimizer.parameter_space import decode_vector
    from optimizer.fitness import compute_fitness_for_subset
    cfg = decode_vector(individual)

    train_fit, _ = compute_fitness_for_subset(
        _worker_train_rows, _worker_score_timeline, cfg
    )
    val_fit, _ = compute_fitness_for_subset(
        _worker_val_rows, _worker_score_timeline, cfg
    )

    fitness = (1.0 - VAL_BLEND_WEIGHT) * train_fit + VAL_BLEND_WEIGHT * val_fit

    return (fitness,)


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
    n_workers: Optional[int] = None,
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
    n_workers : int, optional
        Number of parallel worker processes for fitness evaluation.
        Defaults to os.cpu_count() - 1 (all cores minus one).
        Set to 1 to disable parallelism (useful for debugging).

    Returns
    -------
    dict with keys: best_vector, best_train_fitness, best_val_fitness,
                    generations_run, proposals (list of dicts)
    """
    t_start = time.time()

    # Resolve worker count
    n_workers = int(os.environ.get("OPTIMIZER_WORKERS", _DEFAULT_WORKERS)) \
        if n_workers is None else max(1, n_workers)

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

    # Single-process blended evaluate — same formula as _worker_evaluate.
    # Used for the baseline seed individual (pop[0]) to stay consistent.
    def evaluate_single(individual):
        cfg = decode_vector(individual)
        train_fit, _ = compute_fitness_for_subset(train, score_timeline, cfg)
        val_fit,   _ = compute_fitness_for_subset(val,   score_timeline, cfg)
        fitness = (1.0 - VAL_BLEND_WEIGHT) * train_fit + VAL_BLEND_WEIGHT * val_fit
        return (fitness,)

    toolbox.register("evaluate", evaluate_single)

    # --- Initialize population ---
    rng_seed = int(time.time()) % 100000
    random.seed(rng_seed)
    np.random.seed(rng_seed)

    pop = toolbox.population(n=population_size)

    # Seed population with baseline vector (individual 0)
    pop[0][:] = list(BASELINE_VECTOR)

    print(f"[GA] Starting parallel fitness evaluation with {n_workers} worker(s)...")

    # --- Open the worker pool (stays open for the entire run) ---
    # Windows requires the pool to be created inside an if __name__ == '__main__'
    # guard in scripts, but since this runs as a subprocess spawned by _runner.py
    # (which has the guard), we are safe here.
    with multiprocessing.Pool(
        processes=n_workers,
        initializer=_worker_init,
        initargs=(train, val, score_timeline),
    ) as pool:

        # Evaluate baseline individual (in-process, avoids pickling overhead)
        pop[0].fitness.values = evaluate_single(pop[0])

        # Evaluate rest of initial population in parallel
        print(f"[GA] Evaluating initial population ({population_size} individuals)...")
        fitnesses = pool.map(_worker_evaluate, pop[1:])
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

            # Evaluate offspring in parallel
            invalid = [ind for ind in offspring if not ind.fitness.valid]
            if invalid:
                fitnesses = pool.map(_worker_evaluate, invalid)
                for ind, fit in zip(invalid, fitnesses):
                    ind.fitness.values = fit

            # Replace population (elitism)
            pop[:] = elite + offspring
            hof.update(pop)

            # Generation stats
            gen_best  = max(ind.fitness.values[0] for ind in pop)
            gen_avg   = np.mean([ind.fitness.values[0] for ind in pop])
            gen_worst = min(ind.fitness.values[0] for ind in pop)

            # Validate best individual on validation set every VAL_EVAL_EVERY gens.
            # Between validation points, carry forward the last known val_fit.
            if gen % VAL_EVAL_EVERY == 0 or gen == 1:
                best_ind = tools.selBest(pop, 1)[0]
                cfg_best = decode_vector(best_ind)
                val_fit, _ = compute_fitness_for_subset(val, score_timeline, cfg_best)
                best_val_fitness = val_fit

            train_val_gap = (
                (gen_best - best_val_fitness) / gen_best
                if gen_best > 0 else 0.0
            )

            best_train_fitness = gen_best

            # Write generation record to DB
            _write_generation(
                run_id=run_id,
                generation=gen,
                best_train=gen_best,
                avg_train=gen_avg,
                worst_train=gen_worst,
                best_val=best_val_fitness,
                train_val_gap=train_val_gap,
                db_path=db_path,
            )

            if gen % 10 == 0 or gen <= 5:
                val_marker = "" if gen % VAL_EVAL_EVERY == 0 or gen == 1 else " (cached)"
                print(f"[GA] Gen {gen:3d}/{max_generations}: "
                      f"best={gen_best:.4f}  avg={gen_avg:.4f}  "
                      f"val={best_val_fitness:.4f}{val_marker}  "
                      f"gap={train_val_gap*100:.1f}%")

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
