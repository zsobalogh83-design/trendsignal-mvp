"""
TrendSignal MVP - Configuration Module
Centralized configuration for all components

Version: 1.0
Date: 2024-12-27
"""

from typing import Dict, Any
from dataclasses import dataclass
import os


# ==========================================
# API KEYS (Environment Variables)
# ==========================================

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY", "")

# For development/testing (replace with your keys)
if not NEWSAPI_KEY:
    NEWSAPI_KEY = "YOUR_NEWSAPI_KEY_HERE"
if not ALPHAVANTAGE_KEY:
    ALPHAVANTAGE_KEY = "YOUR_ALPHAVANTAGE_KEY_HERE"


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

# SMA periods
SMA_SHORT = 20
SMA_MEDIUM = 50
SMA_LONG = 200

# EMA periods
EMA_FAST = 12
EMA_SLOW = 26

# MACD parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# RSI period
RSI_PERIOD = 14

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2

# ATR period
ATR_PERIOD = 14


# ==========================================
# RISK MANAGEMENT
# ==========================================

# Stop-loss calculation
STOP_LOSS_ATR_MULTIPLIER = 1.5
MIN_STOP_LOSS_PCT = 0.02  # 2%
MAX_STOP_LOSS_PCT = 0.05  # 5%

# Take-profit calculation
RISK_REWARD_RATIO = 2.0  # Target R:R = 1:2


# ==========================================
# NEWS COLLECTION
# ==========================================

NEWS_LOOKBACK_HOURS = 24  # Only collect last 24h
NEWS_RELEVANCE_THRESHOLD = 0.5  # Minimum relevance score
NEWS_MAX_AGE_HOURS = 24  # Maximum age for sentiment calculation


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
# CONFIGURATION DATACLASS
# ==========================================

@dataclass
class TrendSignalConfig:
    """Complete configuration for TrendSignal MVP"""
    
    # API Keys
    newsapi_key: str = NEWSAPI_KEY
    alphavantage_key: str = ALPHAVANTAGE_KEY
    
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
    
    # Technical parameters
    sma_periods: Dict[str, int] = None
    rsi_period: int = RSI_PERIOD
    macd_params: Dict[str, int] = None
    
    # Risk management
    stop_loss_atr_mult: float = STOP_LOSS_ATR_MULTIPLIER
    risk_reward_ratio: float = RISK_REWARD_RATIO
    
    def __post_init__(self):
        """Initialize nested dictionaries"""
        if self.decay_weights is None:
            self.decay_weights = DECAY_WEIGHTS.copy()
        
        if self.sma_periods is None:
            self.sma_periods = {
                'short': SMA_SHORT,
                'medium': SMA_MEDIUM,
                'long': SMA_LONG
            }
        
        if self.macd_params is None:
            self.macd_params = {
                'fast': MACD_FAST,
                'slow': MACD_SLOW,
                'signal': MACD_SIGNAL
            }
    
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
