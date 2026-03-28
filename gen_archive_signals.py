"""
Archive Signal Generator
========================
Generates historical BUY/SELL/HOLD signals for US tickers on 15-minute candles
during US market hours, using historical Alpaca price data and archive news.

Results are stored in the `archive_signals` table (separate from live `signals`).
The scoring logic mirrors the live signal pipeline exactly.

Usage:
    python gen_archive_signals.py                        # all tickers
    python gen_archive_signals.py --ticker AAPL          # single ticker
    python gen_archive_signals.py --from-date 2025-01-01 # start from date
    python gen_archive_signals.py --dry-run              # no DB writes
    python gen_archive_signals.py --batch-size 1000      # larger batches
"""

import sys
import os
import io
import json
import argparse
import contextlib
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# ── Force UTF-8 on Windows ───────────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'src'))

import sqlite3
from src.config import get_config
from src.technical_analyzer import (
    calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
    calculate_bollinger_bands, calculate_atr, calculate_stochastic,
    detect_support_resistance,
)
from src.signal_generator import SignalGenerator, calculate_risk_score, parse_support_resistance


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(ROOT, 'trendsignal.db')

US_TICKERS = [
    (1,  'AAPL',  'Apple Inc.'),
    (2,  'MSFT',  'Microsoft Corporation'),
    (3,  'GOOGL', 'Alphabet Inc.'),
    (4,  'TSLA',  'Tesla Inc.'),
    (7,  'NVDA',  'NVIDIA Corporation'),
    (8,  'AMZN',  'Amazon.com Inc.'),
    (9,  'META',  'Meta Platforms Inc.'),
    (10, 'IBM',   'International Business Machines Corp.'),
]

# Minimum bars of 15m history needed before we can generate a signal
# (SMA-200 needs 200 bars; add a small buffer)
MIN_LOOKBACK_BARS = 210

# News sentiment time-decay (mirrors aggregate_sentiment_from_news)
DECAY_WEIGHTS = {'0-2h': 1.0, '2-6h': 0.85, '6-12h': 0.60, '12-24h': 0.35}

# LLM duration -> weight multiplier (mirrors signal_generator)
DURATION_WEIGHT = {'hours': 0.6, 'days': 1.0, 'weeks': 1.4, 'permanent': 1.8}


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: suppress noisy print() inside library functions
# ─────────────────────────────────────────────────────────────────────────────

@contextlib.contextmanager
def _quiet():
    """Suppress stdout temporarily (used to silence calculate_risk_score prints)."""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


# ─────────────────────────────────────────────────────────────────────────────
# TABLE / SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS archive_signals (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker_id            INTEGER,
    ticker_symbol        VARCHAR(10)  NOT NULL,
    signal_timestamp     DATETIME     NOT NULL,

    -- Decision
    decision             VARCHAR(20)  NOT NULL,
    strength             VARCHAR(20),

    -- Scores
    combined_score       FLOAT,
    base_combined_score  FLOAT,
    alignment_bonus      INTEGER DEFAULT 0,
    rr_correction        FLOAT   DEFAULT 0,
    sentiment_score      FLOAT,
    technical_score      FLOAT,
    risk_score           FLOAT,

    -- Confidence
    overall_confidence   FLOAT,
    sentiment_confidence FLOAT,
    technical_confidence FLOAT,
    risk_confidence      FLOAT,

    -- Entry / Exit levels
    entry_price          FLOAT,
    stop_loss            FLOAT,
    take_profit          FLOAT,
    risk_reward_ratio    FLOAT,

    -- Technical indicator snapshot at signal time
    close_price          FLOAT,
    rsi                  FLOAT,
    macd                 FLOAT,
    macd_signal          FLOAT,
    macd_hist            FLOAT,
    sma_20               FLOAT,
    sma_50               FLOAT,
    sma_200              FLOAT,
    atr                  FLOAT,
    atr_pct              FLOAT,
    bb_upper             FLOAT,
    bb_lower             FLOAT,
    stoch_k              FLOAT,
    stoch_d              FLOAT,

    -- Support / Resistance
    nearest_support      FLOAT,
    nearest_resistance   FLOAT,

    -- News
    news_count           INTEGER DEFAULT 0,

    -- Full reasoning blob
    reasoning_json       TEXT,

    -- Meta
    generated_at         DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_symbol, signal_timestamp)
)
'''

INSERT_SQL = '''
INSERT OR IGNORE INTO archive_signals (
    ticker_id, ticker_symbol, signal_timestamp,
    decision, strength,
    combined_score, base_combined_score, alignment_bonus, rr_correction,
    sentiment_score, technical_score, risk_score,
    overall_confidence, sentiment_confidence, technical_confidence, risk_confidence,
    entry_price, stop_loss, take_profit, risk_reward_ratio,
    close_price, rsi, macd, macd_signal, macd_hist,
    sma_20, sma_50, sma_200, atr, atr_pct,
    bb_upper, bb_lower, stoch_k, stoch_d,
    nearest_support, nearest_resistance,
    news_count, reasoning_json
) VALUES (
    :ticker_id, :ticker_symbol, :signal_timestamp,
    :decision, :strength,
    :combined_score, :base_combined_score, :alignment_bonus, :rr_correction,
    :sentiment_score, :technical_score, :risk_score,
    :overall_confidence, :sentiment_confidence, :technical_confidence, :risk_confidence,
    :entry_price, :stop_loss, :take_profit, :risk_reward_ratio,
    :close_price, :rsi, :macd, :macd_signal, :macd_hist,
    :sma_20, :sma_50, :sma_200, :atr, :atr_pct,
    :bb_upper, :bb_lower, :stoch_k, :stoch_d,
    :nearest_support, :nearest_resistance,
    :news_count, :reasoning_json
)
'''


def create_table(conn: sqlite3.Connection):
    conn.execute(CREATE_TABLE_SQL)
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_arch_sig_ticker_ts '
        'ON archive_signals(ticker_symbol, signal_timestamp)'
    )
    conn.commit()
    print('archive_signals table ready.')


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_15m(conn: sqlite3.Connection, ticker: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM price_data_alpaca "
        "WHERE ticker_symbol=? AND interval='15m' ORDER BY timestamp",
        conn, params=(ticker,)
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df


def load_1d(conn: sqlite3.Connection, ticker: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM price_data_alpaca "
        "WHERE ticker_symbol=? AND interval='1d' ORDER BY timestamp",
        conn, params=(ticker,)
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df


def load_news(conn: sqlite3.Connection, ticker: str) -> pd.DataFrame:
    """Load non-duplicate news items that have an active_score."""
    df = pd.read_sql_query(
        """SELECT published_at,
                  active_score,
                  av_relevance_score,
                  overall_sentiment_score AS sentiment_score,
                  sentiment_confidence,
                  llm_impact_duration,
                  is_duplicate
           FROM archive_news_items
           WHERE ticker_symbol=?
             AND is_duplicate = 0
             AND active_score IS NOT NULL
           ORDER BY published_at""",
        conn, params=(ticker,)
    )
    if df.empty:
        return df
    df['published_at']      = pd.to_datetime(df['published_at'], utc=True)
    df['av_relevance_score']  = df['av_relevance_score'].fillna(0.5)
    df['sentiment_confidence'] = df['sentiment_confidence'].fillna(0.5)
    df['llm_impact_duration']  = df['llm_impact_duration'].fillna('days')
    return df


def load_existing_timestamps(conn: sqlite3.Connection, ticker: str) -> set:
    cur = conn.execute(
        "SELECT signal_timestamp FROM archive_signals WHERE ticker_symbol=?", (ticker,)
    )
    return {row[0] for row in cur.fetchall()}


# ─────────────────────────────────────────────────────────────────────────────
# INDICATORS (vectorized — computed ONCE per ticker)
# ─────────────────────────────────────────────────────────────────────────────

def compute_indicator_series(df: pd.DataFrame) -> Dict[str, pd.Series]:
    close  = df['close']
    high   = df['high']
    low    = df['low']
    volume = df['volume']

    macd_line, macd_sig, macd_hist = calculate_macd(close, 12, 26, 9)
    bb_up, bb_mid, bb_lo = calculate_bollinger_bands(close)
    stoch_k, stoch_d = calculate_stochastic(high, low, close)

    return {
        'sma_20':      calculate_sma(close, 20),
        'sma_50':      calculate_sma(close, 50),
        'sma_200':     calculate_sma(close, 200),
        'macd':        macd_line,
        'macd_signal': macd_sig,
        'macd_hist':   macd_hist,
        'rsi':         calculate_rsi(close, 14),
        'bb_upper':    bb_up,
        'bb_middle':   bb_mid,
        'bb_lower':    bb_lo,
        'atr':         calculate_atr(high, low, close, 14),
        'stoch_k':     stoch_k,
        'stoch_d':     stoch_d,
        'volume_sma':  calculate_sma(volume, 20),
    }


def _f(val) -> Optional[float]:
    """Convert pandas scalar to float, or None if NaN/None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (f != f) else f   # NaN check without numpy
    except (TypeError, ValueError):
        return None


def indicators_at(series: Dict[str, pd.Series], df: pd.DataFrame, i: int) -> Dict:
    row = {k: _f(v.iloc[i]) for k, v in series.items()}
    row['close']  = _f(df['close'].iloc[i])
    row['volume'] = _f(df['volume'].iloc[i])
    return row


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL SCORE  (mirrors TechnicalAnalyzer exactly)
# ─────────────────────────────────────────────────────────────────────────────

def _trend_score(ind: Dict) -> float:
    score = 0.0; n = 0.0
    s20, s50, s200 = ind.get('sma_20'), ind.get('sma_50'), ind.get('sma_200')
    close = ind['close']

    if s20 and s50 and s200:
        if   s20 > s50 > s200: score += 100
        elif s20 < s50 < s200: score -= 100
        elif s20 > s50:         score += 50
        else:                   score -= 50
        n += 1

    macd, msig = ind.get('macd'), ind.get('macd_signal')
    if macd is not None and msig is not None:
        score += 100 if macd > msig else -100
        n += 1

    if s20:
        score += 50 if close > s20 else -50
        n += 1

    return score / n if n > 0 else 0.0


def _momentum_score(ind: Dict) -> float:
    score = 0.0; n = 0.0
    rsi = ind.get('rsi')
    if rsi is not None:
        if   rsi < 30: score += 100
        elif rsi > 70: score -= 100
        elif rsi > 50: score += 50
        else:          score -= 50
        n += 1

    sk, sd = ind.get('stoch_k'), ind.get('stoch_d')
    if sk is not None and sd is not None:
        score += 100 if sk > sd else -100
        n += 1

    return score / n if n > 0 else 0.0


def _volatility_score(ind: Dict) -> float:
    score = 0.0; n = 0.0
    bb_up, bb_mid, bb_lo = ind.get('bb_upper'), ind.get('bb_middle'), ind.get('bb_lower')
    close = ind['close']

    if bb_up and bb_lo:
        rng = bb_up - bb_lo
        if rng > 0:
            pos = (close - bb_lo) / rng
            if   pos > 0.8: score -= 50
            elif pos < 0.2: score += 50
            else:            score += 20
        n += 1

    atr = ind.get('atr')
    if atr and close:
        ap = (atr / close) * 100
        if   ap < 2.0: score += 50
        elif ap > 5.0: score -= 50
        n += 1

    return score / n if n > 0 else 0.0


def _volume_score(ind: Dict) -> float:
    vol, vsma = ind.get('volume'), ind.get('volume_sma')
    if vol and vsma and vsma > 0:
        r = vol / vsma
        if   r > 1.5: return 100
        elif r > 1.2: return 50
        elif r < 0.8: return -50
    return 0.0


def technical_score_and_confidence(ind: Dict) -> Tuple[float, float]:
    t = _trend_score(ind)
    m = _momentum_score(ind)
    v = _volatility_score(ind)
    u = _volume_score(ind)
    score = float(np.clip(t * 0.40 + m * 0.30 + v * 0.20 + u * 0.10, -100, 100))

    # Confidence: fraction of components that agree on direction
    scores_norm = [t/100, m/100, v/100, u/100]
    pos = sum(1 for s in scores_norm if s > 0)
    neg = sum(1 for s in scores_norm if s < 0)
    conf = max(pos, neg) / len(scores_norm)
    # Boost for clear SMA trend
    s20, s50 = ind.get('sma_20'), ind.get('sma_50')
    if s20 and s50 and s50 > 0 and abs(s20 - s50) / s50 > 0.05:
        conf = min(conf + 0.1, 1.0)

    return score, conf


# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT  (mirrors aggregate_sentiment_from_news)
# ─────────────────────────────────────────────────────────────────────────────

def sentiment_at(news_df: pd.DataFrame, ts: pd.Timestamp) -> Dict:
    """Compute sentiment from news items published in the 24 h before ts."""
    if news_df.empty:
        return {'weighted_avg': 0.0, 'confidence': 0.4, 'count': 0}

    ts_utc = ts.tz_localize('UTC') if ts.tzinfo is None else ts.tz_convert('UTC')
    window_start = ts_utc - pd.Timedelta(hours=24)

    w = news_df[
        (news_df['published_at'] > window_start) &
        (news_df['published_at'] <= ts_utc)
    ]

    if w.empty:
        return {'weighted_avg': 0.0, 'confidence': 0.4, 'count': 0}

    weighted_scores: List[float] = []
    weights_sum = 0.0
    confidences: List[float] = []

    for _, row in w.iterrows():
        age_h = (ts_utc - row['published_at']).total_seconds() / 3600
        if   age_h < 2:  decay = DECAY_WEIGHTS['0-2h']
        elif age_h < 6:  decay = DECAY_WEIGHTS['2-6h']
        elif age_h < 12: decay = DECAY_WEIGHTS['6-12h']
        else:            decay = DECAY_WEIGHTS['12-24h']

        dur   = DURATION_WEIGHT.get(str(row.get('llm_impact_duration') or 'days'), 1.0)
        rel   = float(row.get('av_relevance_score') or 0.5)
        score = float(row['active_score'])
        fw    = decay * rel * dur

        weighted_scores.append(score * fw)
        weights_sum += fw
        confidences.append(float(row.get('sentiment_confidence') or 0.5))

    if not weighted_scores or weights_sum == 0:
        return {'weighted_avg': 0.0, 'confidence': 0.4, 'count': 0}

    weighted_avg = sum(weighted_scores) / weights_sum
    n = len(w)
    if   n >= 5: vol = 1.0
    elif n >= 3: vol = 0.85
    elif n >= 2: vol = 0.70
    elif n >= 1: vol = 0.55
    else:        vol = 0.40

    fb_conf = sum(confidences) / len(confidences)
    confidence = min(fb_conf * vol, 0.90)

    return {
        'weighted_avg': float(np.clip(weighted_avg, -1.0, 1.0)),
        'confidence':   float(confidence),
        'count':        n,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT / RESISTANCE  (daily, from 1d data, cached per date)
# ─────────────────────────────────────────────────────────────────────────────

def sr_for_date(df_1d: pd.DataFrame, target_date: date, config) -> Optional[Dict]:
    """
    Compute swing S/R using 1d bars strictly BEFORE target_date (no lookahead).
    Returns None if insufficient data.
    """
    df_up = df_1d[df_1d.index.date < target_date]
    if len(df_up) < 30:
        return None

    # detect_support_resistance expects columns: Open, High, Low, Close, Volume
    df_sr = df_up.rename(columns={
        'open': 'Open', 'high': 'High', 'low': 'Low',
        'close': 'Close', 'volume': 'Volume'
    })

    try:
        with _quiet():
            return detect_support_resistance(
                df_sr,
                lookback_days=getattr(config, 'sr_dbscan_lookback', 180),
                proximity_pct=getattr(config, 'sr_dbscan_eps', 4.0) / 100.0,
                order=getattr(config, 'sr_dbscan_order', 7),
                min_samples=getattr(config, 'sr_dbscan_min_samples', 3),
            )
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE-BAR SIGNAL GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_bar_signal(
    ticker_id: int,
    ticker_symbol: str,
    ticker_name: str,
    ts: pd.Timestamp,
    ind: Dict,
    sent: Dict,
    sr_data: Optional[Dict],
    config,
    generator: SignalGenerator,
) -> Optional[Dict]:
    """
    Generate one signal row for a single 15m bar.
    Returns dict ready for DB insert, or None if data is insufficient.
    """
    close = ind.get('close')
    if not close or close <= 0:
        return None

    atr     = ind.get('atr') or close * 0.02
    atr_pct = (atr / close) * 100

    # ── Technical ─────────────────────────────────────────────────────────────
    tech_score, tech_conf = technical_score_and_confidence(ind)

    technical_data = {
        'current_price':      close,
        'atr':                atr,
        'atr_pct':            atr_pct,
        'score':              tech_score,
        'confidence':         tech_conf,
        'overall_confidence': tech_conf,
        'adx':                None,   # not computed (consistent with live pipeline)
        'rsi':                ind.get('rsi'),
        'sma_20':             ind.get('sma_20'),
        'sma_50':             ind.get('sma_50'),
        'sma_200':            ind.get('sma_200'),
    }

    # ── Risk ──────────────────────────────────────────────────────────────────
    with _quiet():
        risk_data = calculate_risk_score(technical_data, ticker_symbol, swing_sr=sr_data)

    risk_score  = risk_data.get('score', 0.0)
    risk_conf   = risk_data.get('confidence', 0.5)

    # ── Sentiment ─────────────────────────────────────────────────────────────
    # weighted_avg is [-1, 1]; multiply by 100 to get -100..+100 range
    sent_score = sent['weighted_avg'] * 100
    sent_conf  = sent['confidence']

    # ── Weighted combination (mirrors generate_signal exactly) ────────────────
    sw = config.SENTIMENT_WEIGHT
    tw = config.TECHNICAL_WEIGHT
    rw = config.RISK_WEIGHT

    sent_contrib  = sent_score  * sw
    tech_contrib  = tech_score  * tw
    risk_contrib  = (risk_score - 50) * rw
    base_combined = sent_contrib + tech_contrib + risk_contrib

    # Alignment bonus
    with _quiet():
        alignment_bonus = generator._calculate_alignment_bonus(
            sent_score, tech_score, risk_score
        )
    combined_after_alignment = base_combined + alignment_bonus

    # Preliminary decision (for level calculation)
    HOLD_ZONE = config.hold_zone_threshold
    if   combined_after_alignment >= HOLD_ZONE:  prelim = 'BUY'
    elif combined_after_alignment <= -HOLD_ZONE: prelim = 'SELL'
    else:                                         prelim = 'HOLD'

    # Entry / Exit levels
    with _quiet():
        levels = generator._calculate_levels(prelim, close, technical_data, risk_data)

    entry_price = stop_loss = take_profit = rr_ratio = None
    sl_method   = tp_method = None
    rr_correction = 0

    if levels[0] is not None:
        entry_price, stop_loss, take_profit, rr_ratio, sl_method, tp_method = levels

        # R:R correction (mirrors generate_signal)
        if prelim != 'HOLD' and rr_ratio is not None:
            direction = 1 if prelim == 'BUY' else -1
            if tp_method == 'rr_target':
                rr_correction = -3 * direction
            elif rr_ratio >= 3.0:
                rr_correction = 3 * direction
            elif rr_ratio >= 2.5:
                rr_correction = 2 * direction
            elif rr_ratio >= 2.0:
                rr_correction = 1 * direction

    combined_score = combined_after_alignment + rr_correction

    # If R:R correction pushed score into HOLD zone → force HOLD
    if prelim != 'HOLD' and abs(combined_score) < HOLD_ZONE:
        prelim        = 'HOLD'
        entry_price   = stop_loss = take_profit = rr_ratio = None
        rr_correction = 0
        combined_score = combined_after_alignment   # restore

    # Overall confidence
    overall_conf = sent_conf * sw + tech_conf * tw + risk_conf * rw

    # Final decision / strength
    # If R:R correction forced HOLD (prelim already overridden above), use HOLD directly
    # to avoid _determine_decision returning BUY/SELL again on the restored score
    if prelim == 'HOLD' and (entry_price is None):
        decision, strength = 'HOLD', 'NEUTRAL'
    else:
        with _quiet():
            decision, strength = generator._determine_decision(combined_score, overall_conf)

    # S/R values for storage
    nearest_support, nearest_resistance = parse_support_resistance(risk_data)

    # Reasoning blob
    reasoning = {
        'combined_score':      round(combined_score, 2),
        'base_combined_score': round(base_combined, 2),
        'alignment_bonus':     alignment_bonus,
        'rr_correction':       rr_correction,
        'components': {
            'sentiment': {
                'score': round(sent_score, 2), 'weight': sw,
                'contribution': round(sent_contrib, 2), 'confidence': round(sent_conf, 3),
            },
            'technical': {
                'score': round(tech_score, 2), 'weight': tw,
                'contribution': round(tech_contrib, 2), 'confidence': round(tech_conf, 3),
            },
            'risk': {
                'score': round(risk_score, 2), 'weight': rw,
                'contribution': round(risk_contrib, 2), 'confidence': round(risk_conf, 3),
            },
        },
        'levels_meta': {'sl_method': sl_method, 'tp_method': tp_method}
                       if sl_method else None,
    }

    return {
        'ticker_id':             ticker_id,
        'ticker_symbol':         ticker_symbol,
        'signal_timestamp':      ts.strftime('%Y-%m-%d %H:%M:%S'),
        'decision':              decision,
        'strength':              strength,
        'combined_score':        round(combined_score, 4),
        'base_combined_score':   round(base_combined, 4),
        'alignment_bonus':       alignment_bonus,
        'rr_correction':         rr_correction,
        'sentiment_score':       round(sent_score,  4),
        'technical_score':       round(tech_score,  4),
        'risk_score':            round(risk_score,  4),
        'overall_confidence':    round(overall_conf, 4),
        'sentiment_confidence':  round(sent_conf,   4),
        'technical_confidence':  round(tech_conf,   4),
        'risk_confidence':       round(risk_conf,   4),
        'entry_price':           entry_price,
        'stop_loss':             stop_loss,
        'take_profit':           take_profit,
        'risk_reward_ratio':     rr_ratio,
        'close_price':           close,
        'rsi':                   ind.get('rsi'),
        'macd':                  ind.get('macd'),
        'macd_signal':           ind.get('macd_signal'),
        'macd_hist':             ind.get('macd_hist'),
        'sma_20':                ind.get('sma_20'),
        'sma_50':                ind.get('sma_50'),
        'sma_200':               ind.get('sma_200'),
        'atr':                   atr if ind.get('atr') else None,
        'atr_pct':               round(atr_pct, 4),
        'bb_upper':              ind.get('bb_upper'),
        'bb_lower':              ind.get('bb_lower'),
        'stoch_k':               ind.get('stoch_k'),
        'stoch_d':               ind.get('stoch_d'),
        'nearest_support':       nearest_support,
        'nearest_resistance':    nearest_resistance,
        'news_count':            sent.get('count', 0),
        'reasoning_json':        json.dumps(reasoning, default=str),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PER-TICKER PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def process_ticker(
    conn:          sqlite3.Connection,
    ticker_id:     int,
    ticker_symbol: str,
    ticker_name:   str,
    config,
    generator:     SignalGenerator,
    from_date:     Optional[date],
    dry_run:       bool,
    batch_size:    int,
) -> Dict:
    stats = {
        'market_bars': 0, 'inserted': 0,
        'skipped_existing': 0, 'skipped_data': 0, 'errors': 0,
    }

    print(f"\n{'='*60}")
    print(f"  {ticker_symbol}  {ticker_name}")
    print(f"{'='*60}")

    df_15m  = load_15m(conn, ticker_symbol)
    df_1d   = load_1d(conn, ticker_symbol)
    news_df = load_news(conn, ticker_symbol)

    if df_15m.empty:
        print(f"  No 15m data — skipping.")
        return stats

    print(f"  15m bars : {len(df_15m):,}  ({df_15m.index[0].date()} – {df_15m.index[-1].date()})")
    print(f"  1d bars  : {len(df_1d):,}")
    print(f"  News     : {len(news_df):,} items")

    existing_ts = load_existing_timestamps(conn, ticker_symbol)
    print(f"  Existing : {len(existing_ts):,} signals already in DB")

    print(f"  Computing indicator series (vectorized)...")
    ind_series = compute_indicator_series(df_15m)

    sr_cache: Dict[date, Optional[Dict]] = {}

    def get_sr(d: date) -> Optional[Dict]:
        if d not in sr_cache:
            sr_cache[d] = sr_for_date(df_1d, d, config)
        return sr_cache[d]

    batch: List[Dict] = []
    skipped_warmup = 0
    total = len(df_15m)

    print(f"  Generating signals...")

    for i in range(total):
        ts      = df_15m.index[i]
        ts_date = ts.date()

        # ── Warmup: skip first MIN_LOOKBACK_BARS bars ──────────────────────
        if i < MIN_LOOKBACK_BARS:
            skipped_warmup += 1
            continue

        # ── from_date filter (still use full history for indicator lookback) ─
        if from_date and ts_date < from_date:
            continue

        # ── Skip weekends (belt-and-suspenders) ───────────────────────────
        if ts.dayofweek >= 5:
            continue

        stats['market_bars'] += 1
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')

        # ── Skip already generated ─────────────────────────────────────────
        if ts_str in existing_ts:
            stats['skipped_existing'] += 1
            continue

        # ── Indicator values at this bar ───────────────────────────────────
        ind = indicators_at(ind_series, df_15m, i)
        if not ind.get('close'):
            stats['skipped_data'] += 1
            continue

        # ── Daily S/R (cached) ─────────────────────────────────────────────
        sr = get_sr(ts_date)

        # ── Sentiment (24h rolling window) ─────────────────────────────────
        sent = sentiment_at(news_df, ts)

        # ── Generate signal ────────────────────────────────────────────────
        try:
            row = generate_bar_signal(
                ticker_id, ticker_symbol, ticker_name,
                ts, ind, sent, sr, config, generator,
            )
        except Exception as exc:
            stats['errors'] += 1
            if stats['errors'] <= 5:   # only print first 5 errors
                print(f"  ERROR at {ts_str}: {exc}")
            continue

        if row:
            batch.append(row)

        # ── Batch flush ────────────────────────────────────────────────────
        if len(batch) >= batch_size:
            if not dry_run:
                conn.executemany(INSERT_SQL, batch)
                conn.commit()
            stats['inserted'] += len(batch)
            pct = stats['market_bars'] / max(total - MIN_LOOKBACK_BARS, 1) * 100
            print(f"  {stats['inserted']:>8,} inserted  ({pct:.1f}%  bar {i+1}/{total})")
            batch = []

    # Final batch
    if batch:
        if not dry_run:
            conn.executemany(INSERT_SQL, batch)
            conn.commit()
        stats['inserted'] += len(batch)

    print(f"\n  {ticker_symbol} done:")
    print(f"    Warmup skipped  : {skipped_warmup:,}")
    print(f"    Market bars     : {stats['market_bars']:,}")
    print(f"    Already in DB   : {stats['skipped_existing']:,}")
    print(f"    Inserted        : {stats['inserted']:,}")
    print(f"    Errors          : {stats['errors']}")
    if dry_run:
        print(f"    (DRY RUN — nothing written)")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Generate archive signals from historical Alpaca 15m data'
    )
    parser.add_argument('--ticker',     type=str,  default=None,
                        help='Process only this ticker (e.g. AAPL)')
    parser.add_argument('--from-date',  type=str,  default=None,
                        help='Start from this date YYYY-MM-DD (full history still used for indicators)')
    parser.add_argument('--dry-run',    action='store_true',
                        help='Compute signals but do not write to DB')
    parser.add_argument('--batch-size', type=int,  default=500,
                        help='DB insert batch size (default 500)')
    args = parser.parse_args()

    from_date: Optional[date] = None
    if args.from_date:
        from_date = datetime.strptime(args.from_date, '%Y-%m-%d').date()

    config    = get_config()
    generator = SignalGenerator(config)

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')

    if not args.dry_run:
        create_table(conn)
    else:
        print('[DRY RUN] — no DB writes')
        create_table(conn)   # still create table so queries work

    tickers = US_TICKERS
    if args.ticker:
        tickers = [t for t in US_TICKERS if t[1] == args.ticker.upper()]
        if not tickers:
            print(f"Ticker {args.ticker.upper()} not found in US_TICKERS list.")
            conn.close()
            return

    total_stats = {'market_bars': 0, 'inserted': 0, 'errors': 0}

    for tid, sym, name in tickers:
        s = process_ticker(
            conn, tid, sym, name,
            config, generator,
            from_date=from_date,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
        total_stats['market_bars'] += s['market_bars']
        total_stats['inserted']    += s['inserted']
        total_stats['errors']      += s['errors']

    conn.close()

    print(f"\n{'='*60}")
    print(f"  ALL DONE")
    print(f"  Market bars processed : {total_stats['market_bars']:,}")
    print(f"  Signals inserted      : {total_stats['inserted']:,}")
    print(f"  Errors                : {total_stats['errors']}")
    if args.dry_run:
        print(f"  (DRY RUN — nothing written)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
