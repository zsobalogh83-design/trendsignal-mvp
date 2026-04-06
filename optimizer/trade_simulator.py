"""
TrendSignal Self-Tuning Engine - Trade Simulator

Performs full in-memory trade simulation for a given config variant:
  1. compute_sl_tp()   : Reproduces signal_generator.py SL/TP logic exactly
  2. simulate_trade()  : Delegál a src.trade_simulator_core.simulate_exit()-hez
                         → ugyanaz a szimulációs logika mint az archive_backtest_service-ben

Key design:
  - Zero DB access during simulation (all data pre-loaded by signal_data.py)
  - simulate_trade() a kanonikus core-t hívja → soha nem divergál a live/archive logikától
  - compute_sl_tp() és SimConfig megmaradnak (SL/TP számításhoz szükségesek)

Version: 3.0 – simulate_trade() → trade_simulator_core delegálás
Date: 2026-03-29
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.trade_simulator_core import (
    simulate_exit as _core_simulate_exit,
    ALERT_THRESHOLD as _ALERT_THRESHOLD,
)

from optimizer.signal_data import PriceCandle

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum |combined_score| for a trade to be opened
SIGNAL_THRESHOLD = 15.0

# SL cannot be wider than this % of entry price
SL_MAX_PCT = 0.05          # 5%

# Minimum risk:reward ratio (enforced by pushing TP, never tightening SL)
MIN_RISK_REWARD = 1.5

# S/R discount for TP: pull TP slightly inside the S/R level for realistic fill
TAKE_PROFIT_SR_DISCOUNT = 0.005  # 0.5%


# ---------------------------------------------------------------------------
# SimConfig: SL/TP-related parameters drawn from the optimizer config dict
# ---------------------------------------------------------------------------

@dataclass
class SimConfig:
    """
    SL/TP config parameters for one optimizer config variant.
    Extracted from the full cfg dict produced by decode_vector().
    """
    # Signal threshold
    signal_threshold: float = SIGNAL_THRESHOLD

    # ATR stop-loss multipliers (confidence-adaptive)
    atr_stop_high_conf: float = 1.5    # confidence >= 0.75
    atr_stop_default: float   = 2.0    # 0.50 <= conf < 0.75
    atr_stop_low_conf: float  = 2.5    # conf < 0.50

    # ATR take-profit multipliers (volatility-adaptive)
    atr_tp_low_vol: float  = 2.5       # atr_pct < vol_low_threshold
    atr_tp_high_vol: float = 4.0       # atr_pct > vol_high_threshold

    # Volatility thresholds for TP multiplier selection
    vol_low_threshold:  float = 2.0    # % ATR
    vol_high_threshold: float = 4.0    # % ATR

    # S/R blend thresholds for SL (mirrors config.sr_support_*_distance_pct)
    sr_support_soft_pct: float = 2.0
    sr_support_hard_pct: float = 4.0

    # S/R blend thresholds for TP (mirrors config.sr_resistance_*_distance_pct)
    sr_resistance_soft_pct: float = 3.0
    sr_resistance_hard_pct: float = 6.5

    # ATR buffer added to S/R level for SL placement (mirrors config.stop_loss_sr_buffer)
    sr_buffer_atr_mult: float = 0.3

    # SHORT daytrade SL/TP multipliers (külön a LONG swing multiplierektől)
    short_atr_stop_high_conf: float = 0.5
    short_atr_stop_default:   float = 0.7
    short_atr_stop_low_conf:  float = 1.0
    short_atr_tp_low_vol:     float = 1.0
    short_atr_tp_high_vol:    float = 1.8
    short_sl_max_pct:         float = 0.015

    # LONG trade max holding period (kereskedési napokban)
    long_max_hold_days:           int   = 5
    long_trailing_tighten_day:    int   = 3
    long_trailing_tighten_factor: float = 0.6

    @classmethod
    def from_cfg(cls, cfg: dict) -> "SimConfig":
        """Extract sim-relevant params from a decoded config dict."""
        return cls(
            signal_threshold   = cfg.get("HOLD_ZONE_THRESHOLD", SIGNAL_THRESHOLD),
            atr_stop_high_conf = cfg.get("ATR_STOP_HIGH_CONF", 1.5),
            atr_stop_default   = cfg.get("ATR_STOP_DEFAULT",   2.0),
            atr_stop_low_conf  = cfg.get("ATR_STOP_LOW_CONF",  2.5),
            atr_tp_low_vol     = cfg.get("ATR_TP_LOW_VOL",     2.5),
            atr_tp_high_vol    = cfg.get("ATR_TP_HIGH_VOL",    4.0),
            vol_low_threshold  = cfg.get("VOL_LOW_THRESHOLD",  2.0),
            vol_high_threshold = cfg.get("VOL_HIGH_THRESHOLD", 4.0),
            sr_support_soft_pct     = cfg.get("SR_SUPPORT_SOFT_PCT",     2.0),
            sr_support_hard_pct     = cfg.get("SR_SUPPORT_HARD_PCT",     4.0),
            sr_resistance_soft_pct  = cfg.get("SR_RESISTANCE_SOFT_PCT",  3.0),
            sr_resistance_hard_pct  = cfg.get("SR_RESISTANCE_HARD_PCT",  6.5),
            sr_buffer_atr_mult      = cfg.get("SR_BUFFER_ATR_MULT",      0.3),
            short_atr_stop_high_conf = cfg.get("SHORT_ATR_STOP_HIGH_CONF", 0.5),
            short_atr_stop_default   = cfg.get("SHORT_ATR_STOP_DEFAULT",   0.7),
            short_atr_stop_low_conf  = cfg.get("SHORT_ATR_STOP_LOW_CONF",  1.0),
            short_atr_tp_low_vol     = cfg.get("SHORT_ATR_TP_LOW_VOL",     1.0),
            short_atr_tp_high_vol    = cfg.get("SHORT_ATR_TP_HIGH_VOL",    1.8),
            short_sl_max_pct         = cfg.get("SHORT_SL_MAX_PCT",         0.015),
            long_max_hold_days           = int(cfg.get("LONG_MAX_HOLD_DAYS",           5)),
            long_trailing_tighten_day    = int(cfg.get("LONG_TRAILING_TIGHTEN_DAY",    3)),
            long_trailing_tighten_factor = cfg.get("LONG_TRAILING_TIGHTEN_FACTOR", 0.6),
        )


# ---------------------------------------------------------------------------
# TradeSimResult
# ---------------------------------------------------------------------------

@dataclass
class TradeSimResult:
    """
    Result of simulating one signal through a config variant.
    If trade_active=False the signal did not generate a trade (HOLD or below threshold).
    """
    signal_id: int
    ticker: str
    calculated_at: str

    original_decision: str          # DB-stored decision
    new_decision: str               # Replayed decision under new config
    new_combined_score: float

    trade_active: bool              # False → no trade (skip in fitness)

    # Set when trade_active=True
    direction: str = ""             # "LONG" | "SHORT"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    sl_method: str = ""
    tp_method: str = ""

    exit_reason: str = ""           # SL_HIT | TP_HIT | OPPOSING_SIGNAL | EOD_LIQUIDATION | NO_EXIT
    exit_price: float = 0.0
    pnl_percent: float = 0.0        # Positive = profit, negative = loss


# ---------------------------------------------------------------------------
# SL/TP computation  (mirrors signal_generator.py lines 640–833)
# ---------------------------------------------------------------------------

def compute_sl_tp(
    decision: str,
    entry_price: float,
    atr: float,
    atr_pct: float,
    confidence: float,
    nearest_support: Optional[float],
    nearest_resistance: Optional[float],
    sim_cfg: SimConfig,
) -> Tuple[float, float, str, str]:
    """
    Reproduce signal_generator.py SL/TP calculation for a given direction.

    Parameters
    ----------
    decision : "BUY" or "SELL"
    entry_price : current market price at signal time
    atr : ATR in price units
    atr_pct : ATR as % of price (for TP volatility-adaptive mult)
    confidence : overall_confidence (determines SL ATR multiplier)
    nearest_support, nearest_resistance : closest S/R levels (or None)
    sim_cfg : SimConfig with ATR multipliers and S/R blend thresholds

    Returns
    -------
    (stop_loss, take_profit, sl_method, tp_method)
    """
    # SHORT (SELL) daytrade multiplierek — szűkebb SL/TP, napi range-en belül befutható.
    # LONG (BUY) swing multiplierek — szélesebb, multi-day range.
    if "BUY" in decision:
        # --- Confidence-adaptive SL multiplier (LONG swing) ---
        if confidence >= 0.75:
            atr_sl_mult = sim_cfg.atr_stop_high_conf
        elif confidence < 0.50:
            atr_sl_mult = sim_cfg.atr_stop_low_conf
        else:
            atr_sl_mult = sim_cfg.atr_stop_default

        # --- Volatility-adaptive TP multiplier (LONG swing) ---
        if atr_pct < sim_cfg.vol_low_threshold:
            atr_tp_mult = sim_cfg.atr_tp_low_vol
        elif atr_pct > sim_cfg.vol_high_threshold:
            atr_tp_mult = sim_cfg.atr_tp_high_vol
        else:
            t = (atr_pct - sim_cfg.vol_low_threshold) / (
                sim_cfg.vol_high_threshold - sim_cfg.vol_low_threshold
            )
            atr_tp_mult = sim_cfg.atr_tp_low_vol + t * (
                sim_cfg.atr_tp_high_vol - sim_cfg.atr_tp_low_vol
            )
    else:
        # --- Confidence-adaptive SL multiplier (SHORT daytrade) ---
        if confidence >= 0.75:
            atr_sl_mult = sim_cfg.short_atr_stop_high_conf
        elif confidence < 0.50:
            atr_sl_mult = sim_cfg.short_atr_stop_low_conf
        else:
            atr_sl_mult = sim_cfg.short_atr_stop_default

        # --- Volatility-adaptive TP multiplier (SHORT daytrade) ---
        if atr_pct < sim_cfg.vol_low_threshold:
            atr_tp_mult = sim_cfg.short_atr_tp_low_vol
        elif atr_pct > sim_cfg.vol_high_threshold:
            atr_tp_mult = sim_cfg.short_atr_tp_high_vol
        else:
            t = (atr_pct - sim_cfg.vol_low_threshold) / (
                sim_cfg.vol_high_threshold - sim_cfg.vol_low_threshold
            )
            atr_tp_mult = sim_cfg.short_atr_tp_low_vol + t * (
                sim_cfg.short_atr_tp_high_vol - sim_cfg.short_atr_tp_low_vol
            )

    if "BUY" in decision:
        stop_loss, sl_method = _compute_buy_sl(
            entry_price, atr, atr_sl_mult, nearest_support, sim_cfg
        )
        take_profit, tp_method = _compute_buy_tp(
            entry_price, atr, atr_tp_mult, nearest_resistance, sim_cfg
        )
    else:
        stop_loss, sl_method = _compute_sell_sl(
            entry_price, atr, atr_sl_mult, nearest_resistance, sim_cfg
        )
        take_profit, tp_method = _compute_sell_tp(
            entry_price, atr, atr_tp_mult, nearest_support, sim_cfg
        )

    # --- Boundary enforcement (mirrors signal_generator.py lines 796–833) ---
    # SHORT daytrade: szűkebb SL cap (1.5%), LONG swing: 5%
    sl_max_pct = sim_cfg.short_sl_max_pct if "SELL" in decision else SL_MAX_PCT
    stop_loss, take_profit, sl_method, tp_method = _enforce_sl_tp_bounds(
        decision, entry_price, stop_loss, take_profit, sl_method, tp_method, atr,
        sl_max_pct=sl_max_pct,
    )

    return stop_loss, take_profit, sl_method, tp_method


def _blend(
    sr_price: float,
    atr_price: float,
    distance_pct: float,
    soft_limit: float,
    hard_limit: float,
) -> Tuple[float, str]:
    """
    Soft blend between S/R price and ATR-based price.
    Mirrors signal_generator.py blend() helper.
    """
    if distance_pct <= soft_limit:
        return sr_price, "sr"
    elif distance_pct >= hard_limit:
        return atr_price, "atr"
    else:
        t = (distance_pct - soft_limit) / (hard_limit - soft_limit)
        blended = sr_price + t * (atr_price - sr_price)
        return blended, "blended"


def _compute_buy_sl(
    entry: float, atr: float, atr_mult: float,
    nearest_support: Optional[float], sim_cfg: SimConfig,
) -> Tuple[float, str]:
    atr_sl = entry - (atr * atr_mult)
    sl_method = "atr"

    if nearest_support and nearest_support < entry:
        dist_pct = ((entry - nearest_support) / entry) * 100.0
        sr_sl = nearest_support - (atr * sim_cfg.sr_buffer_atr_mult)
        if sr_sl < entry:
            return _blend(
                sr_price=sr_sl, atr_price=atr_sl,
                distance_pct=dist_pct,
                soft_limit=sim_cfg.sr_support_soft_pct,
                hard_limit=sim_cfg.sr_support_hard_pct,
            )
    return atr_sl, sl_method


def _compute_buy_tp(
    entry: float, atr: float, atr_mult: float,
    nearest_resistance: Optional[float], sim_cfg: SimConfig,
) -> Tuple[float, str]:
    atr_tp = entry + (atr * atr_mult)
    tp_method = "atr"

    if nearest_resistance and nearest_resistance > entry:
        dist_pct = ((nearest_resistance - entry) / entry) * 100.0
        sr_tp = nearest_resistance * (1.0 - TAKE_PROFIT_SR_DISCOUNT)
        return _blend(
            sr_price=sr_tp, atr_price=atr_tp,
            distance_pct=dist_pct,
            soft_limit=sim_cfg.sr_resistance_soft_pct,
            hard_limit=sim_cfg.sr_resistance_hard_pct,
        )
    return atr_tp, tp_method


def _compute_sell_sl(
    entry: float, atr: float, atr_mult: float,
    nearest_resistance: Optional[float], sim_cfg: SimConfig,
) -> Tuple[float, str]:
    atr_sl = entry + (atr * atr_mult)
    sl_method = "atr"

    if nearest_resistance and nearest_resistance > entry:
        dist_pct = ((nearest_resistance - entry) / entry) * 100.0
        sr_sl = nearest_resistance + (atr * sim_cfg.sr_buffer_atr_mult)
        if sr_sl > entry:
            return _blend(
                sr_price=sr_sl, atr_price=atr_sl,
                distance_pct=dist_pct,
                soft_limit=sim_cfg.sr_support_soft_pct,
                hard_limit=sim_cfg.sr_support_hard_pct,
            )
    return atr_sl, sl_method


def _compute_sell_tp(
    entry: float, atr: float, atr_mult: float,
    nearest_support: Optional[float], sim_cfg: SimConfig,
) -> Tuple[float, str]:
    atr_tp = entry - (atr * atr_mult)
    tp_method = "atr"

    if nearest_support and nearest_support < entry:
        dist_pct = ((entry - nearest_support) / entry) * 100.0
        sr_tp = nearest_support * (1.0 + TAKE_PROFIT_SR_DISCOUNT)
        return _blend(
            sr_price=sr_tp, atr_price=atr_tp,
            distance_pct=dist_pct,
            soft_limit=sim_cfg.sr_resistance_soft_pct,
            hard_limit=sim_cfg.sr_resistance_hard_pct,
        )
    return atr_tp, tp_method


def _enforce_sl_tp_bounds(
    decision: str,
    entry: float,
    stop_loss: float,
    take_profit: float,
    sl_method: str,
    tp_method: str,
    atr: float,
    sl_max_pct: float = SL_MAX_PCT,
) -> Tuple[float, float, str, str]:
    """Enforce SL max cap and minimum R:R. Mirrors signal_generator.py lines 796-833."""
    # Step 1: SL max cap (SHORT daytrade: short_sl_max_pct, LONG swing: SL_MAX_PCT)
    sl_max_dist = entry * sl_max_pct
    risk = abs(entry - stop_loss)

    if risk > sl_max_dist:
        if "BUY" in decision:
            stop_loss = entry - sl_max_dist
        else:
            stop_loss = entry + sl_max_dist
        sl_method = "capped"
        risk = sl_max_dist

    if risk <= 0:
        # Degenerate: use ATR as fallback
        risk = atr * 1.5
        if "BUY" in decision:
            stop_loss = entry - risk
        else:
            stop_loss = entry + risk
        sl_method = "atr_fallback"

    # Step 2: Enforce minimum R:R by pushing TP further (never tighten SL)
    reward = abs(take_profit - entry)
    if reward < risk * MIN_RISK_REWARD:
        target_reward = risk * MIN_RISK_REWARD
        if "BUY" in decision:
            candidate_tp = entry + target_reward
            if candidate_tp > take_profit:
                take_profit = candidate_tp
                tp_method = "rr_target"
        else:
            candidate_tp = entry - target_reward
            if candidate_tp < take_profit:
                take_profit = candidate_tp
                tp_method = "rr_target"

    return stop_loss, take_profit, sl_method, tp_method


# ---------------------------------------------------------------------------
# Trade simulation — delegál a src.trade_simulator_core-hoz
# ---------------------------------------------------------------------------

def simulate_trade(
    direction: str,                     # "LONG" or "SHORT"
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    entry_ts: datetime,                 # Signal timestamp (UTC naive)
    ticker: str,
    future_candles: List[PriceCandle],  # All 15m candles after entry (pre-loaded)
    score_timeline: List[Tuple[datetime, float, Optional[float], Optional[float]]],
    # ^ [(ts, combined_score, sl, tp)] for this ticker, all time
    sim_cfg: Optional[SimConfig] = None,
) -> Tuple[str, float, float]:
    """
    Kanonikus exit szimuláció — delegál a src.trade_simulator_core.simulate_exit()-hez.
    Azonos logikát futtat mint az archive_backtest_service és a live trade szimuláció.

    Returns
    -------
    (exit_reason, exit_price, pnl_percent)
    """
    if not future_candles:
        return "NO_EXIT", entry_price, 0.0

    # score_timeline → opp_list + same_dir_signals (ahogy az archive backtest csinálja)
    if direction == "LONG":
        opp_list = sorted([ts for ts, s, _, _ in score_timeline if s <= -_ALERT_THRESHOLD])
        same_dir_signals = sorted(
            [(ts, sl) for ts, s, sl, _ in score_timeline
             if s >= _ALERT_THRESHOLD and sl is not None],
            key=lambda x: x[0],
        )
    else:
        opp_list = sorted([ts for ts, s, _, _ in score_timeline if s >= _ALERT_THRESHOLD])
        same_dir_signals = sorted(
            [(ts, sl) for ts, s, sl, _ in score_timeline
             if s <= -_ALERT_THRESHOLD and sl is not None],
            key=lambda x: x[0],
        )

    orig_sl_pct = abs(entry_price - stop_loss) / entry_price if entry_price > 0 else 0.0

    result = _core_simulate_exit(
        bars=future_candles,          # PriceCandle duck-typed: timestamp/open/high/low/close
        direction=direction,
        entry_price=entry_price,
        sl=stop_loss,
        tp=take_profit,
        orig_sl_pct=orig_sl_pct,
        signal_ts=entry_ts,
        opp_list=opp_list,
        same_dir_signals=same_dir_signals,
        symbol=ticker,
    )

    exit_reason = result["exit_reason"]
    exit_price  = result["exit_price"] if result["exit_price"] is not None else entry_price
    pnl = _pnl(direction, entry_price, exit_price)
    return exit_reason, exit_price, pnl


def _pnl(direction: str, entry: float, exit_p: float) -> float:
    """Percent P&L (positive = profit)."""
    if entry <= 0:
        return 0.0
    if direction == "LONG":
        return (exit_p - entry) / entry * 100.0
    else:
        return (entry - exit_p) / entry * 100.0


# ---------------------------------------------------------------------------
# (Eltávolított helpers: _is_sl_hit, _is_tp_hit, _find_opposing_signal,
#  _apply_trailing_sl, _get_day_close, _is_trading_hours, _is_eod,
#  _trading_session_start — ezek a trade_simulator_core-ban vannak.)
# ---------------------------------------------------------------------------

def _trading_session_start(signal_ts: datetime, is_us: bool) -> datetime:
    """DEPRECATED — megtartva backward compat miatt (külső kód nem hívja)."""
    if is_us:
        open_hour, open_minute = 14, 30
    else:
        open_hour, open_minute = 8, 0

    prev_day = signal_ts - timedelta(days=1)
    while prev_day.weekday() >= 5:  # Sat=5, Sun=6
        prev_day -= timedelta(days=1)

    return prev_day.replace(hour=open_hour, minute=open_minute, second=0, microsecond=0)
