"""
TrendSignal MVP - Configuration Module
Centralized configuration for all components

Version: 1.1 - Dynamic Config Support
Date: 2024-12-28
"""

from typing import Dict, Any
from dataclasses import dataclass
import os
import json
from pathlib import Path


# ==========================================
# API KEYS (Environment Variables)
# ==========================================

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY", "")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")  # GNews API (real-time, no delay)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")  # Finnhub API (60 req/min)

# For development/testing (replace with your keys)
if not NEWSAPI_KEY:
    NEWSAPI_KEY = "c042824059404c8e9da37ef7cd4088b6"
if not ALPHAVANTAGE_KEY:
    ALPHAVANTAGE_KEY = "Q3R3ZCIBFDJI8BU9"
if not GNEWS_API_KEY:
    GNEWS_API_KEY = "422e63bafec92ab1e705b47455a16ce5"
if not FINNHUB_API_KEY:
    FINNHUB_API_KEY = "d60j2mpr01qto1rdbjmgd60j2mpr01qto1rdbjn0"  # Finnhub free tier


# ==========================================
# SENTIMENT ANALYSIS CONFIGURATION
# ==========================================

# Toggle between FinBERT (real) and Mock (keyword-based)
USE_FINBERT = True  # Set False to use mock keyword-based sentiment
USE_MULTILINGUAL = True  # Use multilingual model for non-English

# FinBERT device
FINBERT_DEVICE = None  # None = auto-detect (cuda if available, else cpu)


# ==========================================
# SENTIMENT DECAY MODEL (✅ 24H WINDOW)
# ==========================================

DECAY_WEIGHTS = {
    '0-2h': 1.00,    # Fresh news → full weight
    '2-6h': 0.85,    # Still very relevant, strong momentum
    '6-12h': 0.60,   # Intraday news, market reacting
    '12-24h': 0.35,  # 🆕 Overnight news (critical for day trading!)
}


# ==========================================
# COMPONENT WEIGHTS (FINAL)
# ==========================================

SENTIMENT_WEIGHT = 0.70  # 70% - Primary driver
TECHNICAL_WEIGHT = 0.20  # 20% - Confirmation
RISK_WEIGHT = 0.10       # 10% - Risk management


# ==========================================
# DECISION THRESHOLDS
# ==========================================

# Strong signals
STRONG_BUY_SCORE = 65
STRONG_BUY_CONFIDENCE = 0.75

STRONG_SELL_SCORE = -65
STRONG_SELL_CONFIDENCE = 0.75

# Moderate signals
MODERATE_BUY_SCORE = 50
MODERATE_BUY_CONFIDENCE = 0.65

MODERATE_SELL_SCORE = -50
MODERATE_SELL_CONFIDENCE = 0.65


# ==========================================
# TECHNICAL INDICATOR PARAMETERS
# ==========================================

# RSI (Relative Strength Index)
RSI_PERIOD = 14
RSI_TIMEFRAME = "5m"
RSI_LOOKBACK = "2d"

# SMA Short
SMA_SHORT_PERIOD = 20
SMA_SHORT_TIMEFRAME = "5m"
SMA_SHORT_LOOKBACK = "2d"

# SMA Medium
SMA_MEDIUM_PERIOD = 50
SMA_MEDIUM_TIMEFRAME = "1h"
SMA_MEDIUM_LOOKBACK = "30d"

# SMA Long
SMA_LONG_PERIOD = 200
SMA_LONG_TIMEFRAME = "1d"
SMA_LONG_LOOKBACK = "180d"

# MACD (Moving Average Convergence Divergence)
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
MACD_TIMEFRAME = "15m"
MACD_LOOKBACK = "3d"

# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2.0
BB_TIMEFRAME = "1h"
BB_LOOKBACK = "7d"

# ATR (Average True Range)
ATR_PERIOD = 14
ATR_TIMEFRAME = "1d"
ATR_LOOKBACK = "180d"

# Stochastic Oscillator
STOCH_PERIOD = 14
STOCH_TIMEFRAME = "15m"
STOCH_LOOKBACK = "3d"

# ADX (Average Directional Index)
ADX_PERIOD = 14
ADX_TIMEFRAME = "1h"
ADX_LOOKBACK = "30d"


# ==========================================
# TECHNICAL COMPONENT WEIGHTS (PERCENTAGE-BASED)
# ==========================================
# Each indicator produces a normalized score (-100 to +100)
# These weights determine how much each contributes to final technical score
# MUST SUM TO 1.0 (100%)

TECH_SMA_WEIGHT = 0.30          # 30% - Trend (SMA20/50/200, Golden/Death Cross)
TECH_RSI_WEIGHT = 0.25          # 25% - Momentum (RSI zones)
TECH_MACD_WEIGHT = 0.20         # 20% - Momentum (MACD histogram/crossover)
TECH_BOLLINGER_WEIGHT = 0.15    # 15% - Volatility (BB position)
TECH_STOCHASTIC_WEIGHT = 0.05   # 5% - Momentum (Stochastic oscillator)
TECH_VOLUME_WEIGHT = 0.05       # 5% - Confirmation (Volume ratio)

# Deprecated - Legacy detailed weights (kept for backward compatibility)
# These are now used WITHIN each component's internal scoring
TECH_SMA20_BULLISH = 25   # Price > SMA20
TECH_SMA20_BEARISH = 15   # Price < SMA20
TECH_SMA50_BULLISH = 20   # Price > SMA50
TECH_SMA50_BEARISH = 10   # Price < SMA50
TECH_GOLDEN_CROSS = 15    # SMA20 > SMA50
TECH_DEATH_CROSS = 15     # SMA20 < SMA50

TECH_RSI_NEUTRAL = 20     # 45 < RSI < 55
TECH_RSI_BULLISH = 30     # 55 <= RSI < 70
TECH_RSI_WEAK_BULLISH = 10  # 30 < RSI <= 45
TECH_RSI_OVERBOUGHT = 20  # RSI >= 70
TECH_RSI_OVERSOLD = 15    # RSI <= 30

# NEW: Additional indicators (CCI, ADX)
TECH_CCI_WEIGHT = 0.00    # 0% - Optional (can enable if needed)
TECH_ADX_WEIGHT = 0.00    # 0% - Already in risk component


# ==========================================
# RISK MANAGEMENT
# ==========================================

# Risk Component Weights
RISK_VOLATILITY_WEIGHT = 0.40      # 40% - ATR-based volatility risk
RISK_PROXIMITY_WEIGHT = 0.35       # 35% - S/R proximity risk  
RISK_TREND_STRENGTH_WEIGHT = 0.25  # 25% - ADX trend strength risk

# Stop-loss calculation
STOP_LOSS_SR_BUFFER = 0.5          # S/R buffer multiplier (0.5×ATR below support)
STOP_LOSS_ATR_MULTIPLIER = 2.0     # ATR-based stop multiplier (2×ATR)
MIN_STOP_LOSS_PCT = 0.02           # 2% (deprecated - kept for compatibility)
MAX_STOP_LOSS_PCT = 0.05           # 5% (deprecated - kept for compatibility)

# Take-profit calculation
TAKE_PROFIT_ATR_MULTIPLIER = 3.0   # ATR-based target multiplier (3×ATR, 1:1.5 R:R)
RISK_REWARD_RATIO = 2.0            # Target R:R = 1:2 (deprecated - kept for compatibility)

# S/R Distance Thresholds (for using S/R vs ATR fallback)
SR_SUPPORT_MAX_DISTANCE_PCT = 5.0  # Max 5% distance to use support for stop-loss
SR_RESISTANCE_MAX_DISTANCE_PCT = 8.0  # Max 8% distance to use resistance for take-profit

# S/R DBSCAN Detection Parameters
SR_DBSCAN_EPS = 4.0          # Clustering proximity threshold (4%)
SR_DBSCAN_MIN_SAMPLES = 3    # Minimum pivots per cluster
SR_DBSCAN_ORDER = 7          # Pivot detection window (7 bars each side)
SR_DBSCAN_LOOKBACK = 180     # Historical lookback period (180 days = 6 months)


# ==========================================
# NEWS COLLECTION
# ==========================================

NEWS_LOOKBACK_HOURS = 24  # Only collect last 24h
NEWS_RELEVANCE_THRESHOLD = 0.5  # Minimum relevance score
NEWS_MAX_AGE_HOURS = 24  # Maximum age for sentiment calculation


# ==========================================
# 🆕 SCHEDULER CONFIGURATION (Trading Hours)
# ==========================================

# Signal refresh interval (minutes)
SIGNAL_REFRESH_INTERVAL = 15  # Run every 15 minutes during market hours

# BÉT (Budapest Stock Exchange) - CET/CEST
BET_MARKET_OPEN = "09:00"      # 9:00 AM CET/CEST
BET_MARKET_CLOSE = "17:00"     # 5:00 PM CET/CEST
BET_TIMEZONE = "Europe/Budapest"
BET_TICKERS = ["MOL.BD", "OTP.BD"]

# US Markets (NYSE/NASDAQ) - ET
US_MARKET_OPEN = "09:30"       # 9:30 AM ET
US_MARKET_CLOSE = "16:00"      # 4:00 PM ET (market close)
US_TIMEZONE = "America/New_York"
US_TICKERS = ["AAPL", "TSLA", "MSFT", "NVDA"]

# Combined ticker list for batch processing
ALL_TICKERS = [
    {'symbol': 'MOL.BD', 'name': 'MOL Hungarian Oil and Gas', 'market': 'BET'},
    {'symbol': 'OTP.BD', 'name': 'OTP Bank', 'market': 'BET'},
    {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market': 'US'},
    {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'market': 'US'},
    {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'market': 'US'},
    {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'market': 'US'},
]


# ==========================================
# PRICE DATA
# ==========================================

PRICE_INTERVAL_INTRADAY = "5m"  # 5-minute candles for day trading
PRICE_INTERVAL_DAILY = "1d"     # Daily candles for context

INTRADAY_LOOKBACK_DAYS = 5   # 5 days of 5m data
DAILY_LOOKBACK_DAYS = 180    # 6 months for SMA200


# ==========================================
# CONFIDENCE CALCULATION WEIGHTS
# ==========================================

CONFIDENCE_WEIGHTS = {
    'news_volume': 0.30,      # More news = higher confidence
    'sentiment_consistency': 0.25,  # Aligned sentiment = higher
    'technical_alignment': 0.25,    # Tech confirms = higher
    'source_credibility': 0.20,     # Trusted sources = higher
}


# ==========================================
# PERZISZTENCIA - Config fájl kezelés
# ==========================================

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

def save_config_to_file(config_instance):
    """Save current configuration to JSON file for persistence"""
    try:
        config_dict = {
            # Signal weights
            "SENTIMENT_WEIGHT": config_instance.sentiment_weight,
            "TECHNICAL_WEIGHT": config_instance.technical_weight,
            "RISK_WEIGHT": config_instance.risk_weight,
            # Thresholds
            "STRONG_BUY_SCORE": config_instance.strong_buy_score,
            "STRONG_BUY_CONFIDENCE": config_instance.strong_buy_confidence,
            "MODERATE_BUY_SCORE": config_instance.moderate_buy_score,
            "MODERATE_BUY_CONFIDENCE": config_instance.moderate_buy_confidence,
            "STRONG_SELL_SCORE": config_instance.strong_sell_score,
            "STRONG_SELL_CONFIDENCE": config_instance.strong_sell_confidence,
            "MODERATE_SELL_SCORE": config_instance.moderate_sell_score,
            "MODERATE_SELL_CONFIDENCE": config_instance.moderate_sell_confidence,
            # Technical component weights
            "TECH_SMA20_BULLISH": config_instance.tech_sma20_bullish,
            "TECH_SMA20_BEARISH": config_instance.tech_sma20_bearish,
            "TECH_SMA50_BULLISH": config_instance.tech_sma50_bullish,
            "TECH_SMA50_BEARISH": config_instance.tech_sma50_bearish,
            "TECH_GOLDEN_CROSS": config_instance.tech_golden_cross,
            "TECH_DEATH_CROSS": config_instance.tech_death_cross,
            "TECH_RSI_NEUTRAL": config_instance.tech_rsi_neutral,
            "TECH_RSI_BULLISH": config_instance.tech_rsi_bullish,
            "TECH_RSI_WEAK_BULLISH": config_instance.tech_rsi_weak_bullish,
            "TECH_RSI_OVERBOUGHT": config_instance.tech_rsi_overbought,
            "TECH_RSI_OVERSOLD": config_instance.tech_rsi_oversold,
            # NEW: Additional indicator weights
            "TECH_MACD_WEIGHT": config_instance.tech_macd_weight,
            "TECH_BOLLINGER_WEIGHT": config_instance.tech_bollinger_weight,
            "TECH_STOCHASTIC_WEIGHT": config_instance.tech_stochastic_weight,
            "TECH_CCI_WEIGHT": config_instance.tech_cci_weight,
            "TECH_VOLUME_WEIGHT": config_instance.tech_volume_weight,
            "TECH_ADX_WEIGHT": config_instance.tech_adx_weight,
            # Decay weights
            "DECAY_WEIGHTS": config_instance.decay_weights,
            # Technical indicator periods
            "RSI_PERIOD": config_instance.rsi_period,
            "SMA_SHORT_PERIOD": config_instance.sma_short_period,
            "SMA_MEDIUM_PERIOD": config_instance.sma_medium_period,
            "SMA_LONG_PERIOD": config_instance.sma_long_period,
            "MACD_FAST": config_instance.macd_fast,
            "MACD_SLOW": config_instance.macd_slow,
            "MACD_SIGNAL": config_instance.macd_signal,
            "BB_PERIOD": config_instance.bb_period,
            "BB_STD_DEV": config_instance.bb_std_dev,
            "ATR_PERIOD": config_instance.atr_period,
            "STOCH_PERIOD": config_instance.stoch_period,
            "ADX_PERIOD": config_instance.adx_period,
            # Technical indicator timeframes
            "RSI_TIMEFRAME": config_instance.rsi_timeframe,
            "SMA_SHORT_TIMEFRAME": config_instance.sma_short_timeframe,
            "SMA_MEDIUM_TIMEFRAME": config_instance.sma_medium_timeframe,
            "SMA_LONG_TIMEFRAME": config_instance.sma_long_timeframe,
            "MACD_TIMEFRAME": config_instance.macd_timeframe,
            "BB_TIMEFRAME": config_instance.bb_timeframe,
            "ATR_TIMEFRAME": config_instance.atr_timeframe,
            "STOCH_TIMEFRAME": config_instance.stoch_timeframe,
            "ADX_TIMEFRAME": config_instance.adx_timeframe,
            # Technical indicator lookbacks
            "RSI_LOOKBACK": config_instance.rsi_lookback,
            "SMA_SHORT_LOOKBACK": config_instance.sma_short_lookback,
            "SMA_MEDIUM_LOOKBACK": config_instance.sma_medium_lookback,
            "SMA_LONG_LOOKBACK": config_instance.sma_long_lookback,
            "MACD_LOOKBACK": config_instance.macd_lookback,
            "BB_LOOKBACK": config_instance.bb_lookback,
            "ATR_LOOKBACK": config_instance.atr_lookback,
            "STOCH_LOOKBACK": config_instance.stoch_lookback,
            "ADX_LOOKBACK": config_instance.adx_lookback,
            # Risk management parameters
            "RISK_VOLATILITY_WEIGHT": config_instance.risk_volatility_weight,
            "RISK_PROXIMITY_WEIGHT": config_instance.risk_proximity_weight,
            "RISK_TREND_STRENGTH_WEIGHT": config_instance.risk_trend_strength_weight,
            "STOP_LOSS_SR_BUFFER": config_instance.stop_loss_sr_buffer,
            "STOP_LOSS_ATR_MULTIPLIER": config_instance.stop_loss_atr_mult,
            "TAKE_PROFIT_ATR_MULTIPLIER": config_instance.take_profit_atr_mult,
            "SR_SUPPORT_MAX_DISTANCE_PCT": config_instance.sr_support_max_distance_pct,
            "SR_RESISTANCE_MAX_DISTANCE_PCT": config_instance.sr_resistance_max_distance_pct,
            "SR_DBSCAN_EPS": config_instance.sr_dbscan_eps,
            "SR_DBSCAN_MIN_SAMPLES": config_instance.sr_dbscan_min_samples,
            "SR_DBSCAN_ORDER": config_instance.sr_dbscan_order,
            "SR_DBSCAN_LOOKBACK": config_instance.sr_dbscan_lookback,
        }
        
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2)
        
        print(f"✅ Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def load_config_from_file():
    """Load configuration from JSON file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                print(f"✅ Configuration loaded from {CONFIG_FILE}")
                return config
        except Exception as e:
            print(f"⚠️ Error loading config: {e}, using defaults")
    else:
        print(f"Config file not found at {CONFIG_FILE}, using defaults")
    return None

def update_config_values(config_instance, updates: dict):
    """Update configuration values and save to file"""
    
    # Mapping from JSON keys to dataclass attribute names
    key_mapping = {
        "STOP_LOSS_ATR_MULTIPLIER": "stop_loss_atr_mult",
        "TAKE_PROFIT_ATR_MULTIPLIER": "take_profit_atr_mult",
        "SR_SUPPORT_MAX_DISTANCE_PCT": "sr_support_max_distance_pct",
        "SR_RESISTANCE_MAX_DISTANCE_PCT": "sr_resistance_max_distance_pct",
    }
    
    for key, value in updates.items():
        # Use mapping if available, otherwise use lowercase
        attr_name = key_mapping.get(key, key.lower())
        
        if hasattr(config_instance, attr_name):
            setattr(config_instance, attr_name, value)
            print(f"  ✓ Updated {key} = {value}")
        else:
            print(f"  ⚠️ Attribute not found: {attr_name} (from key: {key})")
    
    save_config_to_file(config_instance)
    print(f"✅ Configuration updated with {len(updates)} changes")
    return config_instance


# ==========================================
# CONFIGURATION DATACLASS
# ==========================================

@dataclass
class TrendSignalConfig:
    """Complete configuration for TrendSignal MVP"""
    
    # API Keys
    newsapi_key: str = NEWSAPI_KEY
    alphavantage_key: str = ALPHAVANTAGE_KEY
    gnews_api_key: str = GNEWS_API_KEY  # GNews API (real-time news, no 24h delay)
    finnhub_api_key: str = FINNHUB_API_KEY  # Finnhub API (60 req/min)
    
    # Decay model
    decay_weights: Dict[str, float] = None
    
    # Component weights
    sentiment_weight: float = SENTIMENT_WEIGHT
    technical_weight: float = TECHNICAL_WEIGHT
    risk_weight: float = RISK_WEIGHT
    
    # Decision thresholds
    strong_buy_score: int = STRONG_BUY_SCORE
    strong_buy_confidence: float = STRONG_BUY_CONFIDENCE
    moderate_buy_score: int = MODERATE_BUY_SCORE
    moderate_buy_confidence: float = MODERATE_BUY_CONFIDENCE
    
    strong_sell_score: int = STRONG_SELL_SCORE
    strong_sell_confidence: float = STRONG_SELL_CONFIDENCE
    moderate_sell_score: int = MODERATE_SELL_SCORE
    moderate_sell_confidence: float = MODERATE_SELL_CONFIDENCE
    
    # Technical parameters - Periods
    rsi_period: int = RSI_PERIOD
    sma_short_period: int = SMA_SHORT_PERIOD
    sma_medium_period: int = SMA_MEDIUM_PERIOD
    sma_long_period: int = SMA_LONG_PERIOD
    macd_fast: int = MACD_FAST
    macd_slow: int = MACD_SLOW
    macd_signal: int = MACD_SIGNAL
    bb_period: int = BB_PERIOD
    bb_std_dev: float = BB_STD_DEV
    atr_period: int = ATR_PERIOD
    stoch_period: int = STOCH_PERIOD
    adx_period: int = ADX_PERIOD
    
    # Technical parameters - Timeframes
    rsi_timeframe: str = RSI_TIMEFRAME
    sma_short_timeframe: str = SMA_SHORT_TIMEFRAME
    sma_medium_timeframe: str = SMA_MEDIUM_TIMEFRAME
    sma_long_timeframe: str = SMA_LONG_TIMEFRAME
    macd_timeframe: str = MACD_TIMEFRAME
    bb_timeframe: str = BB_TIMEFRAME
    atr_timeframe: str = ATR_TIMEFRAME
    stoch_timeframe: str = STOCH_TIMEFRAME
    adx_timeframe: str = ADX_TIMEFRAME
    
    # Technical parameters - Lookbacks
    rsi_lookback: str = RSI_LOOKBACK
    sma_short_lookback: str = SMA_SHORT_LOOKBACK
    sma_medium_lookback: str = SMA_MEDIUM_LOOKBACK
    sma_long_lookback: str = SMA_LONG_LOOKBACK
    macd_lookback: str = MACD_LOOKBACK
    bb_lookback: str = BB_LOOKBACK
    atr_lookback: str = ATR_LOOKBACK
    stoch_lookback: str = STOCH_LOOKBACK
    adx_lookback: str = ADX_LOOKBACK
    
    # Legacy compatibility
    sma_periods: Dict[str, int] = None
    macd_params: Dict[str, int] = None
    
    # Technical component weights (percentage-based, sum to 1.0)
    tech_sma_weight: float = TECH_SMA_WEIGHT
    tech_rsi_weight: float = TECH_RSI_WEIGHT
    tech_macd_weight: float = TECH_MACD_WEIGHT
    tech_bollinger_weight: float = TECH_BOLLINGER_WEIGHT
    tech_stochastic_weight: float = TECH_STOCHASTIC_WEIGHT
    tech_volume_weight: float = TECH_VOLUME_WEIGHT
    tech_cci_weight: float = TECH_CCI_WEIGHT
    tech_adx_weight: float = TECH_ADX_WEIGHT
    
    # Legacy: Detailed weights (used within each component's internal scoring)
    tech_sma20_bullish: int = TECH_SMA20_BULLISH
    tech_sma20_bearish: int = TECH_SMA20_BEARISH
    tech_sma50_bullish: int = TECH_SMA50_BULLISH
    tech_sma50_bearish: int = TECH_SMA50_BEARISH
    tech_golden_cross: int = TECH_GOLDEN_CROSS
    tech_death_cross: int = TECH_DEATH_CROSS
    tech_rsi_neutral: int = TECH_RSI_NEUTRAL
    tech_rsi_bullish: int = TECH_RSI_BULLISH
    tech_rsi_weak_bullish: int = TECH_RSI_WEAK_BULLISH
    tech_rsi_overbought: int = TECH_RSI_OVERBOUGHT
    tech_rsi_oversold: int = TECH_RSI_OVERSOLD
    
    # Risk management parameters
    risk_volatility_weight: float = RISK_VOLATILITY_WEIGHT
    risk_proximity_weight: float = RISK_PROXIMITY_WEIGHT
    risk_trend_strength_weight: float = RISK_TREND_STRENGTH_WEIGHT
    stop_loss_sr_buffer: float = STOP_LOSS_SR_BUFFER
    stop_loss_atr_mult: float = STOP_LOSS_ATR_MULTIPLIER
    take_profit_atr_mult: float = TAKE_PROFIT_ATR_MULTIPLIER
    sr_support_max_distance_pct: float = SR_SUPPORT_MAX_DISTANCE_PCT
    sr_resistance_max_distance_pct: float = SR_RESISTANCE_MAX_DISTANCE_PCT
    sr_dbscan_eps: float = SR_DBSCAN_EPS
    sr_dbscan_min_samples: int = SR_DBSCAN_MIN_SAMPLES
    sr_dbscan_order: int = SR_DBSCAN_ORDER
    sr_dbscan_lookback: int = SR_DBSCAN_LOOKBACK
    
    # 🆕 Scheduler settings
    signal_refresh_interval: int = SIGNAL_REFRESH_INTERVAL
    bet_market_open: str = BET_MARKET_OPEN
    bet_market_close: str = BET_MARKET_CLOSE
    bet_timezone: str = BET_TIMEZONE
    bet_tickers: list = None
    us_market_open: str = US_MARKET_OPEN
    us_market_close: str = US_MARKET_CLOSE
    us_timezone: str = US_TIMEZONE
    us_tickers: list = None
    all_tickers: list = None
    
    # Legacy compatibility
    risk_reward_ratio: float = RISK_REWARD_RATIO
    
    def __post_init__(self):
        """Initialize nested dictionaries and load from file if exists"""
        # Load from file if exists - CRITICAL FIX!
        saved_config = load_config_from_file()
        if saved_config:
            self.sentiment_weight = saved_config.get("SENTIMENT_WEIGHT", SENTIMENT_WEIGHT)
            self.technical_weight = saved_config.get("TECHNICAL_WEIGHT", TECHNICAL_WEIGHT)
            self.risk_weight = saved_config.get("RISK_WEIGHT", RISK_WEIGHT)
            self.strong_buy_score = saved_config.get("STRONG_BUY_SCORE", STRONG_BUY_SCORE)
            self.strong_buy_confidence = saved_config.get("STRONG_BUY_CONFIDENCE", STRONG_BUY_CONFIDENCE)
            self.moderate_buy_score = saved_config.get("MODERATE_BUY_SCORE", MODERATE_BUY_SCORE)
            self.moderate_buy_confidence = saved_config.get("MODERATE_BUY_CONFIDENCE", MODERATE_BUY_CONFIDENCE)
            self.strong_sell_score = saved_config.get("STRONG_SELL_SCORE", STRONG_SELL_SCORE)
            self.strong_sell_confidence = saved_config.get("STRONG_SELL_CONFIDENCE", STRONG_SELL_CONFIDENCE)
            self.moderate_sell_score = saved_config.get("MODERATE_SELL_SCORE", MODERATE_SELL_SCORE)
            self.moderate_sell_confidence = saved_config.get("MODERATE_SELL_CONFIDENCE", MODERATE_SELL_CONFIDENCE)
            # Technical component weights
            self.tech_sma20_bullish = saved_config.get("TECH_SMA20_BULLISH", TECH_SMA20_BULLISH)
            self.tech_sma20_bearish = saved_config.get("TECH_SMA20_BEARISH", TECH_SMA20_BEARISH)
            self.tech_sma50_bullish = saved_config.get("TECH_SMA50_BULLISH", TECH_SMA50_BULLISH)
            self.tech_sma50_bearish = saved_config.get("TECH_SMA50_BEARISH", TECH_SMA50_BEARISH)
            self.tech_golden_cross = saved_config.get("TECH_GOLDEN_CROSS", TECH_GOLDEN_CROSS)
            self.tech_death_cross = saved_config.get("TECH_DEATH_CROSS", TECH_DEATH_CROSS)
            self.tech_rsi_neutral = saved_config.get("TECH_RSI_NEUTRAL", TECH_RSI_NEUTRAL)
            self.tech_rsi_bullish = saved_config.get("TECH_RSI_BULLISH", TECH_RSI_BULLISH)
            self.tech_rsi_weak_bullish = saved_config.get("TECH_RSI_WEAK_BULLISH", TECH_RSI_WEAK_BULLISH)
            self.tech_rsi_overbought = saved_config.get("TECH_RSI_OVERBOUGHT", TECH_RSI_OVERBOUGHT)
            self.tech_rsi_oversold = saved_config.get("TECH_RSI_OVERSOLD", TECH_RSI_OVERSOLD)
            # Decay weights
            if "DECAY_WEIGHTS" in saved_config:
                self.decay_weights = saved_config["DECAY_WEIGHTS"]
            # Technical indicator periods
            self.rsi_period = saved_config.get("RSI_PERIOD", RSI_PERIOD)
            self.sma_short_period = saved_config.get("SMA_SHORT_PERIOD", SMA_SHORT_PERIOD)
            self.sma_medium_period = saved_config.get("SMA_MEDIUM_PERIOD", SMA_MEDIUM_PERIOD)
            self.sma_long_period = saved_config.get("SMA_LONG_PERIOD", SMA_LONG_PERIOD)
            self.macd_fast = saved_config.get("MACD_FAST", MACD_FAST)
            self.macd_slow = saved_config.get("MACD_SLOW", MACD_SLOW)
            self.macd_signal = saved_config.get("MACD_SIGNAL", MACD_SIGNAL)
            self.bb_period = saved_config.get("BB_PERIOD", BB_PERIOD)
            self.bb_std_dev = saved_config.get("BB_STD_DEV", BB_STD_DEV)
            self.atr_period = saved_config.get("ATR_PERIOD", ATR_PERIOD)
            self.stoch_period = saved_config.get("STOCH_PERIOD", STOCH_PERIOD)
            self.adx_period = saved_config.get("ADX_PERIOD", ADX_PERIOD)
            # Technical indicator timeframes
            self.rsi_timeframe = saved_config.get("RSI_TIMEFRAME", RSI_TIMEFRAME)
            self.sma_short_timeframe = saved_config.get("SMA_SHORT_TIMEFRAME", SMA_SHORT_TIMEFRAME)
            self.sma_medium_timeframe = saved_config.get("SMA_MEDIUM_TIMEFRAME", SMA_MEDIUM_TIMEFRAME)
            self.sma_long_timeframe = saved_config.get("SMA_LONG_TIMEFRAME", SMA_LONG_TIMEFRAME)
            self.macd_timeframe = saved_config.get("MACD_TIMEFRAME", MACD_TIMEFRAME)
            self.bb_timeframe = saved_config.get("BB_TIMEFRAME", BB_TIMEFRAME)
            self.atr_timeframe = saved_config.get("ATR_TIMEFRAME", ATR_TIMEFRAME)
            self.stoch_timeframe = saved_config.get("STOCH_TIMEFRAME", STOCH_TIMEFRAME)
            self.adx_timeframe = saved_config.get("ADX_TIMEFRAME", ADX_TIMEFRAME)
            # Technical indicator lookbacks
            self.rsi_lookback = saved_config.get("RSI_LOOKBACK", RSI_LOOKBACK)
            self.sma_short_lookback = saved_config.get("SMA_SHORT_LOOKBACK", SMA_SHORT_LOOKBACK)
            self.sma_medium_lookback = saved_config.get("SMA_MEDIUM_LOOKBACK", SMA_MEDIUM_LOOKBACK)
            self.sma_long_lookback = saved_config.get("SMA_LONG_LOOKBACK", SMA_LONG_LOOKBACK)
            self.macd_lookback = saved_config.get("MACD_LOOKBACK", MACD_LOOKBACK)
            self.bb_lookback = saved_config.get("BB_LOOKBACK", BB_LOOKBACK)
            self.atr_lookback = saved_config.get("ATR_LOOKBACK", ATR_LOOKBACK)
            self.stoch_lookback = saved_config.get("STOCH_LOOKBACK", STOCH_LOOKBACK)
            self.adx_lookback = saved_config.get("ADX_LOOKBACK", ADX_LOOKBACK)
            # Risk management parameters
            self.risk_volatility_weight = saved_config.get("RISK_VOLATILITY_WEIGHT", RISK_VOLATILITY_WEIGHT)
            self.risk_proximity_weight = saved_config.get("RISK_PROXIMITY_WEIGHT", RISK_PROXIMITY_WEIGHT)
            self.risk_trend_strength_weight = saved_config.get("RISK_TREND_STRENGTH_WEIGHT", RISK_TREND_STRENGTH_WEIGHT)
            self.stop_loss_sr_buffer = saved_config.get("STOP_LOSS_SR_BUFFER", STOP_LOSS_SR_BUFFER)
            self.stop_loss_atr_mult = saved_config.get("STOP_LOSS_ATR_MULTIPLIER", STOP_LOSS_ATR_MULTIPLIER)
            self.take_profit_atr_mult = saved_config.get("TAKE_PROFIT_ATR_MULTIPLIER", TAKE_PROFIT_ATR_MULTIPLIER)
            self.sr_support_max_distance_pct = saved_config.get("SR_SUPPORT_MAX_DISTANCE_PCT", SR_SUPPORT_MAX_DISTANCE_PCT)
            self.sr_resistance_max_distance_pct = saved_config.get("SR_RESISTANCE_MAX_DISTANCE_PCT", SR_RESISTANCE_MAX_DISTANCE_PCT)
            self.sr_dbscan_eps = saved_config.get("SR_DBSCAN_EPS", SR_DBSCAN_EPS)
            self.sr_dbscan_min_samples = saved_config.get("SR_DBSCAN_MIN_SAMPLES", SR_DBSCAN_MIN_SAMPLES)
            self.sr_dbscan_order = saved_config.get("SR_DBSCAN_ORDER", SR_DBSCAN_ORDER)
            self.sr_dbscan_lookback = saved_config.get("SR_DBSCAN_LOOKBACK", SR_DBSCAN_LOOKBACK)
            print("📝 Config loaded from file with custom weights")
        
        # Initialize nested dicts if not loaded (legacy compatibility)
        if self.decay_weights is None:
            self.decay_weights = DECAY_WEIGHTS.copy()
        
        if self.sma_periods is None:
            self.sma_periods = {
                'short': self.sma_short_period,
                'medium': self.sma_medium_period,
                'long': self.sma_long_period
            }
        
        if self.macd_params is None:
            self.macd_params = {
                'fast': self.macd_fast,
                'slow': self.macd_slow,
                'signal': self.macd_signal
            }
        
        # 🆕 Initialize scheduler ticker lists
        if self.bet_tickers is None:
            self.bet_tickers = BET_TICKERS.copy()
        
        if self.us_tickers is None:
            self.us_tickers = US_TICKERS.copy()
        
        if self.all_tickers is None:
            self.all_tickers = ALL_TICKERS.copy()
        
        # ===== AUTO-MIGRATION: Save new parameters to file =====
        # Check if saved_config is missing any of the new parameters
        if saved_config:
            new_params = [
                'SR_DBSCAN_EPS', 'SR_DBSCAN_MIN_SAMPLES', 'SR_DBSCAN_ORDER', 'SR_DBSCAN_LOOKBACK',
                'RSI_TIMEFRAME', 'SMA_SHORT_TIMEFRAME', 'MACD_TIMEFRAME',
                'RISK_VOLATILITY_WEIGHT', 'RISK_PROXIMITY_WEIGHT'
            ]
            
            missing_params = [p for p in new_params if p not in saved_config]
            
            if missing_params:
                print(f"🔄 Auto-migration: Detected {len(missing_params)} new parameters")
                print(f"   New params: {', '.join(missing_params[:3])}...")
                save_config_to_file(self)
                print("✅ Config auto-migrated with new parameters")
    
    # Uppercase property aliases for backward compatibility
    @property
    def SENTIMENT_WEIGHT(self):
        return self.sentiment_weight
    
    @SENTIMENT_WEIGHT.setter
    def SENTIMENT_WEIGHT(self, value):
        self.sentiment_weight = value
    
    @property
    def TECHNICAL_WEIGHT(self):
        return self.technical_weight
    
    @TECHNICAL_WEIGHT.setter
    def TECHNICAL_WEIGHT(self, value):
        self.technical_weight = value
    
    @property
    def RISK_WEIGHT(self):
        return self.risk_weight
    
    @RISK_WEIGHT.setter
    def RISK_WEIGHT(self, value):
        self.risk_weight = value
    
    @property
    def STRONG_BUY_SCORE(self):
        return self.strong_buy_score
    
    @property
    def STRONG_BUY_CONFIDENCE(self):
        return self.strong_buy_confidence
    
    @property
    def MODERATE_BUY_SCORE(self):
        return self.moderate_buy_score
    
    @property
    def MODERATE_BUY_CONFIDENCE(self):
        return self.moderate_buy_confidence
    
    @property
    def STRONG_SELL_SCORE(self):
        return self.strong_sell_score
    
    @property
    def STRONG_SELL_CONFIDENCE(self):
        return self.strong_sell_confidence
    
    @property
    def MODERATE_SELL_SCORE(self):
        return self.moderate_sell_score
    
    @property
    def MODERATE_SELL_CONFIDENCE(self):
        return self.moderate_sell_confidence
    
    def reload(self):
        """Reload configuration from file"""
        saved_config = load_config_from_file()
        if saved_config:
            self.sentiment_weight = saved_config.get("SENTIMENT_WEIGHT", SENTIMENT_WEIGHT)
            self.technical_weight = saved_config.get("TECHNICAL_WEIGHT", TECHNICAL_WEIGHT)
            self.risk_weight = saved_config.get("RISK_WEIGHT", RISK_WEIGHT)
            self.strong_buy_score = saved_config.get("STRONG_BUY_SCORE", STRONG_BUY_SCORE)
            self.strong_buy_confidence = saved_config.get("STRONG_BUY_CONFIDENCE", STRONG_BUY_CONFIDENCE)
            self.moderate_buy_score = saved_config.get("MODERATE_BUY_SCORE", MODERATE_BUY_SCORE)
            self.moderate_buy_confidence = saved_config.get("MODERATE_BUY_CONFIDENCE", MODERATE_BUY_CONFIDENCE)
            self.strong_sell_score = saved_config.get("STRONG_SELL_SCORE", STRONG_SELL_SCORE)
            self.strong_sell_confidence = saved_config.get("STRONG_SELL_CONFIDENCE", STRONG_SELL_CONFIDENCE)
            self.moderate_sell_score = saved_config.get("MODERATE_SELL_SCORE", MODERATE_SELL_SCORE)
            self.moderate_sell_confidence = saved_config.get("MODERATE_SELL_CONFIDENCE", MODERATE_SELL_CONFIDENCE)
            # Technical component weights
            self.tech_sma20_bullish = saved_config.get("TECH_SMA20_BULLISH", TECH_SMA20_BULLISH)
            self.tech_sma20_bearish = saved_config.get("TECH_SMA20_BEARISH", TECH_SMA20_BEARISH)
            self.tech_sma50_bullish = saved_config.get("TECH_SMA50_BULLISH", TECH_SMA50_BULLISH)
            self.tech_sma50_bearish = saved_config.get("TECH_SMA50_BEARISH", TECH_SMA50_BEARISH)
            self.tech_golden_cross = saved_config.get("TECH_GOLDEN_CROSS", TECH_GOLDEN_CROSS)
            self.tech_death_cross = saved_config.get("TECH_DEATH_CROSS", TECH_DEATH_CROSS)
            self.tech_rsi_neutral = saved_config.get("TECH_RSI_NEUTRAL", TECH_RSI_NEUTRAL)
            self.tech_rsi_bullish = saved_config.get("TECH_RSI_BULLISH", TECH_RSI_BULLISH)
            self.tech_rsi_weak_bullish = saved_config.get("TECH_RSI_WEAK_BULLISH", TECH_RSI_WEAK_BULLISH)
            self.tech_rsi_overbought = saved_config.get("TECH_RSI_OVERBOUGHT", TECH_RSI_OVERBOUGHT)
            self.tech_rsi_oversold = saved_config.get("TECH_RSI_OVERSOLD", TECH_RSI_OVERSOLD)
            # NEW: Additional indicator weights
            self.tech_macd_weight = saved_config.get("TECH_MACD_WEIGHT", TECH_MACD_WEIGHT)
            self.tech_bollinger_weight = saved_config.get("TECH_BOLLINGER_WEIGHT", TECH_BOLLINGER_WEIGHT)
            self.tech_stochastic_weight = saved_config.get("TECH_STOCHASTIC_WEIGHT", TECH_STOCHASTIC_WEIGHT)
            self.tech_cci_weight = saved_config.get("TECH_CCI_WEIGHT", TECH_CCI_WEIGHT)
            self.tech_volume_weight = saved_config.get("TECH_VOLUME_WEIGHT", TECH_VOLUME_WEIGHT)
            self.tech_adx_weight = saved_config.get("TECH_ADX_WEIGHT", TECH_ADX_WEIGHT)
            # Technical indicator periods
            self.rsi_period = saved_config.get("RSI_PERIOD", RSI_PERIOD)
            self.sma_short_period = saved_config.get("SMA_SHORT_PERIOD", SMA_SHORT_PERIOD)
            self.sma_medium_period = saved_config.get("SMA_MEDIUM_PERIOD", SMA_MEDIUM_PERIOD)
            self.sma_long_period = saved_config.get("SMA_LONG_PERIOD", SMA_LONG_PERIOD)
            self.macd_fast = saved_config.get("MACD_FAST", MACD_FAST)
            self.macd_slow = saved_config.get("MACD_SLOW", MACD_SLOW)
            self.macd_signal = saved_config.get("MACD_SIGNAL", MACD_SIGNAL)
            self.bb_period = saved_config.get("BB_PERIOD", BB_PERIOD)
            self.bb_std_dev = saved_config.get("BB_STD_DEV", BB_STD_DEV)
            self.atr_period = saved_config.get("ATR_PERIOD", ATR_PERIOD)
            self.stoch_period = saved_config.get("STOCH_PERIOD", STOCH_PERIOD)
            self.adx_period = saved_config.get("ADX_PERIOD", ADX_PERIOD)
            # Technical indicator timeframes
            self.rsi_timeframe = saved_config.get("RSI_TIMEFRAME", RSI_TIMEFRAME)
            self.sma_short_timeframe = saved_config.get("SMA_SHORT_TIMEFRAME", SMA_SHORT_TIMEFRAME)
            self.sma_medium_timeframe = saved_config.get("SMA_MEDIUM_TIMEFRAME", SMA_MEDIUM_TIMEFRAME)
            self.sma_long_timeframe = saved_config.get("SMA_LONG_TIMEFRAME", SMA_LONG_TIMEFRAME)
            self.macd_timeframe = saved_config.get("MACD_TIMEFRAME", MACD_TIMEFRAME)
            self.bb_timeframe = saved_config.get("BB_TIMEFRAME", BB_TIMEFRAME)
            self.atr_timeframe = saved_config.get("ATR_TIMEFRAME", ATR_TIMEFRAME)
            self.stoch_timeframe = saved_config.get("STOCH_TIMEFRAME", STOCH_TIMEFRAME)
            self.adx_timeframe = saved_config.get("ADX_TIMEFRAME", ADX_TIMEFRAME)
            # Technical indicator lookbacks
            self.rsi_lookback = saved_config.get("RSI_LOOKBACK", RSI_LOOKBACK)
            self.sma_short_lookback = saved_config.get("SMA_SHORT_LOOKBACK", SMA_SHORT_LOOKBACK)
            self.sma_medium_lookback = saved_config.get("SMA_MEDIUM_LOOKBACK", SMA_MEDIUM_LOOKBACK)
            self.sma_long_lookback = saved_config.get("SMA_LONG_LOOKBACK", SMA_LONG_LOOKBACK)
            self.macd_lookback = saved_config.get("MACD_LOOKBACK", MACD_LOOKBACK)
            self.bb_lookback = saved_config.get("BB_LOOKBACK", BB_LOOKBACK)
            self.atr_lookback = saved_config.get("ATR_LOOKBACK", ATR_LOOKBACK)
            self.stoch_lookback = saved_config.get("STOCH_LOOKBACK", STOCH_LOOKBACK)
            self.adx_lookback = saved_config.get("ADX_LOOKBACK", ADX_LOOKBACK)
            # Risk management parameters
            self.risk_volatility_weight = saved_config.get("RISK_VOLATILITY_WEIGHT", RISK_VOLATILITY_WEIGHT)
            self.risk_proximity_weight = saved_config.get("RISK_PROXIMITY_WEIGHT", RISK_PROXIMITY_WEIGHT)
            self.risk_trend_strength_weight = saved_config.get("RISK_TREND_STRENGTH_WEIGHT", RISK_TREND_STRENGTH_WEIGHT)
            self.stop_loss_sr_buffer = saved_config.get("STOP_LOSS_SR_BUFFER", STOP_LOSS_SR_BUFFER)
            self.stop_loss_atr_mult = saved_config.get("STOP_LOSS_ATR_MULTIPLIER", STOP_LOSS_ATR_MULTIPLIER)
            self.take_profit_atr_mult = saved_config.get("TAKE_PROFIT_ATR_MULTIPLIER", TAKE_PROFIT_ATR_MULTIPLIER)
            self.sr_support_max_distance_pct = saved_config.get("SR_SUPPORT_MAX_DISTANCE_PCT", SR_SUPPORT_MAX_DISTANCE_PCT)
            self.sr_resistance_max_distance_pct = saved_config.get("SR_RESISTANCE_MAX_DISTANCE_PCT", SR_RESISTANCE_MAX_DISTANCE_PCT)
            self.sr_dbscan_eps = saved_config.get("SR_DBSCAN_EPS", SR_DBSCAN_EPS)
            self.sr_dbscan_min_samples = saved_config.get("SR_DBSCAN_MIN_SAMPLES", SR_DBSCAN_MIN_SAMPLES)
            self.sr_dbscan_order = saved_config.get("SR_DBSCAN_ORDER", SR_DBSCAN_ORDER)
            self.sr_dbscan_lookback = saved_config.get("SR_DBSCAN_LOOKBACK", SR_DBSCAN_LOOKBACK)
            print("🔄 Config reloaded from file")
    
    def validate(self) -> bool:
        """Validate configuration"""
        # Check API keys
        if not self.newsapi_key or self.newsapi_key == "YOUR_NEWSAPI_KEY_HERE":
            print("⚠️ Warning: NewsAPI key not set!")
            return False
        
        if not self.alphavantage_key or self.alphavantage_key == "YOUR_ALPHAVANTAGE_KEY_HERE":
            print("⚠️ Warning: Alpha Vantage key not set!")
            return False
        
        # Check weights sum to 1.0
        total_weight = self.sentiment_weight + self.technical_weight + self.risk_weight
        if abs(total_weight - 1.0) > 0.01:
            print(f"⚠️ Warning: Component weights sum to {total_weight}, not 1.0!")
            return False
        
        print("✅ Configuration validated!")
        return True
    
    def display(self):
        """Display current configuration"""
        print("=" * 60)
        print("TrendSignal MVP Configuration")
        print("=" * 60)
        print()
        
        print("⚖️ Component Weights:")
        print(f"  Sentiment: {self.sentiment_weight:.0%}")
        print(f"  Technical: {self.technical_weight:.0%}")
        print(f"  Risk:      {self.risk_weight:.0%}")
        print()
        
        print("⏱️ Sentiment Decay Model (24h window):")
        for period, weight in self.decay_weights.items():
            marker = "🆕" if '24h' in period else ""
            print(f"  {period:8s}: {weight:.0%}  {marker}")
        print()
        
        print("🎯 Decision Thresholds:")
        print(f"  STRONG BUY:  Score ≥ {self.strong_buy_score:+d}, Conf ≥ {self.strong_buy_confidence:.0%}")
        print(f"  MOD BUY:     Score ≥ {self.moderate_buy_score:+d}, Conf ≥ {self.moderate_buy_confidence:.0%}")
        print(f"  STRONG SELL: Score ≤ {self.strong_sell_score:+d}, Conf ≥ {self.strong_sell_confidence:.0%}")
        print(f"  MOD SELL:    Score ≤ {self.moderate_sell_score:+d}, Conf ≥ {self.moderate_sell_confidence:.0%}")
        print()
        
        print("📊 Technical Indicators:")
        print(f"  SMA: {self.sma_periods['short']}, {self.sma_periods['medium']}, {self.sma_periods['long']}")
        print(f"  MACD: ({self.macd_params['fast']}, {self.macd_params['slow']}, {self.macd_params['signal']})")
        print(f"  RSI: {self.rsi_period}")
        print()
        
        print("⏰ Scheduler Settings:")
        print(f"  Refresh Interval: {self.signal_refresh_interval} minutes")
        print(f"  BÉT Hours: {self.bet_market_open}-{self.bet_market_close} {self.bet_timezone}")
        print(f"  US Hours:  {self.us_market_open}-{self.us_market_close} {self.us_timezone}")
        print()
        
        print("=" * 60)


# ==========================================
# DEFAULT CONFIG INSTANCE
# ==========================================

default_config = TrendSignalConfig()


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_config() -> TrendSignalConfig:
    """Get default configuration instance"""
    return default_config

def reload_config():
    """Reload configuration from file"""
    default_config.reload()
    return default_config

def get_signal_weights():
    """Get signal component weights as tuple"""
    return (
        default_config.SENTIMENT_WEIGHT,
        default_config.TECHNICAL_WEIGHT,
        default_config.RISK_WEIGHT
    )

def get_buy_thresholds():
    """Get BUY thresholds"""
    return {
        "strong": {
            "score": default_config.STRONG_BUY_SCORE,
            "confidence": default_config.STRONG_BUY_CONFIDENCE
        },
        "moderate": {
            "score": default_config.MODERATE_BUY_SCORE,
            "confidence": default_config.MODERATE_BUY_CONFIDENCE
        }
    }

def get_sell_thresholds():
    """Get SELL thresholds"""
    return {
        "strong": {
            "score": default_config.STRONG_SELL_SCORE,
            "confidence": default_config.STRONG_SELL_CONFIDENCE
        },
        "moderate": {
            "score": default_config.MODERATE_SELL_SCORE,
            "confidence": default_config.MODERATE_SELL_CONFIDENCE
        }
    }

def load_config_from_env() -> TrendSignalConfig:
    """Load configuration from environment variables"""
    config = TrendSignalConfig(
        newsapi_key=os.getenv("NEWSAPI_KEY", NEWSAPI_KEY),
        alphavantage_key=os.getenv("ALPHAVANTAGE_KEY", ALPHAVANTAGE_KEY),
    )
    return config


if __name__ == "__main__":
    # Test configuration
    config = get_config()
    config.display()
    config.validate()
