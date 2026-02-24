"""
TrendSignal Self-Tuning Engine - Score Backtester & Trade Simulator

Two-stage pipeline:
  Stage 1 (replay_scores):      Recompute combined scores and BUY/SELL/HOLD decisions
                                 using a new config vector. Pure Python, no DB.
  Stage 2 (replay_and_simulate): For each active signal, compute SL/TP under the new
                                 config and simulate the full trade candle-by-candle.

Key design:
  - All raw inputs are read once from the DB (load_all_sim_data in signal_data.py)
  - score recalculation is pure Python — no DB writes during evaluation
  - trade simulation is in-memory, using pre-loaded price_data candles
  - SignalSimRow replaces the old SignalRow (superset of fields)
  - Old load_signal_rows / load_trade_outcomes are kept for backward compatibility

Version: 2.0
Date: 2026-02-24
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
# Score replay  (unchanged from v1 — works with both SignalRow and SignalSimRow)
# ---------------------------------------------------------------------------

def replay_signal(row, cfg: dict) -> ReplayResult:
    """
    Recompute the combined score for one row using the provided config dict.
    Accepts both SignalRow and SignalSimRow.
    """
    sentiment_score = _replay_sentiment(row, cfg)
    technical_score = _replay_technical(row, cfg)
    risk_score      = row.stored_risk_score

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

    combined  = base_combined + alignment_bonus
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
      3. compute_sl_tp()     → stop_loss, take_profit under new config
      4. simulate_trade()    → exit_reason, exit_price, pnl_percent

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
        # Stage 1: Score replay
        replay = replay_signal(row, cfg)

        # Stage 2: Filter
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

        # Stage 4: Trade simulation
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
# Sentiment replay
# ---------------------------------------------------------------------------

def _replay_sentiment(row, cfg: dict) -> float:
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
# Technical score replay
# ---------------------------------------------------------------------------

def _replay_technical(row, cfg: dict) -> float:
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

    is_bullish_trend = _infer_trend(row)

    sma_score   = _score_sma(price, sma20, sma50, sma200, cfg)
    rsi_score   = _score_rsi(rsi, is_bullish_trend, cfg)
    macd_score  = _score_macd(macd_v, macd_s, macd_h)
    bb_score    = _score_bollinger(price, bb_up, bb_lo, bb_mid, is_bullish_trend)
    stoch_score = _score_stochastic(stoch_k, row.stoch_d, is_bullish_trend, cfg)
    vol_score   = 0.0

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


def _infer_trend(row) -> Optional[bool]:
    if row.sma_20 and row.sma_50 and row.current_price:
        if row.current_price > row.sma_20 and row.sma_20 > row.sma_50:
            return True
        if row.current_price < row.sma_20 and row.sma_20 < row.sma_50:
            return False
    signals_lower = " ".join(row.key_signals).lower()
    if "golden cross" in signals_lower or "price > sma" in signals_lower:
        return True
    if "death cross" in signals_lower or "price < sma" in signals_lower:
        return False
    return None


def _score_sma(price, sma20, sma50, sma200, cfg: dict) -> float:
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
    if rsi is None:
        return 0.0
    ob      = cfg.get("RSI_OVERBOUGHT",      70)
    os_     = cfg.get("RSI_OVERSOLD",        30)
    nl      = cfg.get("RSI_NEUTRAL_LOW",     45)
    nh      = cfg.get("RSI_NEUTRAL_HIGH",    55)
    bull_sc = cfg.get("TECH_RSI_BULLISH",    30)
    weak_b  = cfg.get("TECH_RSI_WEAK_BULLISH", 10)
    ob_sc   = cfg.get("TECH_RSI_OVERBOUGHT", 30)
    os_sc   = cfg.get("TECH_RSI_OVERSOLD",   30)
    neut_sc = cfg.get("TECH_RSI_NEUTRAL",    20)
    if rsi >= ob:
        return _clamp(-ob_sc * 0.5 if is_bullish_trend is True else -ob_sc, -100.0, 100.0)
    elif rsi <= os_:
        return _clamp(-os_sc * 0.5 if is_bullish_trend is False else os_sc, -100.0, 100.0)
    elif nh < rsi < ob:
        return _clamp(bull_sc, -100.0, 100.0)
    elif nl <= rsi <= nh:
        return _clamp(neut_sc if is_bullish_trend is True else -neut_sc, -100.0, 100.0)
    elif os_ < rsi < nl:
        return _clamp(-weak_b, -100.0, 100.0)
    return 0.0


def _score_macd(macd_val, macd_sig, macd_hist) -> float:
    if macd_hist is None and (macd_val is None or macd_sig is None):
        return 0.0
    hist  = macd_hist if macd_hist is not None else (macd_val - macd_sig)
    score = _clamp(hist * 20.0, -100.0, 100.0)
    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig:
            score = min(100.0, score + 10.0)
        elif macd_val < macd_sig:
            score = max(-100.0, score - 10.0)
    return float(score)


def _score_bollinger(price, bb_up, bb_lo, bb_mid, is_bullish_trend) -> float:
    if price is None or bb_up is None or bb_lo is None or bb_mid is None:
        return 0.0
    band_width = bb_up - bb_lo
    if band_width <= 0:
        return 0.0
    pos = (price - bb_mid) / (band_width / 2.0)
    if price > bb_up:
        score = -20.0 if is_bullish_trend is True else -40.0
    elif price < bb_lo:
        score = 20.0 if is_bullish_trend is False else 40.0
    else:
        score = _clamp(-pos * 30.0, -100.0, 100.0)
        if is_bullish_trend is True and pos > 0:
            score = _clamp(-pos * 15.0, -100.0, 100.0)
        elif is_bullish_trend is False and pos < 0:
            score = _clamp(-pos * 15.0, -100.0, 100.0)
    return float(_clamp(score, -100.0, 100.0))


def _score_stochastic(stoch_k, stoch_d, is_bullish_trend, cfg: dict) -> float:
    if stoch_k is None:
        return 0.0
    ob  = cfg.get("STOCH_OVERBOUGHT", 80)
    os_ = cfg.get("STOCH_OVERSOLD",   20)
    if stoch_k >= ob:
        return _clamp(-20.0 if is_bullish_trend is True else -40.0, -100.0, 100.0)
    elif stoch_k <= os_:
        return _clamp(20.0 if is_bullish_trend is False else 40.0, -100.0, 100.0)
    else:
        midpoint = (ob + os_) / 2.0
        score = (stoch_k - midpoint) / (ob - midpoint) * 40.0
        return float(_clamp(score, -100.0, 100.0))


# ---------------------------------------------------------------------------
# Alignment bonus
# ---------------------------------------------------------------------------

def _calculate_alignment_bonus(sentiment: float, technical: float, risk: float, cfg: dict) -> float:
    tech_thr  = cfg.get("ALIGNMENT_TECH_THRESHOLD", 60)
    sent_thr  = cfg.get("ALIGNMENT_SENT_THRESHOLD", 40)
    bonus_all = cfg.get("ALIGNMENT_BONUS_ALL", 8)
    bonus_tr  = cfg.get("ALIGNMENT_BONUS_TR",  5)
    bonus_st  = cfg.get("ALIGNMENT_BONUS_ST",  5)
    bonus_sr  = cfg.get("ALIGNMENT_BONUS_SR",  3)

    tech_bull = technical >= tech_thr;  tech_bear = technical <= -tech_thr
    sent_bull = sentiment >= sent_thr;  sent_bear = sentiment <= -sent_thr
    risk_bull = risk >= 40;             risk_bear = risk <= -40

    if sent_bull and tech_bull and risk_bull:
        return bonus_all
    if tech_bull and risk_bull:
        return bonus_tr
    if sent_bull and tech_bull:
        return bonus_st
    if sent_bull and risk_bull:
        return bonus_sr
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
