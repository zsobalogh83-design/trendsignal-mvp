"""
TrendSignal Self-Tuning Engine - Extended Signal Data Loader

Loads all data needed for full trade re-simulation in one pass:
  1. signal_calculations rows (indicators, scores, ATR, confidence, S/R)
  2. Optionally: archive_signals rows (csak CLOSED archive_simulated_trades-hez tartozók)
  3. price_data_alpaca: future 15m candles for each signal (for SL/TP hit detection)
     — megegyezik az archive_backtest_service bar forrásával → szinkron szimuláció
  4. signals table: all combined_score values per ticker (for opposing signal detection)

Design goals:
  - Single DB pass, everything in memory → zero DB I/O during optimizer evaluation
  - Estimated RAM: ~20-30 MB for 1097 signals × ~130 candles/day × 45 days (15m)
  - score_timeline used by simulate_trade() for opposing signal detection

trade_mode filter:
  "all"   → minden jelzés (BUY + SELL + HOLD, de HOLD kiszűrésre kerül a backtesterben)
  "long"  → csak BUY/STRONG_BUY/MODERATE_BUY decision-ű jelzések
  "short" → csak SELL/STRONG_SELL/MODERATE_SELL decision-ű jelzések

Version: 3.2 – MAX_ARCHIVE_SIGNALS 4000→50000 (no artificial cap on direction-filtered data)
Date: 2026-03-29
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"

# How many calendar days of price data to load after each signal timestamp.
# A trade rarely lasts more than 30 trading days; 45 days is a safe buffer.
PRICE_LOOKAHEAD_DAYS = 45

# Hány legutóbbi CLOSED archive jelet vonunk be max.
# 50 000: elég nagy ahhoz, hogy trade_mode-szűrés után se vágjuk le az adatot
# (jelenleg max ~6 500 BUY + ~5 000 SELL archive CLOSED signal létezik).
# A tényleges futásidőt a ténylegesen betöltött sorok száma határozza meg, nem ez a konstans.
MAX_ARCHIVE_SIGNALS = 50000


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PriceCandle:
    """One 15-minute OHLCV candle (price_data_alpaca forrásból)."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SignalSimRow:
    """
    Combined data for one signal_calculations row — everything needed for:
      1. Score replay (same as original SignalRow)
      2. SL/TP recalculation (atr, confidence, nearest_support/resistance)
      3. Trade simulation (future_candles after entry)

    future_candles is populated by load_all_sim_data(); it contains all 5m
    candles from the signal's calculated_at through PRICE_LOOKAHEAD_DAYS.
    """
    # --- Identifiers ---
    signal_id: int
    ticker: str
    calculated_at: str          # ISO timestamp string
    original_decision: str      # BUY / SELL / HOLD (stored in DB)

    # --- Score replay inputs (mirrors SignalRow) ---
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
    volatility: Optional[float]     # stored atr_pct (%)

    stored_sentiment_score: float
    stored_technical_score: float
    stored_risk_score: float
    stored_combined_score: float

    news_items: List[dict] = field(default_factory=list)
    stored_weight_sentiment: float = 0.50
    stored_weight_technical: float = 0.35
    stored_weight_risk: float = 0.15
    stored_weights: dict = field(default_factory=dict)
    key_signals: List[str] = field(default_factory=list)

    # --- SL/TP recalculation inputs ---
    atr: Optional[float] = None             # raw ATR value (price units)
    atr_pct: Optional[float] = None         # ATR as % of price
    confidence: float = 0.60               # overall_confidence
    sentiment_confidence: float = 0.50     # component-level sentiment confidence
    risk_reward_ratio: Optional[float] = None  # for rr_quality_score
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None

    # --- Trade simulation ---
    future_candles: List[PriceCandle] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Main loader — call once per optimizer run
# ---------------------------------------------------------------------------

def load_all_sim_data(
    db_path: Path = DATABASE_PATH,
    lookahead_days: int = PRICE_LOOKAHEAD_DAYS,
    include_archive: bool = False,
    trade_mode: str = "all",
    max_archive_signals: int = MAX_ARCHIVE_SIGNALS,
) -> Tuple[List[SignalSimRow], Dict[str, List[Tuple[datetime, float]]]]:
    """
    Load everything needed for full trade re-simulation.

    Parameters
    ----------
    include_archive : bool
        Ha True, az archive_signals CLOSED trade-eket is betölti (max max_archive_signals db).
    trade_mode : str
        "all"   → minden BUY+SELL jelzés
        "long"  → csak BUY irányú jelzések
        "short" → csak SELL irányú jelzések
    max_archive_signals : int
        Maximum betöltendő archive jel (a legutóbbiak; teljesítmény-limit).

    Returns
    -------
    rows : List[SignalSimRow]
        Signal rows chronological order, with future_candles populated.
    score_timeline : Dict[str, List[Tuple[datetime, float]]]
        {ticker: [(timestamp, combined_score), ...]} for opposing signal detection.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    rows = _load_signal_rows(conn)

    if include_archive:
        archive_rows = _load_archive_signal_rows(conn, max_archive_signals, trade_mode)
        rows = rows + archive_rows
        # Re-sort chronologically
        rows.sort(key=lambda r: r.calculated_at)

    candle_map = _load_price_data(conn, rows, lookahead_days)
    timeline   = _load_score_timeline(conn)

    conn.close()

    # Attach future candles
    for row in rows:
        row.future_candles = candle_map.get(row.ticker, {}).get(
            row.calculated_at, []
        )

    # trade_mode filter — a HOLD jelzések a backtesterben szűrődnek ki;
    # itt csak a direction-szintű szűrést végezzük el.
    if trade_mode == "long":
        rows = [r for r in rows if _is_buy_decision(r.original_decision)]
    elif trade_mode == "short":
        rows = [r for r in rows if _is_sell_decision(r.original_decision)]

    return rows, timeline


# ---------------------------------------------------------------------------
# Internal loaders
# ---------------------------------------------------------------------------

def _load_signal_rows(conn: sqlite3.Connection) -> List[SignalSimRow]:
    """Load signal_calculations with all fields needed for sim."""
    raw_rows = conn.execute("""
        SELECT
            sc.signal_id            AS signal_id,
            sc.ticker_symbol        AS ticker,
            sc.calculated_at,
            sc.decision             AS original_decision,

            -- Score replay inputs
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
            sc.technical_details,

            -- SL/TP recalculation inputs
            sc.atr,
            sc.atr_pct,
            -- overall_confidence: weighted average of three confidence columns
            -- mirrors signal_generator.py logic (equal weight fallback)
            CASE
                WHEN sc.sentiment_confidence IS NOT NULL
                 AND sc.technical_confidence IS NOT NULL
                 AND sc.risk_confidence IS NOT NULL
                THEN (sc.sentiment_confidence + sc.technical_confidence + sc.risk_confidence) / 3.0
                ELSE COALESCE(sc.technical_confidence, sc.sentiment_confidence, sc.risk_confidence, 0.60)
            END AS confidence,
            COALESCE(sc.sentiment_confidence, 0.50) AS sentiment_confidence,
            sc.risk_reward_ratio,
            sc.nearest_support,
            sc.nearest_resistance

        FROM signal_calculations sc
        WHERE sc.sentiment_score IS NOT NULL
          AND sc.technical_score IS NOT NULL
          AND sc.risk_score IS NOT NULL
          AND sc.combined_score IS NOT NULL
        ORDER BY sc.calculated_at ASC
    """).fetchall()

    result = []
    for r in raw_rows:
        # Parse JSON fields
        news_items = _parse_json_list(r["news_inputs"])
        stored_weights = {}
        key_signals = []

        if r["config_snapshot"]:
            try:
                snap = json.loads(r["config_snapshot"])
                stored_weights = snap.get("weights", {})
            except (json.JSONDecodeError, TypeError):
                pass

        if r["technical_details"]:
            try:
                td = json.loads(r["technical_details"])
                key_signals = td.get("key_signals", [])
            except (json.JSONDecodeError, TypeError):
                pass

        # Sentiment score scaling: stored as -1..+1 → -100..+100
        raw_sent = r["sentiment_score"]
        if raw_sent is not None and abs(float(raw_sent)) <= 1.0:
            stored_sent = float(raw_sent) * 100.0
        else:
            stored_sent = float(raw_sent) if raw_sent is not None else 0.0

        # overall_confidence: prefer confidence column; fallback to average of 3
        conf_val = _f(r["confidence"])
        if conf_val is None:
            # Reconstruct from three confidence columns if available
            # (older rows may not have the single combined column)
            conf_val = 0.60

        result.append(SignalSimRow(
            signal_id=r["signal_id"],
            ticker=r["ticker"],
            calculated_at=r["calculated_at"],
            original_decision=r["original_decision"] or "HOLD",
            # score replay
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
            stored_weight_sentiment=float(r["weight_sentiment"]) if r["weight_sentiment"] else 0.50,
            stored_weight_technical=float(r["weight_technical"]) if r["weight_technical"] else 0.35,
            stored_weight_risk=float(r["weight_risk"]) if r["weight_risk"] else 0.15,
            news_items=news_items,
            stored_weights=stored_weights,
            key_signals=key_signals,
            # SL/TP recalculation
            atr=_f(r["atr"]),
            atr_pct=_f(r["atr_pct"]),
            confidence=conf_val,
            sentiment_confidence=_f(r["sentiment_confidence"]) or 0.50,
            risk_reward_ratio=_f(r["risk_reward_ratio"]),
            nearest_support=_f(r["nearest_support"]),
            nearest_resistance=_f(r["nearest_resistance"]),
        ))

    return result


def _load_price_data(
    conn: sqlite3.Connection,
    rows: List[SignalSimRow],
    lookahead_days: int,
) -> Dict[str, Dict[str, List[PriceCandle]]]:
    """
    For each signal row, load all 15m candles from calculated_at onward
    up to lookahead_days later.

    Returns {ticker: {calculated_at: [PriceCandle, ...]}}
    Candles are sorted ascending by timestamp.

    Strategy: load ALL 15m price data for each ticker once, then slice
    per signal. This avoids N×SELECT queries.

    Forrás: price_data (interval='15m') — tartalmaz minden historikus és friss bar-t
    (a price_data_alpaca adatai bele lettek olvasztva a merge_price_data_alpaca.py által).
    """
    # Collect unique tickers
    tickers = list({r.ticker for r in rows})

    placeholders = ",".join("?" * len(tickers))
    raw = conn.execute("""
        SELECT ticker_symbol, timestamp, open, high, low, close, volume
        FROM price_data
        WHERE interval = '15m'
          AND ticker_symbol IN ({placeholders})
        ORDER BY ticker_symbol, timestamp ASC
    """.format(placeholders=placeholders), tickers).fetchall()

    # Build {ticker: [(timestamp_dt, candle), ...]}
    all_candles: Dict[str, List[PriceCandle]] = {}
    for row in raw:
        ticker = row["ticker_symbol"]
        ts = _parse_ts(row["timestamp"])
        if ts is None:
            continue
        candle = PriceCandle(
            timestamp=ts,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]) if row["volume"] else 0.0,
        )
        if ticker not in all_candles:
            all_candles[ticker] = []
        all_candles[ticker].append(candle)

    # For each signal row, slice the candles that fall after calculated_at
    # Use binary search (candles are sorted)
    result: Dict[str, Dict[str, List[PriceCandle]]] = {}

    for sig_row in rows:
        ticker = sig_row.ticker
        sig_ts = _parse_ts(sig_row.calculated_at)
        if sig_ts is None or ticker not in all_candles:
            continue

        end_ts = sig_ts + timedelta(days=lookahead_days)
        candles = all_candles[ticker]

        # Binary search for start index
        lo, hi = 0, len(candles)
        while lo < hi:
            mid = (lo + hi) // 2
            if candles[mid].timestamp <= sig_ts:
                lo = mid + 1
            else:
                hi = mid
        start_idx = lo

        # Collect candles within the lookahead window
        future = []
        for c in candles[start_idx:]:
            if c.timestamp > end_ts:
                break
            future.append(c)

        if ticker not in result:
            result[ticker] = {}
        result[ticker][sig_row.calculated_at] = future

    return result


def _load_score_timeline(
    conn: sqlite3.Connection,
) -> Dict[str, List[Tuple[datetime, float]]]:
    """
    Load all signals (with combined_score) per ticker, sorted chronologically.
    Used for opposing signal detection during trade simulation.

    Returns {ticker: [(created_at_dt, combined_score), ...]}
    """
    raw = conn.execute("""
        SELECT ticker_symbol, created_at, combined_score, stop_loss, take_profit
        FROM signals
        WHERE combined_score IS NOT NULL
        ORDER BY ticker_symbol, created_at ASC
    """).fetchall()

    timeline: Dict[str, List[Tuple[datetime, float, Optional[float], Optional[float]]]] = {}
    for r in raw:
        ticker = r["ticker_symbol"]
        ts = _parse_ts(r["created_at"])
        if ts is None:
            continue
        score = float(r["combined_score"])
        sl = _f(r["stop_loss"])
        tp = _f(r["take_profit"])
        if ticker not in timeline:
            timeline[ticker] = []
        timeline[ticker].append((ts, score, sl, tp))

    return timeline


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


def _parse_ts(s) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime (naive UTC)."""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s[:len(fmt) + 3], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        return None


def _parse_json_list(raw) -> List[dict]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _is_buy_decision(decision: str) -> bool:
    d = (decision or "").upper()
    return "BUY" in d


def _is_sell_decision(decision: str) -> bool:
    d = (decision or "").upper()
    return "SELL" in d


def _trade_mode_sql_filter(trade_mode: str) -> str:
    """SQL WHERE fragment a direction-szintű szűréshez (archive lekérdezésben)."""
    if trade_mode == "long":
        return "AND a.decision LIKE '%BUY%'"
    elif trade_mode == "short":
        return "AND a.decision LIKE '%SELL%'"
    return ""  # "all" → nincs extra szűrés


# ---------------------------------------------------------------------------
# Archive signal loader
# ---------------------------------------------------------------------------

def _load_archive_signal_rows(
    conn: sqlite3.Connection,
    max_signals: int = MAX_ARCHIVE_SIGNALS,
    trade_mode: str = "all",
) -> List[SignalSimRow]:
    """
    Load archive_signals that have a CLOSED archive_simulated_trade.

    Csak azokat a jelzéseket vesszük be, amelyekhez létezik CLOSED szimulált trade —
    ezzel garantáljuk, hogy van elegendő árfolyam-adat a szimulációhoz.
    A legutóbbi max_signals darabot töltjük be (teljesítmény-limit).

    Schema mapping (archive_signals → SignalSimRow):
      signal_timestamp → calculated_at
      close_price      → current_price
      macd_hist        → macd_histogram
      macd_signal      → macd_signal_val
      overall_confidence → confidence
      (adx, bb_middle  → None — ezek opcionálisak)
      (news_inputs     → [] — egyedi hírek nem elérhetők az archive-ban)
    """
    raw_rows = conn.execute(f"""
        SELECT
            a.id                  AS signal_id,
            a.ticker_symbol       AS ticker,
            a.signal_timestamp    AS calculated_at,
            a.decision            AS original_decision,

            a.rsi,
            a.macd,
            a.macd_signal         AS macd_signal_val,
            a.macd_hist           AS macd_histogram,
            a.sma_20,
            a.sma_50,
            a.sma_200,
            NULL                  AS adx,
            a.bb_upper,
            a.bb_lower,
            NULL                  AS bb_middle,
            a.stoch_k,
            a.stoch_d,
            a.close_price         AS current_price,
            a.atr_pct             AS volatility,

            a.sentiment_score,
            a.technical_score,
            a.risk_score,
            a.combined_score,

            a.atr,
            a.atr_pct,
            a.overall_confidence      AS confidence,
            COALESCE(a.sentiment_confidence, 0.50) AS sentiment_confidence,
            a.risk_reward_ratio,
            a.nearest_support,
            a.nearest_resistance,
            a.reasoning_json

        FROM archive_signals a
        INNER JOIN archive_simulated_trades t
            ON t.archive_signal_id = a.id
           AND t.status = 'CLOSED'
        WHERE a.sentiment_score IS NOT NULL
          AND a.technical_score IS NOT NULL
          AND a.risk_score      IS NOT NULL
          AND a.combined_score  IS NOT NULL
          AND a.decision NOT IN ('HOLD', 'NEUTRAL')
          {_trade_mode_sql_filter(trade_mode)}
        ORDER BY a.signal_timestamp DESC
        LIMIT {int(max_signals)}
    """).fetchall()

    result = []
    for r in raw_rows:
        # Stored weights kinyerése reasoning_json-ból
        stored_weight_sentiment = 0.50
        stored_weight_technical = 0.35
        stored_weight_risk      = 0.15
        if r["reasoning_json"]:
            try:
                rj = json.loads(r["reasoning_json"])
                comps = rj.get("components", {})
                stored_weight_sentiment = comps.get("sentiment", {}).get("weight", 0.50)
                stored_weight_technical = comps.get("technical", {}).get("weight", 0.35)
                stored_weight_risk      = comps.get("risk",      {}).get("weight", 0.15)
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

        # Sentiment score: archive-ban általában -100..+100 skálán tárolva
        raw_sent = r["sentiment_score"]
        if raw_sent is not None and abs(float(raw_sent)) <= 1.0:
            stored_sent = float(raw_sent) * 100.0
        else:
            stored_sent = float(raw_sent) if raw_sent is not None else 0.0

        conf_val = _f(r["confidence"]) or 0.60

        result.append(SignalSimRow(
            signal_id=r["signal_id"],
            ticker=r["ticker"],
            calculated_at=r["calculated_at"],
            original_decision=r["original_decision"] or "HOLD",
            rsi=_f(r["rsi"]),
            macd=_f(r["macd"]),
            macd_signal_val=_f(r["macd_signal_val"]),
            macd_histogram=_f(r["macd_histogram"]),
            sma_20=_f(r["sma_20"]),
            sma_50=_f(r["sma_50"]),
            sma_200=_f(r["sma_200"]),
            adx=None,
            bb_upper=_f(r["bb_upper"]),
            bb_lower=_f(r["bb_lower"]),
            bb_middle=None,
            stoch_k=_f(r["stoch_k"]),
            stoch_d=_f(r["stoch_d"]),
            current_price=_f(r["current_price"]),
            volatility=_f(r["volatility"]),
            stored_sentiment_score=stored_sent,
            stored_technical_score=float(r["technical_score"]),
            stored_risk_score=float(r["risk_score"]),
            stored_combined_score=float(r["combined_score"]),
            stored_weight_sentiment=stored_weight_sentiment,
            stored_weight_technical=stored_weight_technical,
            stored_weight_risk=stored_weight_risk,
            news_items=[],          # egyedi hírek nem elérhetők archive-ban
            stored_weights={},
            key_signals=[],
            atr=_f(r["atr"]),
            atr_pct=_f(r["atr_pct"]),
            confidence=conf_val,
            sentiment_confidence=_f(r["sentiment_confidence"]) or 0.50,
            risk_reward_ratio=_f(r["risk_reward_ratio"]),
            nearest_support=_f(r["nearest_support"]),
            nearest_resistance=_f(r["nearest_resistance"]),
        ))

    return result
