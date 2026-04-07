"""
TrendSignal BCD Optimizer - Atomic Unit Definitions

Atomic units are groups of parameter dimensions that MUST be optimized
together because decode_vector() enforces constraints between them
(ordering, sum=1 normalization, monotone sequences, etc.).

25 atomic units covering all 61 dimensions.

Version: 2.0 — 12-component CW_ weight architecture
Date: 2026-04-07
"""

import random
from typing import Dict, Any, List, Tuple


ATOMIC_UNITS: List[Dict[str, Any]] = [

    # ------------------------------------------------------------------
    # Group 1: CW_ sentiment weights (dims 0-1)
    # Part of the shared 12-component sum=1 normalization.
    # Constraint: all CW_ dims [0,1,9-13,22,23,59,60] share global sum.
    # ------------------------------------------------------------------
    {"id": "W",     "dims": [0, 1],
     "name": "CW sentiment weights (signal + recency)"},

    # ------------------------------------------------------------------
    # Group 2: Signal thresholds — split into 3 independent units
    # dims 3+4 kept together: MODERATE_BUY_SCORE implied < STRONG_BUY_SCORE
    # ------------------------------------------------------------------
    {"id": "TH_H",  "dims": [2],
     "name": "HOLD zone threshold"},
    {"id": "TH_S",  "dims": [3, 4],
     "name": "Score thresholds (strong/moderate BUY)"},
    {"id": "TH_C",  "dims": [5],
     "name": "Signal confidence threshold"},

    # ------------------------------------------------------------------
    # Group 3: Sentiment decay — monotone constraint: d26 >= d612 >= d1224
    # ------------------------------------------------------------------
    {"id": "DEC",   "dims": [6, 7, 8],
     "name": "Sentiment decay"},

    # ------------------------------------------------------------------
    # Group 4: CW_ technical weights (dims 9-13)
    # Part of the shared 12-component sum=1 normalization.
    # ------------------------------------------------------------------
    {"id": "TW",    "dims": [9, 10, 11, 12, 13],
     "name": "CW technical weights (sma/rsi/macd/bb/stoch)"},

    # ------------------------------------------------------------------
    # Group 5: Technical signal scores — no cross-constraints, split 2x4
    # ------------------------------------------------------------------
    {"id": "TS_A",  "dims": [14, 15, 16, 17],
     "name": "Tech scores A (SMA/RSI bullish)"},
    {"id": "TS_B",  "dims": [18, 19, 20, 21],
     "name": "Tech scores B (RSI overbought/oversold/neutral)"},

    # ------------------------------------------------------------------
    # Group 6: CW_ risk weights — volume_confirm + volatility_risk (dims 22-23)
    # Part of the shared 12-component sum=1 normalization.
    # ------------------------------------------------------------------
    {"id": "RW",    "dims": [22, 23],
     "name": "CW risk weights (volume_confirm + volatility_risk)"},

    # ------------------------------------------------------------------
    # Group 7: Alignment — no cross-constraints, split bonus + threshold
    # ------------------------------------------------------------------
    {"id": "AL_B",  "dims": [24, 25, 26, 27],
     "name": "Alignment bonuses"},
    {"id": "AL_T",  "dims": [28, 29],
     "name": "Alignment thresholds"},

    # ------------------------------------------------------------------
    # Group 8: RSI/Stoch zone thresholds
    # Constraint: oversold < neutral_low < neutral_high < overbought
    #             stoch_oversold < stoch_overbought
    # ------------------------------------------------------------------
    {"id": "RSI",   "dims": [30, 31, 32, 33, 34, 35],
     "name": "RSI/Stoch zone thresholds"},

    # ------------------------------------------------------------------
    # Group 9: Sentiment confidence — two independent pairs
    # ------------------------------------------------------------------
    {"id": "SC_T",  "dims": [36, 37],
     "name": "Sentiment score thresholds (pos/neg)"},
    {"id": "SC_C",  "dims": [38, 39],
     "name": "Sentiment confidence counts"},

    # ------------------------------------------------------------------
    # Group 10: ATR Stop-Loss (LONG) — sorted: HIGH_CONF <= DEFAULT <= LOW_CONF
    # ------------------------------------------------------------------
    {"id": "ATR_SL", "dims": [40, 41, 42],
     "name": "ATR Stop-Loss multipliers (LONG)"},

    # ------------------------------------------------------------------
    # Group 11: ATR Take-Profit (LONG) — LOW_VOL <= HIGH_VOL
    # ------------------------------------------------------------------
    {"id": "ATR_TP", "dims": [43, 44],
     "name": "ATR Take-Profit multipliers (LONG)"},

    # ------------------------------------------------------------------
    # Group 12: S/R hard distance threshold — independent
    # ------------------------------------------------------------------
    {"id": "SR",    "dims": [45],
     "name": "S/R hard distance threshold"},

    # ------------------------------------------------------------------
    # Group 13: SHORT ATR Stop-Loss — sorted: HIGH_CONF <= DEFAULT <= LOW_CONF
    # ------------------------------------------------------------------
    {"id": "S_SL",  "dims": [46, 47, 48],
     "name": "SHORT ATR Stop-Loss multipliers"},

    # ------------------------------------------------------------------
    # Group 14a: SHORT ATR Take-Profit — LOW_VOL <= HIGH_VOL
    # ------------------------------------------------------------------
    {"id": "S_TP",  "dims": [49, 50],
     "name": "SHORT ATR Take-Profit multipliers"},

    # ------------------------------------------------------------------
    # Group 14b: SHORT SL max pct — independent
    # ------------------------------------------------------------------
    {"id": "S_MAX", "dims": [51],
     "name": "SHORT SL max pct"},

    # ------------------------------------------------------------------
    # Group 15: Entry gate thresholds (dims 52-58)
    # Split into pairs so BCD can tune each gate independently.
    # ------------------------------------------------------------------
    {"id": "EG_R",  "dims": [52, 53],
     "name": "Entry gates RSI (buy_max / sell_min)"},
    {"id": "EG_M",  "dims": [54, 55],
     "name": "Entry gates MACD histogram (buy_min / sell_max)"},
    {"id": "EG_S",  "dims": [56, 57],
     "name": "Entry gates SMA200 pct (buy_max / sell_min)"},
    {"id": "EG_D",  "dims": [58],
     "name": "Entry gate dist_to_resistance (buy_max)"},

    # ------------------------------------------------------------------
    # Group 16: CW_ risk proximity + trend strength (dims 59-60)
    # Part of the shared 12-component sum=1 normalization.
    # ------------------------------------------------------------------
    {"id": "CW_R",  "dims": [59, 60],
     "name": "CW risk weights (sr_proximity + trend_strength)"},
]


# Validate: all 61 dims covered exactly once
_all_dims = [d for u in ATOMIC_UNITS for d in u["dims"]]
assert sorted(_all_dims) == list(range(61)), (
    f"ATOMIC_UNITS must cover dims 0-60 exactly once. Got: {sorted(_all_dims)}"
)

# Convenience lookup by ID
_UNIT_BY_ID: Dict[str, Dict[str, Any]] = {u["id"]: u for u in ATOMIC_UNITS}


def unit_by_id(unit_id: str) -> Dict[str, Any]:
    """Return atomic unit definition by ID."""
    if unit_id not in _UNIT_BY_ID:
        raise KeyError(f"Unknown atomic unit ID: {unit_id!r}")
    return _UNIT_BY_ID[unit_id]


def sample_active_dims(
    max_dims: int = 7,
    rng: random.Random = None,
    exclude_ids: List[str] = None,
) -> Tuple[List[int], List[str]]:
    """
    Randomly sample atomic units until total dims <= max_dims.

    Uses greedy random shuffle: shuffles the unit list, then greedily adds
    units that fit within the budget. This ensures:
      - All dims have equal long-run sampling probability (unbiased)
      - Constraint groups are never split
      - Total dims never exceeds max_dims

    Parameters
    ----------
    max_dims : int
        Maximum number of dimensions to activate per round (default: 7).
    rng : random.Random, optional
        RNG instance for reproducibility. Uses global random if None.
    exclude_ids : list of str, optional
        Atomic unit IDs to exclude from sampling (e.g. fixed params).

    Returns
    -------
    active_dims : sorted list of int
        Active dimension indices for this round.
    selected_unit_ids : list of str
        IDs of the selected atomic units (in selection order).
    """
    if rng is None:
        rng = random

    exclude = set(exclude_ids or [])
    eligible = [u for u in ATOMIC_UNITS if u["id"] not in exclude]

    shuffled = list(eligible)
    rng.shuffle(shuffled)

    selected_dims: List[int] = []
    selected_ids: List[str] = []

    for unit in shuffled:
        if len(selected_dims) + len(unit["dims"]) <= max_dims:
            selected_dims.extend(unit["dims"])
            selected_ids.append(unit["id"])

    return sorted(selected_dims), selected_ids
