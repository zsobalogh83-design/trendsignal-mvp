"""
TrendSignal Self-Tuning Engine - Score Backtester

Replays historical signal_calculations with a new config vector,
recomputing combined scores and BUY/SELL/HOLD decisions without
touching live price data or APIs.

Key design:
  - All raw inputs are read once from the DB (load_signal_rows)
  - score recalculation is pure Python / numpy — no DB writes
  - trade outcome lookup uses the pre-existing simulated_trades table
  - SignalRow is a lightweight dataclass, no SQLAlchemy overhead

Version: 1.0
Date: 2026-02-23
"""

import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SignalRow:
    """
    Lightweight representation of one signal_calculations row.
    All fields needed for score replay are pre-parsed at load time.
    """
    signal_id: int
    ticker: str
    calculated_at: str          # ISO timestamp string

    # Raw stored indicator values
    rsi: Optional[float]
    macd: Optional[float]
    macd_signal_val: Optional[float]
    macd_histogram: Optional[float]
    sma_20: Optional[float]
    sma_50: Optional[float]
    sma_200: Optional[float]
    adx: Optional[float]
    bb_upper: Optional[float]
    bb_lower: Optional[float]
    bb_middle: Optional[float]
    stoch_k: Optional[float]
    stoch_d: Optional[float]
    current_price: Optional[float]
    volatility: Optional[float]  # ATR%

    # Stored aggregate scores (for validation / baseline)
    stored_sentiment_score: float   # already -100..+100 scaled
    stored_technical_score: float
    stored_risk_score: float
    stored_combined_score: float

    # Raw news items for sentiment replay
    # List of {sentiment_score, time_decay, weight, published_at}
    news_items: List[dict] = field(default_factory=list)

    # Stored component weights at calculation time (from weight_* columns)
    stored_weight_sentiment: float = 0.5
    stored_weight_technical: float = 0.35
    stored_weight_risk: float = 0.15

    # Stored config snapshot (for cross-check)
    stored_weights: dict = field(default_factory=dict)

    # ADX direction context (from technical_details key_signals)
    key_signals: List[str] = field(default_factory=list)


@dataclass
class ReplayResult:
    """Result of replaying one signal with a new config."""
    signal_id: int
    ticker: str
    calculated_at: str
    new_combined_score: float
    new_decision: str           # BUY / SELL / HOLD
    new_sentiment_score: float
    new_technical_score: float
    stored_risk_score: float    # risk score is not replayable (needs raw S/R)


# ---------------------------------------------------------------------------
# DB loader — called once per optimizer run, cached in memory
# ---------------------------------------------------------------------------

def load_signal_rows(db_path: Path = DATABASE_PATH) -> List[SignalRow]:
    """
    Load all signal_calculations rows that have enough data for replay.
    Filters out rows with NULL sentiment or technical scores.

    Returns a list sorted by calculated_at (chronological order).
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT
            sc.signal_id            AS signal_id,
            sc.ticker_symbol        AS ticker,
            sc.calculated_at,
            sc.rsi,
            sc.macd,
            sc.macd_signal          AS macd_signal_val,
            sc.macd_histogram,
            sc.sma_20,
            sc.sma_50,
            sc.sma_200,
            sc.adx,
            sc.bb_upper,
            sc.bb_lower,
            sc.bb_middle,
            sc.stoch_k,
            sc.stoch_d,
            sc.current_price,
            sc.volatility,
            sc.sentiment_score,
            sc.technical_score,
            sc.risk_score,
            sc.combined_score,
            sc.weight_sentiment,
            sc.weight_technical,
            sc.weight_risk,
            sc.news_inputs,
            sc.config_snapshot,
            sc.technical_details
        FROM signal_calculations sc
        WHERE sc.sentiment_score IS NOT NULL
          AND sc.technical_score IS NOT NULL
          AND sc.risk_score IS NOT NULL
          AND sc.combined_score IS NOT NULL
        ORDER BY sc.calculated_at ASC
    """).fetchall()

    conn.close()

    result = []
    for r in rows:
        # Parse news_inputs
        news_items = []
        if r["news_inputs"]:
            try:
                raw = json.loads(r["news_inputs"])
                if isinstance(raw, list):
                    news_items = raw
            except (json.JSONDecodeError, TypeError):
                pass

        # Parse stored weights from config_snapshot
        stored_weights = {}
        if r["config_snapshot"]:
            try:
                snap = json.loads(r["config_snapshot"])
                stored_weights = snap.get("weights", {})
            except (json.JSONDecodeError, TypeError):
                pass

        # Parse key_signals from technical_details
        key_signals = []
        if r["technical_details"]:
            try:
                td = json.loads(r["technical_details"])
                key_signals = td.get("key_signals", [])
            except (json.JSONDecodeError, TypeError):
                pass

        # Sentiment score is stored as -1..+1 fraction → scale to -100..+100
        raw_sent = r["sentiment_score"]
        if raw_sent is not None and abs(raw_sent) <= 1.0:
            stored_sent = float(raw_sent) * 100.0
        else:
            stored_sent = float(raw_sent) if raw_sent is not None else 0.0

        result.append(SignalRow(
            signal_id=r["signal_id"],
            ticker=r["ticker"],
            calculated_at=r["calculated_at"],
            rsi=_f(r["rsi"]),
            macd=_f(r["macd"]),
            macd_signal_val=_f(r["macd_signal_val"]),
            macd_histogram=_f(r["macd_histogram"]),
            sma_20=_f(r["sma_20"]),
            sma_50=_f(r["sma_50"]),
            sma_200=_f(r["sma_200"]),
            adx=_f(r["adx"]),
            bb_upper=_f(r["bb_upper"]),
            bb_lower=_f(r["bb_lower"]),
            bb_middle=_f(r["bb_middle"]),
            stoch_k=_f(r["stoch_k"]),
            stoch_d=_f(r["stoch_d"]),
            current_price=_f(r["current_price"]),
            volatility=_f(r["volatility"]),
            stored_sentiment_score=stored_sent,
            stored_technical_score=float(r["technical_score"]),
            stored_risk_score=float(r["risk_score"]),
            stored_combined_score=float(r["combined_score"]),
            stored_weight_sentiment=float(r["weight_sentiment"]) if r["weight_sentiment"] else 0.5,
            stored_weight_technical=float(r["weight_technical"]) if r["weight_technical"] else 0.35,
            stored_weight_risk=float(r["weight_risk"]) if r["weight_risk"] else 0.15,
            news_items=news_items,
            stored_weights=stored_weights,
            key_signals=key_signals,
        ))

    return result


def load_trade_outcomes(db_path: Path = DATABASE_PATH) -> Dict[int, dict]:
    """
    Load simulated_trades keyed by entry_signal_id.
    Used by the fitness function to look up trade P&L given a signal.

    Returns {signal_id: {pnl_percent, direction, status, exit_reason}}
    """
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT entry_signal_id, direction, status, exit_reason,
               pnl_percent, pnl_amount_huf
        FROM simulated_trades
        WHERE status = 'CLOSED'
    """).fetchall()
    conn.close()

    outcomes = {}
    for r in rows:
        outcomes[r[0]] = {
            "direction":    r[1],
            "status":       r[2],
            "exit_reason":  r[3],
            "pnl_percent":  r[4] if r[4] is not None else 0.0,
            "pnl_amount_huf": r[5] if r[5] is not None else 0.0,
        }
    return outcomes


# ---------------------------------------------------------------------------
# Score replay — the core computation
# ---------------------------------------------------------------------------

def replay_signal(row: SignalRow, cfg: dict) -> ReplayResult:
    """
    Recompute the combined score for one signal_calculations row
    using the provided config dict (output of parameter_space.decode_vector).

    Design principle:
      The original signal pipeline uses multi-timeframe data (5m/15m/1h/1d)
      that cannot be fully reproduced from the single stored indicator snapshot.
      Therefore:

      - Sentiment score: fully replayable from raw news_items + new decay weights
      - Technical score: the stored component scores (RSI zone, SMA cross etc.)
        are RESCALED using new tech component weights and signal score params.
        We use the stored raw indicator values (rsi, sma_20, stoch_k etc.) to
        recompute individual component contributions with new score parameters,
        then apply new component weights. The stored aggregate is not reused.
      - Risk score: reused from DB (S/R proximity cannot be replayed without
        full OHLCV + DBSCAN recalculation)
      - Combined: new weights × new component scores + new alignment bonus

    Steps:
      1. Sentiment score  (decay weights applied to raw news items)
      2. Technical score  (individual component scores with new params & weights)
      3. Risk score       (stored — not replayable)
      4. Combined score   (new weighted sum + alignment bonus)
      5. Decision         (BUY/SELL/HOLD via new hold_zone_threshold)
    """
    # --- 1. Sentiment score ---
    sentiment_score = _replay_sentiment(row, cfg)

    # --- 2. Technical score ---
    # Use stored raw indicator values with new signal score params and weights
    technical_score = _replay_technical(row, cfg)

    # --- 3. Risk score — reused from DB ---
    risk_score = row.stored_risk_score

    # --- 4. Combined score ---
    sw = cfg["SENTIMENT_WEIGHT"]
    tw = cfg["TECHNICAL_WEIGHT"]
    rw = cfg["RISK_WEIGHT"]

    base_combined = (
        sentiment_score * sw +
        technical_score * tw +
        risk_score      * rw
    )

    alignment_bonus = _calculate_alignment_bonus(
        sentiment_score, technical_score, risk_score, cfg
    )

    combined = base_combined + alignment_bonus

    # --- 5. Decision ---
    hold_zone = cfg["HOLD_ZONE_THRESHOLD"]
    if combined >= hold_zone:
        decision = "BUY"
    elif combined <= -hold_zone:
        decision = "SELL"
    else:
        decision = "HOLD"

    return ReplayResult(
        signal_id=row.signal_id,
        ticker=row.ticker,
        calculated_at=row.calculated_at,
        new_combined_score=combined,
        new_decision=decision,
        new_sentiment_score=sentiment_score,
        new_technical_score=technical_score,
        stored_risk_score=risk_score,
    )


# ---------------------------------------------------------------------------
# Sentiment replay
# ---------------------------------------------------------------------------

def _replay_sentiment(row: SignalRow, cfg: dict) -> float:
    """
    Recompute sentiment score from raw news items using new decay weights.
    Mirrors aggregate_sentiment_from_news() in signal_generator.py.

    Returns score in -100..+100 range.
    """
    if not row.news_items:
        return row.stored_sentiment_score

    decay_map = {
        "0-2h":   1.0,
        "2-6h":   cfg.get("DECAY_2_6H",   0.85),
        "6-12h":  cfg.get("DECAY_6_12H",  0.60),
        "12-24h": cfg.get("DECAY_12_24H", 0.35),
    }

    total_weight = 0.0
    weighted_sum = 0.0

    for item in row.news_items:
        score       = float(item.get("sentiment_score", 0.0))
        stored_decay = float(item.get("time_decay", 1.0))
        credibility  = float(item.get("weight", 1.0))

        # Determine which decay bucket this item's stored_decay corresponds to
        # and remap to the new decay weight.
        new_decay = _remap_decay(stored_decay, decay_map)
        effective = new_decay * credibility

        weighted_sum  += score * effective
        total_weight  += effective

    if total_weight <= 0.0:
        return row.stored_sentiment_score

    # weighted_avg is in -1..+1 → scale to -100..+100
    weighted_avg = weighted_sum / total_weight
    return float(weighted_avg) * 100.0


def _remap_decay(stored_decay: float, decay_map: dict) -> float:
    """
    Map a stored decay float to a new bucket weight.

    The stored time_decay in news_inputs was calculated with the original
    decay config. We infer the bucket by proximity to the default values
    and substitute the new bucket weight.

    Default buckets:  0-2h=1.0, 2-6h=0.85, 6-12h=0.60, 12-24h=0.35
    """
    if stored_decay >= 0.95:
        return decay_map["0-2h"]
    elif stored_decay >= 0.72:
        return decay_map["2-6h"]
    elif stored_decay >= 0.47:
        return decay_map["6-12h"]
    elif stored_decay > 0.0:
        return decay_map["12-24h"]
    else:
        return 0.0  # expired (>24h)


# ---------------------------------------------------------------------------
# Technical score replay
# ---------------------------------------------------------------------------

def _replay_technical(row: SignalRow, cfg: dict) -> float:
    """
    Recompute technical score from stored indicator values using new
    component weights and signal score params.

    Mirrors calculate_technical_score() + component scorers in signal_generator.py.
    Returns score in -100..+100 range.
    """
    price   = row.current_price
    rsi     = row.rsi
    sma20   = row.sma_20
    sma50   = row.sma_50
    sma200  = row.sma_200
    macd_h  = row.macd_histogram
    macd_v  = row.macd
    macd_s  = row.macd_signal_val
    bb_up   = row.bb_upper
    bb_lo   = row.bb_lower
    bb_mid  = row.bb_middle
    stoch_k = row.stoch_k
    adx     = row.adx

    # Determine trend direction from stored key_signals or SMA position
    is_bullish_trend = _infer_trend(row)

    # Compute each component score
    sma_score   = _score_sma(price, sma20, sma50, sma200, cfg)
    rsi_score   = _score_rsi(rsi, is_bullish_trend, cfg)
    macd_score  = _score_macd(macd_v, macd_s, macd_h)
    bb_score    = _score_bollinger(price, bb_up, bb_lo, bb_mid, is_bullish_trend)
    stoch_score = _score_stochastic(stoch_k, row.stoch_d, is_bullish_trend, cfg)
    vol_score   = 0.0  # volume not stored per-signal; weight is residual anyway

    # Weighted combination
    w_sma   = cfg.get("TECH_SMA_WEIGHT",        0.30)
    w_rsi   = cfg.get("TECH_RSI_WEIGHT",         0.25)
    w_macd  = cfg.get("TECH_MACD_WEIGHT",        0.20)
    w_bb    = cfg.get("TECH_BOLLINGER_WEIGHT",   0.15)
    w_stoch = cfg.get("TECH_STOCHASTIC_WEIGHT",  0.05)
    w_vol   = cfg.get("TECH_VOLUME_WEIGHT",      0.05)

    tech = (
        sma_score   * w_sma   +
        rsi_score   * w_rsi   +
        macd_score  * w_macd  +
        bb_score    * w_bb    +
        stoch_score * w_stoch +
        vol_score   * w_vol
    )

    return float(_clamp(tech, -100.0, 100.0))


def _infer_trend(row: SignalRow) -> Optional[bool]:
    """Infer bullish/bearish trend from stored key_signals and SMA values."""
    # First try SMA relationship
    if row.sma_20 and row.sma_50 and row.current_price:
        if row.current_price > row.sma_20 and row.sma_20 > row.sma_50:
            return True
        if row.current_price < row.sma_20 and row.sma_20 < row.sma_50:
            return False

    # Fall back to key_signals text
    signals_lower = " ".join(row.key_signals).lower()
    if "golden cross" in signals_lower or "price > sma" in signals_lower:
        return True
    if "death cross" in signals_lower or "price < sma" in signals_lower:
        return False

    return None  # neutral / unknown


def _score_sma(price, sma20, sma50, sma200, cfg: dict) -> float:
    """
    Mirrors calculate_sma_component_score() in signal_generator.py.
    Returns -100..+100.
    """
    if price is None:
        return 0.0

    score = 0.0

    sma20_bull = cfg.get("TECH_SMA20_BULLISH", 25)
    sma50_bull = cfg.get("TECH_SMA50_BULLISH", 20)
    golden     = cfg.get("TECH_GOLDEN_CROSS",  15)

    if sma20 and price > sma20:
        score += sma20_bull
    elif sma20 and price < sma20:
        score -= cfg.get("TECH_SMA20_BEARISH", sma20_bull)

    if sma50 and price > sma50:
        score += sma50_bull
    elif sma50 and price < sma50:
        score -= cfg.get("TECH_SMA50_BEARISH", sma50_bull)

    if sma20 and sma50:
        if sma20 > sma50:
            score += golden
        else:
            score -= cfg.get("TECH_DEATH_CROSS", golden)

    return _clamp(score, -100.0, 100.0)


def _score_rsi(rsi, is_bullish_trend, cfg: dict) -> float:
    """
    Mirrors calculate_rsi_component_score() — trend-aware RSI zones.
    Returns -100..+100.
    """
    if rsi is None:
        return 0.0

    ob        = cfg.get("RSI_OVERBOUGHT",    70)
    os_       = cfg.get("RSI_OVERSOLD",      30)
    nl        = cfg.get("RSI_NEUTRAL_LOW",   45)
    nh        = cfg.get("RSI_NEUTRAL_HIGH",  55)
    bull_sc   = cfg.get("TECH_RSI_BULLISH",  30)
    weak_bull = cfg.get("TECH_RSI_WEAK_BULLISH", 10)
    ob_sc     = cfg.get("TECH_RSI_OVERBOUGHT",   30)
    os_sc     = cfg.get("TECH_RSI_OVERSOLD",     30)
    neut_sc   = cfg.get("TECH_RSI_NEUTRAL",      20)

    if rsi >= ob:
        # Overbought
        if is_bullish_trend is True:
            return _clamp(-ob_sc * 0.5, -100.0, 100.0)  # half penalty in uptrend
        return _clamp(-ob_sc, -100.0, 100.0)

    elif rsi <= os_:
        # Oversold
        if is_bullish_trend is False:
            return _clamp(-os_sc * 0.5, -100.0, 100.0)  # half penalty in downtrend
        return _clamp(os_sc, -100.0, 100.0)

    elif nh < rsi < ob:
        return _clamp(bull_sc, -100.0, 100.0)

    elif nl <= rsi <= nh:
        return _clamp(neut_sc if is_bullish_trend is True else -neut_sc, -100.0, 100.0)

    elif os_ < rsi < nl:
        return _clamp(-weak_bull, -100.0, 100.0)

    return 0.0


def _score_macd(macd_val, macd_sig, macd_hist) -> float:
    """
    Mirrors calculate_macd_component_score().
    Histogram × 20 clamped to ±100, adjusted by crossover direction.
    """
    if macd_hist is None and (macd_val is None or macd_sig is None):
        return 0.0

    hist = macd_hist if macd_hist is not None else (macd_val - macd_sig)
    score = _clamp(hist * 20.0, -100.0, 100.0)

    # Crossover direction boost
    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig:
            score = min(100.0, score + 10.0)
        elif macd_val < macd_sig:
            score = max(-100.0, score - 10.0)

    return float(score)


def _score_bollinger(price, bb_up, bb_lo, bb_mid, is_bullish_trend) -> float:
    """
    Mirrors calculate_bollinger_component_score().
    Returns -100..+100.
    """
    if price is None or bb_up is None or bb_lo is None or bb_mid is None:
        return 0.0

    band_width = bb_up - bb_lo
    if band_width <= 0:
        return 0.0

    # Position within bands: -1 (at lower) to +1 (at upper)
    pos = (price - bb_mid) / (band_width / 2.0)

    if price > bb_up:
        score = -40.0 if is_bullish_trend is not True else -20.0
    elif price < bb_lo:
        score = 40.0 if is_bullish_trend is not False else 20.0
    else:
        # Linear interpolation: above mid = bullish signal, below = bearish
        score = _clamp(-pos * 30.0, -100.0, 100.0)
        if is_bullish_trend is True and pos > 0:
            score = _clamp(-pos * 15.0, -100.0, 100.0)  # weaker penalty in uptrend
        elif is_bullish_trend is False and pos < 0:
            score = _clamp(-pos * 15.0, -100.0, 100.0)

    return float(_clamp(score, -100.0, 100.0))


def _score_stochastic(stoch_k, stoch_d, is_bullish_trend, cfg: dict) -> float:
    """
    Mirrors calculate_stochastic_component_score().
    Returns -100..+100.
    """
    if stoch_k is None:
        return 0.0

    ob = cfg.get("STOCH_OVERBOUGHT", 80)
    os_ = cfg.get("STOCH_OVERSOLD", 20)

    if stoch_k >= ob:
        return _clamp(-40.0 if is_bullish_trend is not True else -20.0, -100.0, 100.0)
    elif stoch_k <= os_:
        return _clamp(40.0 if is_bullish_trend is not False else 20.0, -100.0, 100.0)
    else:
        # Linear: midpoint = 0
        midpoint = (ob + os_) / 2.0
        score = (stoch_k - midpoint) / (ob - midpoint) * 40.0
        return float(_clamp(score, -100.0, 100.0))


# ---------------------------------------------------------------------------
# Alignment bonus
# ---------------------------------------------------------------------------

def _calculate_alignment_bonus(
    sentiment: float,
    technical: float,
    risk: float,
    cfg: dict
) -> float:
    """
    Mirrors _calculate_alignment_bonus() in SignalGenerator.

    Awards bonus when pairs of components agree directionally and are strong.
    Sign matches the dominant direction.
    """
    tech_thr = cfg.get("ALIGNMENT_TECH_THRESHOLD", 60)
    sent_thr = cfg.get("ALIGNMENT_SENT_THRESHOLD", 40)
    risk_thr = cfg.get("ALIGNMENT_RISK_THRESHOLD", 40)

    bonus_all = cfg.get("ALIGNMENT_BONUS_ALL", 8)
    bonus_tr  = cfg.get("ALIGNMENT_BONUS_TR",  5)
    bonus_st  = cfg.get("ALIGNMENT_BONUS_ST",  5)
    bonus_sr  = cfg.get("ALIGNMENT_BONUS_SR",  3)

    # Strong in direction?
    tech_bull = technical >= tech_thr
    tech_bear = technical <= -tech_thr
    sent_bull = sentiment >= sent_thr
    sent_bear = sentiment <= -sent_thr
    risk_bull = risk >= risk_thr
    risk_bear = risk <= -risk_thr

    # BUY alignment
    if sent_bull and tech_bull and risk_bull:
        return bonus_all
    if tech_bull and risk_bull:
        return bonus_tr
    if sent_bull and tech_bull:
        return bonus_st
    if sent_bull and risk_bull:
        return bonus_sr

    # SELL alignment (negative bonus)
    if sent_bear and tech_bear and risk_bear:
        return -bonus_all
    if tech_bear and risk_bear:
        return -bonus_tr
    if sent_bear and tech_bear:
        return -bonus_st
    if sent_bear and risk_bear:
        return -bonus_sr

    return 0.0


# ---------------------------------------------------------------------------
# Batch replay — entry point for the optimizer
# ---------------------------------------------------------------------------

def replay_all(
    rows: List[SignalRow],
    cfg: dict
) -> List[ReplayResult]:
    """
    Replay all signal rows with the given config.
    Returns results in the same order as input rows.
    """
    return [replay_signal(r, cfg) for r in rows]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(v) -> Optional[float]:
    """Safe float conversion, returns None if NULL."""
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
