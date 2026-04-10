"""
TrendSignal Self-Tuning Engine - Fitness Function

Evaluates how good a config vector is based on full trade re-simulation:
  1. Replays all signals with new config → new BUY/SELL/HOLD decisions
  2. Computes new SL/TP for each active signal under the new config
  3. Simulates each trade candle-by-candle against price_data
  4. Computes fitness = win_rate × profit_factor × volume_factor on simulated P&L

Key design change from v1:
  - v1 looked up FIXED P&L from simulated_trades (fundamentally flawed)
  - v2 derives P&L from fresh simulation → changing config truly changes outcomes

Fitness formula (v4.0):
    fitness = win_rate × profit_factor × volume_factor
    where:
      win_rate      = winning_trades / total_trades
      profit_factor = total_gross_profit / total_gross_loss
      volume_factor = min(1.0, sqrt(total_trades / VOLUME_TARGET))
                      — bünteti a kis trade-számot, megakadályozza a cherry-pickinget

    If total_trades == 0:         fitness = 0.0
    If total_gross_loss == 0:     fitness = win_rate × 3.0 × volume_factor (cap)

    Nincs hard MIN_TRADES floor a fitness-ben — a GA minden trade-számnál kap
    gradienst, így short módban (kevés induló trade) sem bolyong vakon.
    Az elfogadási kapu (validation.py gate_min_trades ≥ 150) változatlan.

    VOLUME_TARGET: az a trade-szám, aminél volume_factor = 1.0 (teljes pontszám).
    Ennél kevesebb trade esetén sqrt-alapú fokozatos büntetés érvényesül.
    Indoklás: a GA így nem tud 50-100 db „cherry-picked" trade-del hamisan magas
    fitnesst elérni — ösztönözve van arra, hogy minél több jelet aktiváljon.

Data split (v3.0 — random):
    Véletlenszerű felosztás időszak-független stabilitásért.
    A run_id seed-ként szolgál → egy futáson belül konzisztens, futások között eltérő.

        50% train  |  30% val  |  20% test   (véletlenszerűen kiválasztott sorok)

    Előnye a korábbi reversed-chronological splittel szemben:
      - Nem kötődik egyetlen piaci rezsimhez sem
      - A GA általánosan jobb konfigurációkat talál
      - Train/val/test fitness értékek összehasonlíthatóak és stabilak

Version: 4.0 — volume_factor anti-cherry-picking, MIN_TRADES 50→150
Date: 2026-04-08
"""

import math
import random
from typing import Dict, List, Optional, Tuple

from optimizer.trade_simulator import TradeSimResult
from optimizer.signal_data import SignalSimRow

# Minimum trades for a valid fitness score (hard floor — below this: fitness = 0.0).
# 150 alatt a GA még mindig cherry-pickinget végezhet; 150-nél a 7500-as train seten
# ez ~2% aktivációs rátát jelent, ami már statisztikailag értékelhető.
MIN_TRADES = 150

# Volume target: ennél a trade-számnál volume_factor = 1.0 (nincs büntetés).
# A train set ~50%-a az összes adatnak; 300 trade a teljes adaton → 150 a train seten.
# A GA ösztönözve van, hogy legalább ennyi trade-et aktiváljon.
VOLUME_TARGET = 300


# ---------------------------------------------------------------------------
# Primary fitness function — uses TradeSimResult from replay_and_simulate()
# ---------------------------------------------------------------------------

def compute_fitness(
    sim_results: List[TradeSimResult],
    min_trades: int = MIN_TRADES,
) -> Tuple[float, dict]:
    """
    Compute fitness from fully simulated trade results.

    Parameters
    ----------
    sim_results : list of TradeSimResult
        Output of backtester.replay_and_simulate() for one config.
    min_trades : int
        Minimum number of active trades for a non-zero fitness.

    Returns
    -------
    fitness : float
        win_rate × profit_factor, or 0.0 if insufficient trades.
    stats : dict
        Detailed breakdown for logging/display.
    """
    gross_profit = 0.0
    gross_loss   = 0.0
    wins         = 0
    losses       = 0
    total        = 0
    skipped      = 0   # HOLD or below-threshold signals

    exit_reasons: Dict[str, int] = {}

    for result in sim_results:
        if not result.trade_active:
            skipped += 1
            continue

        # NO_EXIT trades are counted as neutral (not won, not lost)
        if result.exit_reason == "NO_EXIT":
            skipped += 1
            continue

        pnl = result.pnl_percent
        total += 1
        exit_reasons[result.exit_reason] = exit_reasons.get(result.exit_reason, 0) + 1

        if pnl > 0:
            gross_profit += pnl
            wins += 1
        else:
            gross_loss += abs(pnl)
            losses += 1

    # Compute rates
    win_rate = wins / total if total > 0 else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = 3.0     # all wins, cap at 3.0
    else:
        profit_factor = 0.0

    # Volume factor: bünteti az alacsony trade-számot (cherry-picking elleni védelem).
    # sqrt skálázás: fokozatos, nem bináris büntetés.
    # Nincs hard floor — a GA akkor is kap gradienst, ha total < min_trades.
    # Ez kritikus pl. short módban, ahol az induló config kevés trade-et aktivál:
    # a hard floor esetén minden konfiguráció fitness=0 lenne, és a GA vakon bolyongna.
    # Az elfogadási kapu (validation.py, gate_min_trades) marad 150 — gyenge javaslat
    # nem kerülhet elfogadásra, de a GA navigálni tud a helyes irányba.
    volume_factor = min(1.0, math.sqrt(total / VOLUME_TARGET)) if total > 0 else 0.0

    fitness = win_rate * profit_factor * volume_factor

    stats = {
        "fitness":        round(fitness, 6),
        "win_rate":       round(win_rate, 4),
        "profit_factor":  round(profit_factor, 4),
        "volume_factor":  round(volume_factor, 4),
        "total_trades":   total,
        "wins":           wins,
        "losses":         losses,
        "skipped":        skipped,
        "gross_profit":   round(gross_profit, 4),
        "gross_loss":     round(gross_loss, 4),
        "exit_reasons":   exit_reasons,
    }
    return fitness, stats


# ---------------------------------------------------------------------------
# Convenience wrapper: replay + simulate + fitness in one call
# ---------------------------------------------------------------------------

def compute_fitness_for_subset(
    rows: List[SignalSimRow],
    score_timeline: dict,
    cfg: dict,
    min_trades: int = MIN_TRADES,
) -> Tuple[float, dict]:
    """
    Convenience wrapper: replay + simulate + fitness in one call.
    Used for train/val/test splits.

    Parameters
    ----------
    rows : List[SignalSimRow]
        Signal rows for this split (with future_candles pre-loaded).
    score_timeline : dict
        {ticker: [(ts, score, sl, tp), ...]} for opposing signal detection.
    cfg : dict
        Decoded config dict from parameter_space.decode_vector().
    min_trades : int
        Minimum trades for non-zero fitness.
    """
    from optimizer.backtester import replay_and_simulate
    sim_results = replay_and_simulate(rows, score_timeline, cfg)
    return compute_fitness(sim_results, min_trades)


# ---------------------------------------------------------------------------
# Train / val / test split  (reversed-chronological: newest = train, v2.1)
# ---------------------------------------------------------------------------

def split_rows(
    rows: List[SignalSimRow],
    trade_outcomes=None,            # DEPRECATED: kept for backward compat only
    train_ratio: float = 0.50,
    val_ratio:   float = 0.30,
    min_trades_per_split: int = 20,
    random_seed: Optional[int] = None,
) -> Tuple[List[SignalSimRow], List[SignalSimRow], List[SignalSimRow]]:
    """
    Split signal rows into train / validation / test sets.

    RANDOM split (v3.0): véletlenszerű, időszak-független felosztás.

    Rationale: az időszak-alapú (reversed chronological) split egyetlen piaci
    rezsimhez kötötte a GA-t. Véletlenszerű splittel a GA általánosan jobb
    konfigurációkat talál, a fitness értékek összehasonlíthatók és stabilak.

    random_seed: reprodukálhatósághoz (tipikusan a run_id).
    Ha None, minden híváskor más felosztás keletkezik.

    Default: 50% train / 30% val / 20% test (véletlenszerűen kiválasztva).
    """
    n = len(rows)

    # Véletlenszerű index-keverés (seeded → egy futáson belül konzisztens)
    indices = list(range(n))
    rng = random.Random(random_seed)
    rng.shuffle(indices)

    test_end = int(n * (1.0 - train_ratio - val_ratio))
    val_end  = int(n * (1.0 - train_ratio))

    # Minimum méret: legalább 10% minden részbe
    test_end = max(test_end, max(1, int(n * 0.10)))
    val_end  = max(val_end,  test_end + max(1, int(n * 0.10)))
    val_end  = min(val_end,  n - max(1, int(n * 0.10)))

    test  = [rows[i] for i in indices[:test_end]]
    val   = [rows[i] for i in indices[test_end:val_end]]
    train = [rows[i] for i in indices[val_end:]]

    return train, val, test
