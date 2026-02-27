"""
TrendSignal Self-Tuning Engine - Statistical Validation

Implements the three validation layers from design doc v1.5 chapter 10:
  1. Acceptance gates  — hard/soft thresholds
  2. Bootstrap test    — statistical significance (p < 0.05)
  3. Walk-forward      — out-of-sample consistency (>=4/5 windows)
  4. Regime breakdown  — ADX-based market regime analysis

Version: 1.0
Date: 2026-02-23
"""

import json
import random
from typing import Dict, List, Optional, Tuple

import numpy as np

from optimizer.backtester import SignalSimRow, replay_and_simulate
from optimizer.fitness import compute_fitness_for_subset, MIN_TRADES
from optimizer.parameter_space import decode_vector, BASELINE_VECTOR


# ---------------------------------------------------------------------------
# Profit Factor helper
# ---------------------------------------------------------------------------

def _profit_factor(pnl_list: List[float]) -> float:
    gross_profit = sum(p for p in pnl_list if p > 0)
    gross_loss   = sum(abs(p) for p in pnl_list if p < 0)
    if gross_loss == 0:
        return 3.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _get_active_pnls(
    rows: List[SignalSimRow],
    score_timeline: dict,
    cfg: dict,
) -> List[float]:
    """
    Return list of P&L values for trades activated by this config.
    Uses full v2 trade simulation pipeline (replay_and_simulate).
    """
    sim_results = replay_and_simulate(rows, score_timeline, cfg)
    pnls = []
    for r in sim_results:
        if not r.trade_active or r.exit_reason == "NO_EXIT":
            continue
        pnls.append(float(r.pnl_percent))
    return pnls


# ---------------------------------------------------------------------------
# 1. Acceptance Gates
# ---------------------------------------------------------------------------

GATES = {
    # name: (description, required, check_fn)
    # check_fn(proposal_stats, baseline_stats) -> (passed: bool, value: float)
}


def check_acceptance_gates(proposal: dict, baseline: dict) -> dict:
    """
    Evaluate all acceptance gates for a proposal.

    Parameters
    ----------
    proposal : dict
        Keys: test_fitness, test_trade_count, test_profit_factor,
              fitness_improvement_pct, train_val_gap, overfitting_ok,
              baseline_fitness, baseline_profit_factor
    baseline : dict
        Keys: test_fitness, test_profit_factor, test_trade_count

    Returns
    -------
    dict with gate results: {gate_name: {passed, value, required, description}}
    """
    gates = {}

    # Gate 1: Minimum trade count (REQUIRED)
    trade_count = proposal.get("test_trade_count", 0)
    gates["min_trades"] = {
        "passed":      trade_count >= 50,
        "value":       trade_count,
        "threshold":   50,
        "required":    True,
        "description": "Min. 50 trade a test seten",
    }

    # Gate 2: Fitness improvement >= 10% (REQUIRED)
    improvement = proposal.get("fitness_improvement_pct", 0.0)
    gates["fitness_improvement"] = {
        "passed":      improvement >= 10.0,
        "value":       round(improvement, 2),
        "threshold":   10.0,
        "required":    True,
        "description": "Fitness javulas >= 10%",
    }

    # Gate 3: Profit factor improvement (REQUIRED)
    prop_pf     = proposal.get("test_profit_factor", 0.0)
    base_pf     = baseline.get("test_profit_factor", 0.0)
    pf_delta    = prop_pf - base_pf
    gates["profit_factor"] = {
        "passed":      pf_delta >= 0.10,
        "value":       round(pf_delta, 3),
        "threshold":   0.10,
        "required":    True,
        "description": "Profit Factor javulas >= 0.10",
    }

    # Gate 4: Bootstrap significance (REQUIRED) — filled by bootstrap_test()
    gates["bootstrap"] = {
        "passed":      proposal.get("bootstrap_significant", False),
        "value":       round(proposal.get("bootstrap_p_value", 1.0), 4),
        "threshold":   0.05,
        "required":    True,
        "description": "Bootstrap p-ertek < 0.05 (95% CI)",
    }

    # Gate 5: Overfitting check (REQUIRED)
    gap = proposal.get("train_val_gap", 100.0)
    gates["overfitting"] = {
        "passed":      gap <= 20.0,
        "value":       round(gap, 2),
        "threshold":   20.0,
        "required":    True,
        "description": "Train/val res <= 20%",
    }

    # Gate 6: Sideways regime PF >= 1.0 (WARNING only)
    sideways_pf = proposal.get("regime_sideways_pf", None)
    gates["sideways_regime"] = {
        "passed":      sideways_pf is None or sideways_pf >= 1.0,
        "value":       round(sideways_pf, 3) if sideways_pf is not None else None,
        "threshold":   1.0,
        "required":    False,
        "description": "Sideways rezim PF >= 1.0 (figyelmezeto)",
    }

    return gates


def gates_verdict(gates: dict) -> Tuple[str, str]:
    """
    Compute final verdict from gate results.

    Returns (verdict, reason) where verdict is:
      PROPOSABLE   — all required gates passed, all warnings passed
      CONDITIONAL  — all required gates passed, some warnings failed
      REJECTED     — at least one required gate failed
    """
    required_failures = [
        name for name, g in gates.items()
        if g["required"] and not g["passed"]
    ]
    warning_failures = [
        name for name, g in gates.items()
        if not g["required"] and not g["passed"]
    ]

    if required_failures:
        reason = f"Kotelező gate-ek nem teljesültek: {', '.join(required_failures)}"
        return "REJECTED", reason
    elif warning_failures:
        reason = f"Figyelmeztetesek: {', '.join(warning_failures)}"
        return "CONDITIONAL", reason
    else:
        return "PROPOSABLE", "Minden gate teljesult"


# ---------------------------------------------------------------------------
# 2. Bootstrap Test
# ---------------------------------------------------------------------------

def bootstrap_test(
    baseline_pnls: List[float],
    proposal_pnls: List[float],
    n_iterations: int = 1000,
    rng_seed: int = 42,
) -> dict:
    """
    Bootstrap significance test.
    H0: proposed config is not better than baseline.

    Samples with replacement from both P&L lists and computes
    the distribution of PF differences.

    Returns
    -------
    dict: p_value, significant, observed_diff, bootstrap_distribution_summary
    """
    rng = np.random.default_rng(rng_seed)

    if not baseline_pnls or not proposal_pnls:
        return {
            "p_value":    1.0,
            "significant": False,
            "observed_diff": 0.0,
            "note": "Insufficient data for bootstrap test",
        }

    observed_pf_baseline = _profit_factor(baseline_pnls)
    observed_pf_proposal = _profit_factor(proposal_pnls)
    observed_diff = observed_pf_proposal - observed_pf_baseline

    base_arr = np.array(baseline_pnls)
    prop_arr = np.array(proposal_pnls)

    boot_diffs = []
    for _ in range(n_iterations):
        b_sample = rng.choice(base_arr, size=len(base_arr), replace=True)
        p_sample = rng.choice(prop_arr, size=len(prop_arr), replace=True)
        boot_diffs.append(_profit_factor(p_sample.tolist()) -
                          _profit_factor(b_sample.tolist()))

    boot_arr = np.array(boot_diffs)
    # p-value: fraction of bootstrap diffs <= 0 (H0: no improvement)
    p_value = float(np.mean(boot_arr <= 0))

    return {
        "p_value":          round(p_value, 4),
        "significant":      p_value < 0.05,
        "observed_diff":    round(observed_diff, 4),
        "observed_pf_baseline": round(observed_pf_baseline, 4),
        "observed_pf_proposal": round(observed_pf_proposal, 4),
        "boot_mean":        round(float(boot_arr.mean()), 4),
        "boot_std":         round(float(boot_arr.std()), 4),
        "boot_p5":          round(float(np.percentile(boot_arr, 5)), 4),
        "boot_p95":         round(float(np.percentile(boot_arr, 95)), 4),
        "n_iterations":     n_iterations,
    }


# ---------------------------------------------------------------------------
# 3. Walk-Forward Validation
# ---------------------------------------------------------------------------

def walk_forward_validation(
    rows: List[SignalSimRow],
    score_timeline: dict,
    proposal_cfg: dict,
    baseline_cfg: dict,
    n_windows: int = 5,
    train_ratio: float = 0.60,
) -> dict:
    """
    Sliding window walk-forward validation.

    Divides the signal rows into n_windows overlapping windows.
    In each window, the last (1 - train_ratio) fraction is the test period.
    Computes PF delta (proposal - baseline) for each window's test period.

    Returns
    -------
    dict: windows (list), positive_count, consistent (>=4/5 positive),
          pf_deltas
    """
    n = len(rows)
    window_size = n // n_windows
    step = window_size // 2  # 50% overlap

    windows = []
    for i in range(n_windows):
        start = i * step
        end   = min(start + window_size, n)
        if end - start < 50:
            break

        window_rows  = rows[start:end]
        test_start   = int(len(window_rows) * train_ratio)
        test_rows    = window_rows[test_start:]

        if len(test_rows) < 10:
            continue

        prop_fit, prop_stats = compute_fitness_for_subset(
            test_rows, score_timeline, proposal_cfg, min_trades=5
        )
        base_fit, base_stats = compute_fitness_for_subset(
            test_rows, score_timeline, baseline_cfg, min_trades=5
        )

        prop_pf = prop_stats["profit_factor"]
        base_pf = base_stats["profit_factor"]
        pf_delta = prop_pf - base_pf

        windows.append({
            "window":          i + 1,
            "signal_range":    f"{rows[start].calculated_at[:10]} to {rows[end-1].calculated_at[:10]}",
            "test_signals":    len(test_rows),
            "prop_fitness":    round(prop_fit, 4),
            "base_fitness":    round(base_fit, 4),
            "prop_pf":         round(prop_pf, 4),
            "base_pf":         round(base_pf, 4),
            "pf_delta":        round(pf_delta, 4),
            "positive":        pf_delta > 0,
        })

    positive_count = sum(1 for w in windows if w["positive"])
    consistent = positive_count >= max(1, len(windows) * 4 // 5)  # >=4/5

    return {
        "windows":        windows,
        "window_count":   len(windows),
        "positive_count": positive_count,
        "consistent":     consistent,
        "status":         (
            "CONSISTENT" if positive_count >= len(windows) * 4 // 5
            else "MIXED"  if positive_count >= len(windows) * 3 // 5
            else "INCONSISTENT"
        ),
    }


# ---------------------------------------------------------------------------
# 4. Market Regime Breakdown
# ---------------------------------------------------------------------------

ADX_SIDEWAYS_MAX  = 20   # ADX < 20 → sideways
ADX_TRENDING_MIN  = 30   # ADX > 30 → trending
ATR_HIGHVOL_MIN   = 3.5  # ATR% > 3.5 → high volatility


def regime_breakdown(
    rows: List[SignalSimRow],
    score_timeline: dict,
    cfg: dict,
) -> dict:
    """
    Compute fitness/PF per market regime (Trending / Sideways / High Vol).

    Regime detection (from design doc):
      - ADX > 30   → Trending
      - ADX < 20   → Sideways
      - ATR% > 3.5 → High Volatility (can overlap with above)
      - Else        → Mixed (excluded from regime-specific stats)
    """
    sim_results = replay_and_simulate(rows, score_timeline, cfg)

    buckets: Dict[str, List[float]] = {
        "trending": [],
        "sideways": [],
        "high_vol": [],
    }

    for r, row in zip(sim_results, rows):
        if not r.trade_active or r.exit_reason == "NO_EXIT":
            continue
        pnl = r.pnl_percent

        adx = row.adx
        atr_pct = row.volatility  # stored as ATR%

        # Classify regime
        if atr_pct is not None and atr_pct >= ATR_HIGHVOL_MIN:
            buckets["high_vol"].append(float(pnl))
        elif adx is not None and adx >= ADX_TRENDING_MIN:
            buckets["trending"].append(float(pnl))
        elif adx is not None and adx < ADX_SIDEWAYS_MAX:
            buckets["sideways"].append(float(pnl))
        else:
            buckets["trending"].append(float(pnl))  # default to trending

    result = {}
    for regime, pnls in buckets.items():
        pf = _profit_factor(pnls) if pnls else None
        wr = (sum(1 for p in pnls if p > 0) / len(pnls)) if pnls else None
        result[regime] = {
            "profit_factor": round(pf, 3) if pf is not None else None,
            "win_rate":      round(wr, 3) if wr is not None else None,
            "trade_count":   len(pnls),
        }

    return result


# ---------------------------------------------------------------------------
# Full validation pipeline for one proposal
# ---------------------------------------------------------------------------

def validate_proposal(
    proposal_vector: List[float],
    rows: List[SignalSimRow],
    score_timeline: dict,
    test_rows: List[SignalSimRow],
    run_walk_forward: bool = True,
    bootstrap_iterations: int = 1000,
) -> dict:
    """
    Run the full validation pipeline for one candidate config vector.

    Returns a complete validation result dict suitable for storing
    in config_proposals table.
    """
    proposal_cfg = decode_vector(proposal_vector)
    baseline_cfg = decode_vector(BASELINE_VECTOR)

    # P&L lists for bootstrap
    proposal_pnls = _get_active_pnls(test_rows, score_timeline, proposal_cfg)
    baseline_pnls = _get_active_pnls(test_rows, score_timeline, baseline_cfg)

    # Bootstrap
    boot = bootstrap_test(baseline_pnls, proposal_pnls, bootstrap_iterations)

    # Walk-forward
    wf = {}
    if run_walk_forward and len(rows) >= 100:
        wf = walk_forward_validation(rows, score_timeline, proposal_cfg, baseline_cfg)

    # Regime breakdown (on full dataset for more data)
    regime = regime_breakdown(rows, score_timeline, proposal_cfg)

    return {
        "bootstrap":    boot,
        "walk_forward": wf,
        "regime":       regime,
    }
