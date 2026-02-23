"""
TrendSignal Self-Tuning Engine - Parameter Space Definition

Defines the 40-dimensional parameter vector for the genetic optimizer.

Dimension layout (0-indexed):
  [0-1]   Component weights (2 free; RISK_WEIGHT = 1 - S - T)
  [2-5]   Signal thresholds (4)
  [6-8]   Sentiment decay (3 free; DECAY_0_2h fixed at 1.0)
  [9-13]  Technical component weights (5 free; VOLUME_WEIGHT = 1 - sum)
  [14-21] Technical signal scores (8)
  [22-23] Risk component weights (2 free; TREND_STRENGTH = 1 - V - P)
  [24-29] Alignment bonuses and thresholds (6)
  [30-35] RSI/Stochastic zone thresholds (6)
  [36-39] Sentiment confidence params (4)

Total: 40 dimensions

Version: 1.0
Date: 2026-02-23
"""

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass
class ParamDef:
    """Definition of a single optimizable parameter."""
    index: int
    name: str           # matches TrendSignalConfig attribute name (lowercase)
    config_key: str     # matches config.json key (uppercase)
    low: float
    high: float
    is_int: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# Full parameter space — 40 dimensions
# ---------------------------------------------------------------------------

PARAM_DEFS: List[ParamDef] = [

    # ------------------------------------------------------------------
    # Group 1: Component Weights  (dim 0-1, RISK_WEIGHT is derived)
    # ------------------------------------------------------------------
    ParamDef(0,  "sentiment_weight",    "SENTIMENT_WEIGHT",    0.10, 0.80, False,
             "Weight of sentiment score in combined score"),
    ParamDef(1,  "technical_weight",    "TECHNICAL_WEIGHT",    0.10, 0.70, False,
             "Weight of technical score in combined score"),
    # RISK_WEIGHT = 1.0 - sentiment_weight - technical_weight  (enforced in decode)

    # ------------------------------------------------------------------
    # Group 2: Signal Thresholds  (dim 2-5)
    # ------------------------------------------------------------------
    ParamDef(2,  "hold_zone_threshold", "HOLD_ZONE_THRESHOLD", 5.0,  30.0, False,
             "Score below which decision is HOLD"),
    ParamDef(3,  "strong_buy_score",    "STRONG_BUY_SCORE",    35.0, 80.0, False,
             "Minimum score for STRONG BUY decision"),
    ParamDef(4,  "moderate_buy_score",  "MODERATE_BUY_SCORE",  15.0, 55.0, False,
             "Minimum score for MODERATE BUY decision"),
    ParamDef(5,  "strong_buy_confidence","STRONG_BUY_CONFIDENCE", 0.50, 0.95, False,
             "Minimum confidence for STRONG BUY"),

    # ------------------------------------------------------------------
    # Group 3: Sentiment Decay  (dim 6-8; DECAY_0_2h = 1.0 fixed)
    # Constraint: dim6 >= dim7 >= dim8  (enforced in decode)
    # ------------------------------------------------------------------
    ParamDef(6,  "decay_2_6h",          "DECAY_2_6H",          0.50, 1.00, False,
             "Sentiment decay weight for 2-6h old news"),
    ParamDef(7,  "decay_6_12h",         "DECAY_6_12H",         0.20, 0.85, False,
             "Sentiment decay weight for 6-12h old news"),
    ParamDef(8,  "decay_12_24h",        "DECAY_12_24H",        0.05, 0.60, False,
             "Sentiment decay weight for 12-24h old news"),

    # ------------------------------------------------------------------
    # Group 4: Technical Component Weights  (dim 9-13; VOLUME = 1-sum)
    # ------------------------------------------------------------------
    ParamDef(9,  "tech_sma_weight",      "TECH_SMA_WEIGHT",     0.05, 0.60, False,
             "Weight of SMA component in technical score"),
    ParamDef(10, "tech_rsi_weight",      "TECH_RSI_WEIGHT",     0.05, 0.50, False,
             "Weight of RSI component in technical score"),
    ParamDef(11, "tech_macd_weight",     "TECH_MACD_WEIGHT",    0.05, 0.45, False,
             "Weight of MACD component in technical score"),
    ParamDef(12, "tech_bollinger_weight","TECH_BOLLINGER_WEIGHT",0.00, 0.40, False,
             "Weight of Bollinger Bands in technical score"),
    ParamDef(13, "tech_stochastic_weight","TECH_STOCHASTIC_WEIGHT",0.00, 0.20, False,
             "Weight of Stochastic in technical score"),
    # TECH_VOLUME_WEIGHT = max(0, 1 - sum(dim9..dim13))  (enforced in decode)

    # ------------------------------------------------------------------
    # Group 5: Technical Signal Scores  (dim 14-21)
    # ------------------------------------------------------------------
    ParamDef(14, "tech_sma20_bullish",  "TECH_SMA20_BULLISH",  5,    50,   True,
             "Score contribution when price > SMA20"),
    ParamDef(15, "tech_sma50_bullish",  "TECH_SMA50_BULLISH",  5,    45,   True,
             "Score contribution when price > SMA50"),
    ParamDef(16, "tech_golden_cross",   "TECH_GOLDEN_CROSS",   3,    35,   True,
             "Score for golden cross (SMA20 > SMA50)"),
    ParamDef(17, "tech_rsi_bullish",    "TECH_RSI_BULLISH",    10,   60,   True,
             "Score when RSI is in bullish zone"),
    ParamDef(18, "tech_rsi_weak_bullish","TECH_RSI_WEAK_BULLISH",0,  30,   True,
             "Score when RSI is weakly bullish"),
    ParamDef(19, "tech_rsi_overbought", "TECH_RSI_OVERBOUGHT", 5,    50,   True,
             "Score deduction when RSI is overbought"),
    ParamDef(20, "tech_rsi_oversold",   "TECH_RSI_OVERSOLD",   5,    50,   True,
             "Score boost when RSI is oversold (contrarian signal)"),
    ParamDef(21, "tech_rsi_neutral",    "TECH_RSI_NEUTRAL",    5,    40,   True,
             "Score when RSI is in neutral zone"),

    # ------------------------------------------------------------------
    # Group 6: Risk Component Weights  (dim 22-23; TREND = 1-V-P)
    # ------------------------------------------------------------------
    ParamDef(22, "risk_volatility_weight",   "RISK_VOLATILITY_WEIGHT",    0.10, 0.70, False,
             "Weight of volatility component in risk score"),
    ParamDef(23, "risk_proximity_weight",    "RISK_PROXIMITY_WEIGHT",     0.10, 0.60, False,
             "Weight of S/R proximity in risk score"),
    # RISK_TREND_STRENGTH_WEIGHT = 1 - V - P  (enforced in decode)

    # ------------------------------------------------------------------
    # Group 7: Alignment Bonuses  (dim 24-29)
    # ------------------------------------------------------------------
    ParamDef(24, "alignment_bonus_all",  "ALIGNMENT_BONUS_ALL",  2,  15,   True,
             "Bonus when all 3 components agree strongly"),
    ParamDef(25, "alignment_bonus_tr",   "ALIGNMENT_BONUS_TR",   1,  12,   True,
             "Bonus when technical+risk agree"),
    ParamDef(26, "alignment_bonus_st",   "ALIGNMENT_BONUS_ST",   1,  12,   True,
             "Bonus when sentiment+technical agree"),
    ParamDef(27, "alignment_bonus_sr",   "ALIGNMENT_BONUS_SR",   0,   8,   True,
             "Bonus when sentiment+risk agree"),
    ParamDef(28, "alignment_tech_threshold","ALIGNMENT_TECH_THRESHOLD", 30, 80, True,
             "Min tech score (abs) to count as strong for alignment"),
    ParamDef(29, "alignment_sent_threshold","ALIGNMENT_SENT_THRESHOLD", 20, 70, True,
             "Min sentiment score (abs) for alignment bonus"),

    # ------------------------------------------------------------------
    # Group 8: RSI/Stochastic Zone Thresholds  (dim 30-35)
    # Constraints enforced in decode:
    #   RSI_OVERSOLD < RSI_NEUTRAL_LOW < RSI_NEUTRAL_HIGH < RSI_OVERBOUGHT
    #   STOCH_OVERSOLD < STOCH_OVERBOUGHT
    # ------------------------------------------------------------------
    ParamDef(30, "rsi_overbought",   "RSI_OVERBOUGHT",   60,  85,  True,
             "RSI level above which market is overbought"),
    ParamDef(31, "rsi_oversold",     "RSI_OVERSOLD",     15,  40,  True,
             "RSI level below which market is oversold"),
    ParamDef(32, "rsi_neutral_low",  "RSI_NEUTRAL_LOW",  35,  55,  True,
             "Lower bound of RSI neutral zone"),
    ParamDef(33, "rsi_neutral_high", "RSI_NEUTRAL_HIGH", 45,  65,  True,
             "Upper bound of RSI neutral zone"),
    ParamDef(34, "stoch_overbought", "STOCH_OVERBOUGHT", 65,  90,  True,
             "Stochastic level for overbought"),
    ParamDef(35, "stoch_oversold",   "STOCH_OVERSOLD",   10,  35,  True,
             "Stochastic level for oversold"),

    # ------------------------------------------------------------------
    # Group 9: Sentiment Confidence Params  (dim 36-39)
    # ------------------------------------------------------------------
    ParamDef(36, "sentiment_positive_threshold", "SENTIMENT_POSITIVE_THRESHOLD",
             0.05, 0.40, False,
             "Sentiment score above which news is considered positive"),
    ParamDef(37, "sentiment_negative_threshold", "SENTIMENT_NEGATIVE_THRESHOLD",
             -0.40, -0.05, False,
             "Sentiment score below which news is considered negative"),
    ParamDef(38, "sentiment_conf_full_news_count", "SENTIMENT_CONF_FULL_NEWS_COUNT",
             5, 20, True,
             "News count for full confidence"),
    ParamDef(39, "sentiment_conf_high_news_count", "SENTIMENT_CONF_HIGH_NEWS_COUNT",
             2, 10, True,
             "News count for high confidence"),
]

# Convenience: number of dimensions
N_DIMS: int = len(PARAM_DEFS)  # 40

# Lower and upper bounds as numpy arrays (for DEAP initialisation)
LOWER_BOUNDS: np.ndarray = np.array([p.low  for p in PARAM_DEFS], dtype=float)
UPPER_BOUNDS: np.ndarray = np.array([p.high for p in PARAM_DEFS], dtype=float)


# ---------------------------------------------------------------------------
# Current config baseline vector (matches config.json as of 2026-02-23)
# ---------------------------------------------------------------------------

BASELINE_VECTOR: List[float] = [
    # Group 1: Component weights
    0.50,   # 0  SENTIMENT_WEIGHT
    0.35,   # 1  TECHNICAL_WEIGHT
    # Group 2: Signal thresholds
    15.0,   # 2  HOLD_ZONE_THRESHOLD
    55.0,   # 3  STRONG_BUY_SCORE
    35.0,   # 4  MODERATE_BUY_SCORE
    0.75,   # 5  STRONG_BUY_CONFIDENCE
    # Group 3: Sentiment decay
    0.85,   # 6  DECAY_2_6h
    0.60,   # 7  DECAY_6_12h
    0.35,   # 8  DECAY_12_24h
    # Group 4: Technical component weights
    0.30,   # 9  TECH_SMA_WEIGHT
    0.25,   # 10 TECH_RSI_WEIGHT
    0.20,   # 11 TECH_MACD_WEIGHT
    0.15,   # 12 TECH_BOLLINGER_WEIGHT
    0.05,   # 13 TECH_STOCHASTIC_WEIGHT
    # Group 5: Technical signal scores
    25.0,   # 14 TECH_SMA20_BULLISH
    20.0,   # 15 TECH_SMA50_BULLISH
    15.0,   # 16 TECH_GOLDEN_CROSS
    30.0,   # 17 TECH_RSI_BULLISH
    10.0,   # 18 TECH_RSI_WEAK_BULLISH
    30.0,   # 19 TECH_RSI_OVERBOUGHT
    30.0,   # 20 TECH_RSI_OVERSOLD
    20.0,   # 21 TECH_RSI_NEUTRAL
    # Group 6: Risk component weights
    0.40,   # 22 RISK_VOLATILITY_WEIGHT
    0.35,   # 23 RISK_PROXIMITY_WEIGHT
    # Group 7: Alignment bonuses
    8.0,    # 24 ALIGNMENT_BONUS_ALL
    5.0,    # 25 ALIGNMENT_BONUS_TR
    5.0,    # 26 ALIGNMENT_BONUS_ST
    3.0,    # 27 ALIGNMENT_BONUS_SR
    60.0,   # 28 ALIGNMENT_TECH_THRESHOLD
    40.0,   # 29 ALIGNMENT_SENT_THRESHOLD
    # Group 8: RSI/Stochastic zones
    70.0,   # 30 RSI_OVERBOUGHT
    30.0,   # 31 RSI_OVERSOLD
    45.0,   # 32 RSI_NEUTRAL_LOW
    55.0,   # 33 RSI_NEUTRAL_HIGH
    80.0,   # 34 STOCH_OVERBOUGHT
    20.0,   # 35 STOCH_OVERSOLD
    # Group 9: Sentiment confidence
    0.20,   # 36 SENTIMENT_POSITIVE_THRESHOLD
    -0.20,  # 37 SENTIMENT_NEGATIVE_THRESHOLD
    10.0,   # 38 SENTIMENT_CONF_FULL_NEWS_COUNT
    5.0,    # 39 SENTIMENT_CONF_HIGH_NEWS_COUNT
]

assert len(BASELINE_VECTOR) == N_DIMS, \
    f"BASELINE_VECTOR length {len(BASELINE_VECTOR)} != N_DIMS {N_DIMS}"


# ---------------------------------------------------------------------------
# Decoded config dict — apply constraints and return all params
# ---------------------------------------------------------------------------

def decode_vector(v: List[float]) -> dict:
    """
    Convert a raw 40-dim vector to a fully-constrained config dict.

    Applies:
      - sum=1.0 normalization for component weights
      - monotone decay constraint
      - RSI/Stoch ordering constraints
      - integer rounding for is_int params
      - derived (non-free) parameters
    """
    v = list(v)

    # --- Round integer params ---
    for p in PARAM_DEFS:
        if p.is_int:
            v[p.index] = round(v[p.index])

    # --- Clamp all to bounds ---
    for p in PARAM_DEFS:
        v[p.index] = float(np.clip(v[p.index], p.low, p.high))

    # --- Group 1: component weights sum=1.0 ---
    sw = v[0]
    tw = v[1]
    rw = 1.0 - sw - tw
    if rw < 0.05:
        # Scale down sw and tw proportionally to free up risk weight
        total = sw + tw
        sw = sw / total * 0.95
        tw = tw / total * 0.95
        rw = 0.05
    v[0] = sw
    v[1] = tw

    # --- Group 3: monotone decay ---
    # Enforce dim6 >= dim7 >= dim8
    d26  = v[6]
    d612 = min(v[7], d26)
    d1224 = min(v[8], d612)
    v[6] = d26
    v[7] = d612
    v[8] = d1224

    # --- Group 4: tech weights sum=1.0, volume is residual ---
    tw_sum = v[9] + v[10] + v[11] + v[12] + v[13]
    if tw_sum > 1.0:
        # Normalise proportionally
        for i in range(9, 14):
            v[i] = v[i] / tw_sum
        tech_volume = 0.0
    else:
        tech_volume = max(0.0, 1.0 - tw_sum)

    # --- Group 6: risk weights sum=1.0, trend is residual ---
    rv = v[22]
    rp = v[23]
    rt = 1.0 - rv - rp
    if rt < 0.05:
        total = rv + rp
        rv = rv / total * 0.95
        rp = rp / total * 0.95
        rt = 0.05
    v[22] = rv
    v[23] = rp

    # --- Group 8: RSI ordering constraints ---
    # RSI_OVERSOLD < RSI_NEUTRAL_LOW < RSI_NEUTRAL_HIGH < RSI_OVERBOUGHT
    rsi_ob   = v[30]
    rsi_os   = v[31]
    rsi_nl   = v[32]
    rsi_nh   = v[33]
    # Sort and re-assign with minimum gaps
    rsi_os  = min(rsi_os, rsi_ob - 20)
    rsi_nl  = max(rsi_os + 5, min(rsi_nl, rsi_ob - 15))
    rsi_nh  = max(rsi_nl + 5, min(rsi_nh, rsi_ob - 5))
    v[30] = rsi_ob
    v[31] = max(15, rsi_os)
    v[32] = rsi_nl
    v[33] = rsi_nh

    # STOCH: oversold < overbought
    if v[35] >= v[34]:
        v[35] = v[34] - 20

    # --- Build result dict ---
    cfg = {}
    for p in PARAM_DEFS:
        cfg[p.config_key] = int(v[p.index]) if p.is_int else v[p.index]

    # Derived / non-free params
    cfg["RISK_WEIGHT"]              = round(1.0 - v[0] - v[1], 6)
    cfg["TECH_VOLUME_WEIGHT"]       = round(tech_volume, 6)
    cfg["RISK_TREND_STRENGTH_WEIGHT"] = round(rt, 6)
    cfg["DECAY_0_2H"]               = 1.0   # always fixed

    # SELL thresholds are symmetric
    cfg["STRONG_SELL_SCORE"]        = -cfg["STRONG_BUY_SCORE"]
    cfg["MODERATE_SELL_SCORE"]      = -cfg["MODERATE_BUY_SCORE"]
    cfg["STRONG_SELL_CONFIDENCE"]   = cfg["STRONG_BUY_CONFIDENCE"]
    cfg["MODERATE_BUY_CONFIDENCE"]  = cfg["STRONG_BUY_CONFIDENCE"] - 0.10
    cfg["MODERATE_SELL_CONFIDENCE"] = cfg["STRONG_BUY_CONFIDENCE"] - 0.10

    # BEARISH scores are symmetric with BULLISH
    cfg["TECH_SMA20_BEARISH"]       = cfg["TECH_SMA20_BULLISH"]
    cfg["TECH_SMA50_BEARISH"]       = cfg["TECH_SMA50_BULLISH"]
    cfg["TECH_DEATH_CROSS"]         = cfg["TECH_GOLDEN_CROSS"]

    return cfg


def vector_to_config_diff(v: List[float]) -> dict:
    """
    Compare decoded vector against BASELINE_VECTOR.
    Returns {config_key: {before, after}} for changed params only.
    """
    decoded  = decode_vector(v)
    baseline = decode_vector(BASELINE_VECTOR)

    diff = {}
    for key in decoded:
        before = baseline.get(key)
        after  = decoded[key]
        if before is not None and abs(float(before) - float(after)) > 1e-6:
            diff[key] = {"before": before, "after": after}
    return diff
