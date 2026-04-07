"""
TrendSignal Self-Tuning Engine - Score Backtester & Trade Simulator

Two-stage pipeline:
  Stage 1 (replay_scores):      Recompute combined scores and BUY/SELL/HOLD decisions
                                 using a new config vector. Pure Python, no DB.
  Stage 2 (replay_and_simulate): For each active signal, compute SL/TP under the new
                                 config and simulate the full trade candle-by-candle.

Key design:
  - All raw inputs are read once from the DB (load_all_sim_data in signal_data.py)
  - score recalculation uses compute_combined_score_from_indicators() —
    same function as live signal generation and archive score recalculation
  - trade simulation is in-memory, using pre-loaded price_data candles
  - SignalSimRow replaces the old SignalRow (superset of fields)
  - Old load_signal_rows / load_trade_outcomes are kept for backward compatibility

Version: 3.0 – score replay → compute_combined_score_from_indicators (12-component formula)
Date: 2026-04-06
"""

import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from optimizer.signal_data import SignalSimRow, PriceCandle, load_all_sim_data, _parse_ts
from optimizer.trade_simulator import (
    SimConfig, TradeSimResult,
    compute_sl_tp, simulate_trade,
    SIGNAL_THRESHOLD,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"


# ---------------------------------------------------------------------------
# Backward-compatible data structures (kept for fitness.py / test_step3.py)
# ---------------------------------------------------------------------------

@dataclass
class SignalRow:
    """
    Lightweight representation of one signal_calculations row.
    DEPRECATED: Use SignalSimRow for new code.
    Kept for backward compatibility with test_step3.py and fitness.py.
    """
    signal_id: int
    ticker: str
    calculated_at: str

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
    volatility: Optional[float]

    stored_sentiment_score: float
    stored_technical_score: float
    stored_risk_score: float
    stored_combined_score: float

    news_items: List[dict] = field(default_factory=list)
    stored_weight_sentiment: float = 0.5
    stored_weight_technical: float = 0.35
    stored_weight_risk: float = 0.15
    stored_weights: dict = field(default_factory=dict)
    key_signals: List[str] = field(default_factory=list)


@dataclass
class ReplayResult:
    """Result of replaying one signal with a new config (score only, no trade sim)."""
    signal_id: int
    ticker: str
    calculated_at: str
    new_combined_score: float
    new_decision: str
    new_sentiment_score: float
    new_technical_score: float
    stored_risk_score: float


# ---------------------------------------------------------------------------
# DB loaders (backward compat)
# ---------------------------------------------------------------------------

def load_signal_rows(db_path: Path = DATABASE_PATH) -> List[SignalRow]:
    """
    Load signal_calculations as SignalRow objects (score replay only).
    DEPRECATED: For new optimizer code, use load_all_sim_data() instead.
    Kept for backward compat and test_step3.py.
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
        news_items = []
        if r["news_inputs"]:
            try:
                raw = json.loads(r["news_inputs"])
                if isinstance(raw, list):
                    news_items = raw
            except (json.JSONDecodeError, TypeError):
                pass

        stored_weights = {}
        if r["config_snapshot"]:
            try:
                snap = json.loads(r["config_snapshot"])
                stored_weights = snap.get("weights", {})
            except (json.JSONDecodeError, TypeError):
                pass

        key_signals = []
        if r["technical_details"]:
            try:
                td = json.loads(r["technical_details"])
                key_signals = td.get("key_signals", [])
            except (json.JSONDecodeError, TypeError):
                pass

        raw_sent = r["sentiment_score"]
        if raw_sent is not None and abs(float(raw_sent)) <= 1.0:
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
    DEPRECATED: The new optimizer does not use fixed trade outcomes.
    Kept for backward compat and test_step3.py.
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
# Optimizer config adapter for compute_combined_score_from_indicators()
# ---------------------------------------------------------------------------

class _OptimizerConfig:
    """
    Lightweight config adapter that maps optimizer cfg dict keys to the
    attribute names expected by calculate_*_component_score() in signal_generator.py
    and compute_combined_score_from_indicators() in recalculate_signals.py.

    Fixed (non-tunable) values use production defaults.
    """
    __slots__ = [
        "COMPONENT_WEIGHTS",
        # SMA component params
        "tech_sma20_bullish", "tech_sma20_bearish",
        "tech_sma50_bullish", "tech_sma50_bearish",
        "tech_golden_cross",  "tech_death_cross",
        # RSI component params
        "rsi_neutral_low", "rsi_neutral_high",
        "rsi_overbought",  "rsi_oversold",
        "tech_rsi_neutral", "tech_rsi_bullish", "tech_rsi_weak_bullish",
        "tech_rsi_overbought", "tech_rsi_oversold",
        # Stochastic
        "stoch_overbought", "stoch_oversold",
        # ATR volatility thresholds (fixed — not optimized)
        "atr_vol_very_low", "atr_vol_low", "atr_vol_moderate", "atr_vol_high",
        # ADX thresholds (fixed — not optimized)
        "adx_very_strong", "adx_strong", "adx_moderate", "adx_weak", "adx_very_weak",
    ]

    def __init__(self, cfg: dict):
        # 12-component weights — sum must = 1.0 (enforced in decode_vector)
        self.COMPONENT_WEIGHTS = {
            "sma_trend":         cfg.get("CW_SMA_TREND",         0.15),
            "rsi_momentum":      cfg.get("CW_RSI_MOMENTUM",       0.07),
            "macd_signal":       cfg.get("CW_MACD_SIGNAL",        0.08),
            "bb_position":       cfg.get("CW_BB_POSITION",        0.04),
            "stoch_cross":       cfg.get("CW_STOCH_CROSS",        0.02),
            "volume_confirm":    cfg.get("CW_VOLUME_CONFIRM",     0.02),
            "sentiment_signal":  cfg.get("CW_SENTIMENT_SIGNAL",   0.30),
            "sentiment_recency": cfg.get("CW_SENTIMENT_RECENCY",  0.10),
            "volatility_risk":   cfg.get("CW_VOLATILITY_RISK",    0.08),
            "sr_proximity":      cfg.get("CW_SR_PROXIMITY",       0.08),
            "trend_strength":    cfg.get("CW_TREND_STRENGTH",     0.04),
            "rr_quality":        cfg.get("CW_RR_QUALITY",         0.02),
        }

        # SMA component (still tunable via TECH_SMA* params)
        self.tech_sma20_bullish = cfg.get("TECH_SMA20_BULLISH", 25)
        self.tech_sma20_bearish = cfg.get("TECH_SMA20_BULLISH", 25)  # symmetric
        self.tech_sma50_bullish = cfg.get("TECH_SMA50_BULLISH", 20)
        self.tech_sma50_bearish = cfg.get("TECH_SMA50_BULLISH", 20)  # symmetric
        self.tech_golden_cross  = cfg.get("TECH_GOLDEN_CROSS",  15)
        self.tech_death_cross   = cfg.get("TECH_GOLDEN_CROSS",  15)  # symmetric

        # RSI zones (tunable)
        self.rsi_overbought    = cfg.get("RSI_OVERBOUGHT",   70)
        self.rsi_oversold      = cfg.get("RSI_OVERSOLD",     30)
        self.rsi_neutral_low   = cfg.get("RSI_NEUTRAL_LOW",  45)
        self.rsi_neutral_high  = cfg.get("RSI_NEUTRAL_HIGH", 55)

        # RSI component scores (tunable)
        self.tech_rsi_bullish      = cfg.get("TECH_RSI_BULLISH",      30)
        self.tech_rsi_weak_bullish = cfg.get("TECH_RSI_WEAK_BULLISH", 10)
        self.tech_rsi_overbought   = cfg.get("TECH_RSI_OVERBOUGHT",   30)
        self.tech_rsi_oversold     = cfg.get("TECH_RSI_OVERSOLD",     30)
        self.tech_rsi_neutral      = cfg.get("TECH_RSI_NEUTRAL",      20)

        # Stochastic zones (tunable)
        self.stoch_overbought = cfg.get("STOCH_OVERBOUGHT", 80)
        self.stoch_oversold   = cfg.get("STOCH_OVERSOLD",   20)

        # ATR volatility thresholds (fixed production values)
        self.atr_vol_very_low = 0.5
        self.atr_vol_low      = 1.5
        self.atr_vol_moderate = 3.0
        self.atr_vol_high     = 5.0

        # ADX thresholds (fixed production values)
        self.adx_very_strong = 50
        self.adx_strong      = 40
        self.adx_moderate    = 25
        self.adx_weak        = 20
        self.adx_very_weak   = 10


# ---------------------------------------------------------------------------
# Score replay using the 12-component formula (matches live signal generation)
# ---------------------------------------------------------------------------

def replay_signal(row: SignalSimRow, cfg: dict) -> ReplayResult:
    """
    Recompute the combined score for one SignalSimRow using the 12-component
    formula via compute_combined_score_from_indicators().

    For live signals (news_items available): sentiment is re-calculated with
    the proposed decay weights before being passed to the formula.
    For archive signals (no news_items): stored sentiment_score is used directly.

    Accepts both SignalSimRow and legacy SignalRow (backward compat).
    """
    from src.recalculate_signals import compute_combined_score_from_indicators

    # Sentiment: re-tune decay for live signals; use stored for archive
    if getattr(row, "news_items", None):
        sentiment_score = _replay_sentiment(row, cfg)
    else:
        sentiment_score = row.stored_sentiment_score

    sentiment_confidence = getattr(row, "sentiment_confidence", 0.50) or 0.50
    risk_reward_ratio    = getattr(row, "risk_reward_ratio", None)

    ind = {
        "current_price":        row.current_price,
        "sma_20":               row.sma_20,
        "sma_50":               row.sma_50,
        "rsi":                  row.rsi,
        "macd_histogram":       row.macd_histogram,
        "bb_upper":             row.bb_upper,
        "bb_lower":             row.bb_lower,
        "bb_middle":            row.bb_middle,
        "stoch_k":              row.stoch_k,
        "stoch_d":              row.stoch_d,
        "atr_pct":              row.atr_pct or getattr(row, "volatility", None),
        "nearest_support":      row.nearest_support,
        "nearest_resistance":   row.nearest_resistance,
        "adx":                  row.adx,
        "sentiment_score":      sentiment_score,
        "sentiment_confidence": sentiment_confidence,
        "decision":             row.original_decision,
        "risk_reward_ratio":    risk_reward_ratio,
    }

    oc = _OptimizerConfig(cfg)
    result = compute_combined_score_from_indicators(ind, oc)
    combined = result["combined_score"]

    hold_zone = cfg.get("HOLD_ZONE_THRESHOLD", 15.0)
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
        new_technical_score=0.0,   # not separately tracked in 12-component formula
        stored_risk_score=0.0,     # not separately tracked in 12-component formula
    )


def replay_all(rows, cfg: dict) -> List[ReplayResult]:
    """Replay all signal rows with the given config (score only)."""
    return [replay_signal(r, cfg) for r in rows]


# ---------------------------------------------------------------------------
# Full pipeline: replay scores → SL/TP → trade simulation
# ---------------------------------------------------------------------------

def replay_and_simulate(
    rows: List[SignalSimRow],
    score_timeline: Dict[str, list],
    cfg: dict,
) -> List[TradeSimResult]:
    """
    Full optimizer evaluation pipeline for one config variant:

      1. replay_signal()     → new_decision + new_combined_score
      2. Filter active signals (|score| >= HOLD_ZONE_THRESHOLD and decision != HOLD)
      3. Entry gate filters  → block bad entries per new config thresholds
      4. compute_sl_tp()     → stop_loss, take_profit under new config
      5. simulate_trade()    → exit_reason, exit_price, pnl_percent

    Parameters
    ----------
    rows : List[SignalSimRow]
        All signal rows loaded by load_all_sim_data(). Must contain future_candles.
    score_timeline : Dict[str, list]
        {ticker: [(ts, score, sl, tp), ...]} — pre-loaded from signals table.
    cfg : dict
        Decoded config dict from parameter_space.decode_vector().

    Returns
    -------
    List[TradeSimResult]
        One entry per signal row. trade_active=False for HOLD / below-threshold signals.
    """
    sim_cfg = SimConfig.from_cfg(cfg)
    results = []

    for row in rows:
        # Stage 1: Score replay (12-component formula)
        replay = replay_signal(row, cfg)

        # Stage 2a: Filter — HOLD or below threshold
        if replay.new_decision == "HOLD" or abs(replay.new_combined_score) < sim_cfg.signal_threshold:
            results.append(TradeSimResult(
                signal_id=row.signal_id,
                ticker=row.ticker,
                calculated_at=row.calculated_at,
                original_decision=row.original_decision,
                new_decision=replay.new_decision,
                new_combined_score=replay.new_combined_score,
                trade_active=False,
            ))
            continue

        # Stage 2b: Entry gate filters
        _blocked   = False
        _direction = replay.new_decision  # "BUY" or "SELL"
        _rsi    = row.rsi
        _mhst   = row.macd_histogram
        _sma200 = row.sma_200
        _sma50  = row.sma_50
        _price  = row.current_price
        _resist = row.nearest_resistance

        _rsi_buy_max    = cfg.get("ENTRY_GATE_RSI_BUY_MAX",              70.0)
        _rsi_sell_min   = cfg.get("ENTRY_GATE_RSI_SELL_MIN",             65.0)
        _macd_buy_min   = cfg.get("ENTRY_GATE_MACD_HIST_BUY_MIN",         0.0)
        _macd_sell_max  = cfg.get("ENTRY_GATE_MACD_HIST_SELL_MAX",        0.0)
        _sma200_buy     = cfg.get("ENTRY_GATE_SMA200_BUY_MAX_PCT",        5.0)
        _sma200_sell    = cfg.get("ENTRY_GATE_SMA200_SELL_MIN_PCT",       -5.0)
        _dist_r_buy     = cfg.get("ENTRY_GATE_DIST_RESIST_BUY_MAX_PCT",  15.0)
        _sma50_sell_min = cfg.get("ENTRY_GATE_SMA50_SELL_MIN_PCT",         3.0)

        if _direction == "BUY":
            if _rsi  is not None and _rsi  >= _rsi_buy_max:
                _blocked = True
            if not _blocked and _mhst is not None and _mhst <= _macd_buy_min:
                _blocked = True
            if not _blocked and _sma200 and _sma200 > 0 and _price and _price > 0:
                if (_price - _sma200) / _sma200 * 100 > _sma200_buy:
                    _blocked = True
            if not _blocked and _resist and _price and _price > 0:
                if (_resist - _price) / _price * 100 > _dist_r_buy:
                    _blocked = True
        else:  # SELL
            if _rsi  is not None and _rsi  <= _rsi_sell_min:
                _blocked = True
            if not _blocked and _mhst is not None and _mhst >= _macd_sell_max:
                _blocked = True
            if not _blocked and _sma200 and _sma200 > 0 and _price and _price > 0:
                if (_price - _sma200) / _sma200 * 100 < _sma200_sell:
                    _blocked = True
            if not _blocked and _sma50 and _sma50 > 0 and _price and _price > 0:
                if (_price - _sma50) / _sma50 * 100 < _sma50_sell_min:
                    _blocked = True

        if _blocked:
            results.append(TradeSimResult(
                signal_id=row.signal_id,
                ticker=row.ticker,
                calculated_at=row.calculated_at,
                original_decision=row.original_decision,
                new_decision=replay.new_decision,
                new_combined_score=replay.new_combined_score,
                trade_active=False,
            ))
            continue

        # Stage 3: SL/TP computation
        entry_price = row.current_price
        if entry_price is None or entry_price <= 0:
            results.append(TradeSimResult(
                signal_id=row.signal_id,
                ticker=row.ticker,
                calculated_at=row.calculated_at,
                original_decision=row.original_decision,
                new_decision=replay.new_decision,
                new_combined_score=replay.new_combined_score,
                trade_active=False,
            ))
            continue

        atr     = row.atr     or (entry_price * 0.02)
        atr_pct = row.atr_pct or 2.0
        conf    = row.confidence or 0.60

        try:
            sl, tp, sl_method, tp_method = compute_sl_tp(
                decision=replay.new_decision,
                entry_price=entry_price,
                atr=atr,
                atr_pct=atr_pct,
                confidence=conf,
                nearest_support=row.nearest_support,
                nearest_resistance=row.nearest_resistance,
                sim_cfg=sim_cfg,
            )
        except Exception:
            results.append(TradeSimResult(
                signal_id=row.signal_id,
                ticker=row.ticker,
                calculated_at=row.calculated_at,
                original_decision=row.original_decision,
                new_decision=replay.new_decision,
                new_combined_score=replay.new_combined_score,
                trade_active=False,
            ))
            continue

        # Sanity check: SL/TP must be on correct side of entry
        if replay.new_decision == "BUY" and (sl >= entry_price or tp <= entry_price):
            results.append(TradeSimResult(
                signal_id=row.signal_id,
                ticker=row.ticker,
                calculated_at=row.calculated_at,
                original_decision=row.original_decision,
                new_decision=replay.new_decision,
                new_combined_score=replay.new_combined_score,
                trade_active=False,
            ))
            continue
        if replay.new_decision == "SELL" and (sl <= entry_price or tp >= entry_price):
            results.append(TradeSimResult(
                signal_id=row.signal_id,
                ticker=row.ticker,
                calculated_at=row.calculated_at,
                original_decision=row.original_decision,
                new_decision=replay.new_decision,
                new_combined_score=replay.new_combined_score,
                trade_active=False,
            ))
            continue

        # Stage 4: Trade simulation (delegates to trade_simulator_core — same as archive backtest)
        direction = "LONG" if replay.new_decision == "BUY" else "SHORT"
        entry_ts  = _parse_ts(row.calculated_at)
        ticker_timeline = score_timeline.get(row.ticker, [])

        try:
            exit_reason, exit_price, pnl = simulate_trade(
                direction=direction,
                entry_price=entry_price,
                stop_loss=sl,
                take_profit=tp,
                entry_ts=entry_ts,
                ticker=row.ticker,
                future_candles=row.future_candles,
                score_timeline=ticker_timeline,
                sim_cfg=sim_cfg,
            )
        except Exception:
            exit_reason, exit_price, pnl = "NO_EXIT", entry_price, 0.0

        results.append(TradeSimResult(
            signal_id=row.signal_id,
            ticker=row.ticker,
            calculated_at=row.calculated_at,
            original_decision=row.original_decision,
            new_decision=replay.new_decision,
            new_combined_score=replay.new_combined_score,
            trade_active=True,
            direction=direction,
            entry_price=entry_price,
            stop_loss=sl,
            take_profit=tp,
            sl_method=sl_method,
            tp_method=tp_method,
            exit_reason=exit_reason,
            exit_price=exit_price,
            pnl_percent=pnl,
        ))

    return results


# ---------------------------------------------------------------------------
# Sentiment replay (decay re-tuning for live signals with news_items)
# ---------------------------------------------------------------------------

def _replay_sentiment(row, cfg: dict) -> float:
    """
    Re-calculate sentiment score from news_items with proposed decay weights.
    Falls back to stored_sentiment_score when news_items is empty.
    Used for live signals (signal_calculations) which have individual news items stored.
    Archive signals return stored_sentiment_score directly (no news_items).
    """
    if not row.news_items:
        return row.stored_sentiment_score

    decay_map = {
        "0-2h":   1.0,
        "2-6h":   cfg.get("DECAY_2_6H",   0.50),
        "6-12h":  cfg.get("DECAY_6_12H",  0.50),
        "12-24h": cfg.get("DECAY_12_24H", 0.37),
    }

    total_weight = 0.0
    weighted_sum = 0.0

    for item in row.news_items:
        score        = float(item.get("sentiment_score", 0.0))
        stored_decay = float(item.get("time_decay", 1.0))
        credibility  = float(item.get("weight", 1.0))
        new_decay    = _remap_decay(stored_decay, decay_map)
        effective    = new_decay * credibility
        weighted_sum += score * effective
        total_weight += effective

    if total_weight <= 0.0:
        return row.stored_sentiment_score

    return float(weighted_sum / total_weight) * 100.0


def _remap_decay(stored_decay: float, decay_map: dict) -> float:
    if stored_decay >= 0.95:
        return decay_map["0-2h"]
    elif stored_decay >= 0.72:
        return decay_map["2-6h"]
    elif stored_decay >= 0.47:
        return decay_map["6-12h"]
    elif stored_decay > 0.0:
        return decay_map["12-24h"]
    else:
        return 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
