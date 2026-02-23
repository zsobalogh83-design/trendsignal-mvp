"""
TrendSignal Self-Tuning Engine - Fitness Function

Evaluates how good a config vector is by:
  1. Replaying all signals in the given subset with the config
  2. Matching replayed BUY/SELL decisions to existing simulated trade outcomes
  3. Computing win_rate × profit_factor as the fitness value

Design notes:
  - Trade outcomes (entry/exit/P&L) are FIXED from simulated_trades table.
    The optimizer only changes WHICH signals trigger trades (via new decisions
    and score thresholds) and HOW those decisions change the win/loss profile.
  - A signal is "active" if its replayed |score| >= ALERT_THRESHOLD (25).
  - The fitness penalizes configs that generate too few trades (< MIN_TRADES).
  - Higher fitness = better config.

Fitness formula:
    fitness = win_rate × profit_factor
    where:
      win_rate      = winning_trades / total_trades
      profit_factor = total_gross_profit / total_gross_loss

    If total_trades < MIN_TRADES: fitness = 0.0 (penalty)
    If total_gross_loss == 0:     fitness = win_rate × 3.0 (cap)

Version: 1.0
Date: 2026-02-23
"""

from typing import Dict, List, Optional, Tuple

from optimizer.backtester import ReplayResult, SignalRow

# Threshold above which a replayed signal counts as an "active" trade trigger.
# The backtest service opens trades at |score| >= 15 (SIGNAL_THRESHOLD),
# not 25 (ALERT_THRESHOLD). We use 15 here to match trade generation logic.
SIGNAL_THRESHOLD = 15.0

# Keep ALERT_THRESHOLD for reference / future use
ALERT_THRESHOLD = 25.0

# Minimum trades required for a valid fitness score
MIN_TRADES = 20


def compute_fitness(
    replay_results: List[ReplayResult],
    trade_outcomes: Dict[int, dict],
    alert_threshold: float = SIGNAL_THRESHOLD,
    min_trades: int = MIN_TRADES,
) -> Tuple[float, dict]:
    """
    Compute fitness for one config vector given the replayed signal scores
    and pre-loaded trade outcomes.

    Parameters
    ----------
    replay_results : list of ReplayResult
        Output of backtester.replay_all() for a given config.
    trade_outcomes : dict {signal_id: {pnl_percent, direction, ...}}
        Pre-loaded from simulated_trades (CLOSED trades only).
    alert_threshold : float
        Min |combined_score| to count as an active trade trigger.
    min_trades : int
        Minimum trades needed for a non-zero fitness.

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
    skipped      = 0   # signals with no matching trade outcome

    for result in replay_results:
        outcome = trade_outcomes.get(result.signal_id)
        if outcome is None:
            # No closed trade for this signal — skip
            skipped += 1
            continue

        pnl = outcome.get("pnl_percent", 0.0)
        if pnl is None:
            skipped += 1
            continue

        # With the new config, does this signal still pass the alert threshold?
        # If not, we treat the trade as "not triggered" — skip it.
        if abs(result.new_combined_score) < alert_threshold:
            skipped += 1
            continue

        # Direction alignment check:
        # If the replayed decision contradicts the trade direction, skip.
        trade_dir = outcome.get("direction", "")
        if result.new_decision == "BUY" and trade_dir == "SHORT":
            skipped += 1
            continue
        if result.new_decision == "SELL" and trade_dir == "LONG":
            skipped += 1
            continue

        total += 1
        if pnl > 0:
            gross_profit += pnl
            wins += 1
        else:
            gross_loss += abs(pnl)
            losses += 1

    # Build stats
    win_rate = wins / total if total > 0 else 0.0
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = 3.0  # all wins, cap at 3.0
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
    }
    return fitness, stats


def compute_fitness_for_subset(
    rows: List[SignalRow],
    trade_outcomes: Dict[int, dict],
    cfg: dict,
    alert_threshold: float = SIGNAL_THRESHOLD,
    min_trades: int = MIN_TRADES,
) -> Tuple[float, dict]:
    """
    Convenience wrapper: replay + fitness in one call.
    Used for train/val/test splits.
    """
    from optimizer.backtester import replay_all
    results = replay_all(rows, cfg)
    return compute_fitness(results, trade_outcomes, alert_threshold, min_trades)


def split_rows(
    rows: List[SignalRow],
    trade_outcomes: Optional[Dict[int, dict]] = None,
    train_ratio: float = 0.60,
    val_ratio:   float = 0.20,
    min_trades_per_split: int = 20,
) -> Tuple[List[SignalRow], List[SignalRow], List[SignalRow]]:
    """
    Split signal rows into train / validation / test sets.
    Split is chronological (not random) to prevent data leakage.

    If trade_outcomes is provided, adjusts split boundaries to ensure
    each split has at least min_trades_per_split matching trades.

    Default: 60% train / 20% val / 20% test by signal count.
    """
    n = len(rows)

    if trade_outcomes is None:
        # Simple ratio split
        train_end = int(n * train_ratio)
        val_end   = int(n * (train_ratio + val_ratio))
        return rows[:train_end], rows[train_end:val_end], rows[val_end:]

    # Trade-aware split: find boundaries where trade counts are balanced
    # Count trades per row position
    signal_ids = [r.signal_id for r in rows]
    has_trade  = [1 if sid in trade_outcomes else 0 for sid in signal_ids]
    cumulative = []
    c = 0
    for h in has_trade:
        c += h
        cumulative.append(c)
    total_trades = c

    if total_trades == 0:
        # Fallback to ratio split
        train_end = int(n * train_ratio)
        val_end   = int(n * (train_ratio + val_ratio))
        return rows[:train_end], rows[train_end:val_end], rows[val_end:]

    # Find split points by trade count
    train_trade_target = int(total_trades * train_ratio)
    val_trade_target   = int(total_trades * (train_ratio + val_ratio))

    train_end = next(
        (i for i, c in enumerate(cumulative) if c >= train_trade_target),
        int(n * train_ratio)
    )
    val_end = next(
        (i for i, c in enumerate(cumulative) if c >= val_trade_target),
        int(n * (train_ratio + val_ratio))
    )

    # Ensure minimum sizes
    train_end = max(train_end, int(n * 0.40))
    val_end   = max(val_end,   train_end + int(n * 0.10))
    val_end   = min(val_end,   n - int(n * 0.10))

    train = rows[:train_end]
    val   = rows[train_end:val_end]
    test  = rows[val_end:]

    return train, val, test
