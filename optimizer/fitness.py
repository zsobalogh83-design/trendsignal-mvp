"""
TrendSignal Self-Tuning Engine - Fitness Function

Evaluates how good a config vector is based on full trade re-simulation:
  1. Replays all signals with new config → new BUY/SELL/HOLD decisions
  2. Computes new SL/TP for each active signal under the new config
  3. Simulates each trade candle-by-candle against price_data
  4. Computes fitness = win_rate × profit_factor on simulated P&L

Key design change from v1:
  - v1 looked up FIXED P&L from simulated_trades (fundamentally flawed)
  - v2 derives P&L from fresh simulation → changing config truly changes outcomes

Fitness formula:
    fitness = win_rate × profit_factor
    where:
      win_rate      = winning_trades / total_trades
      profit_factor = total_gross_profit / total_gross_loss

    If total_trades < MIN_TRADES: fitness = 0.0 (penalty)
    If total_gross_loss == 0:     fitness = win_rate × 3.0 (cap)

Version: 2.0
Date: 2026-02-24
"""

from typing import Dict, List, Optional, Tuple

from optimizer.trade_simulator import TradeSimResult
from optimizer.signal_data import SignalSimRow

# Minimum trades for a valid fitness score
MIN_TRADES = 20


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

    if total < min_trades:
        fitness = 0.0
    else:
        fitness = win_rate * profit_factor

    stats = {
        "fitness":       round(fitness, 6),
        "win_rate":      round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "total_trades":  total,
        "wins":          wins,
        "losses":        losses,
        "skipped":       skipped,
        "gross_profit":  round(gross_profit, 4),
        "gross_loss":    round(gross_loss, 4),
        "exit_reasons":  exit_reasons,
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
# Train / val / test split  (chronological, no trade_outcomes needed in v2)
# ---------------------------------------------------------------------------

def split_rows(
    rows: List[SignalSimRow],
    trade_outcomes=None,            # DEPRECATED: kept for backward compat only
    train_ratio: float = 0.60,
    val_ratio:   float = 0.20,
    min_trades_per_split: int = 20,
) -> Tuple[List[SignalSimRow], List[SignalSimRow], List[SignalSimRow]]:
    """
    Split signal rows into train / validation / test sets.
    Split is chronological to prevent data leakage.

    In v2, we split by signal count (not by trade count) because we no longer
    need a pre-existing simulated_trades table — trades are generated on-the-fly.

    Default: 60% train / 20% val / 20% test by signal count.
    """
    n = len(rows)
    train_end = int(n * train_ratio)
    val_end   = int(n * (train_ratio + val_ratio))

    # Ensure minimum sizes
    train_end = max(train_end, int(n * 0.40))
    val_end   = max(val_end,   train_end + int(n * 0.10))
    val_end   = min(val_end,   n - int(n * 0.10))

    train = rows[:train_end]
    val   = rows[train_end:val_end]
    test  = rows[val_end:]

    return train, val, test
