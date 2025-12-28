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

# For development/testing (replace with your keys)
if not NEWSAPI_KEY:
    NEWSAPI_KEY = "c042824059404c8e9da37ef7cd4088b6"
if not ALPHAVANTAGE_KEY:
    ALPHAVANTAGE_KEY = "Q3R3ZCIBFDJI8BU9"


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
# PERZISZTENCIA - Config fájl kezelés
# ==========================================

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

def save_config_to_file(config_instance):
    """Save current configuration to JSON file for persistence"""
    try:
        config_dict = {
            "SENTIMENT_WEIGHT": config_instance.sentiment_weight,
            "TECHNICAL_WEIGHT": config_instance.technical_weight,
            "RISK_WEIGHT": config_instance.risk_weight,
            "STRONG_BUY_SCORE": config_instance.strong_buy_score,
            "STRONG_BUY_CONFIDENCE": config_instance.strong_buy_confidence,
            "MODERATE_BUY_SCORE": config_instance.moderate_buy_score,
            "MODERATE_BUY_CONFIDENCE": config_instance.moderate_buy_confidence,
            "STRONG_SELL_SCORE": config_instance.strong_sell_score,
            "STRONG_SELL_CONFIDENCE": config_instance.strong_sell_confidence,
            "MODERATE_SELL_SCORE": config_instance.moderate_sell_score,
            "MODERATE_SELL_CONFIDENCE": config_instance.moderate_sell_confidence,
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
    for key, value in updates.items():
        # Use lowercase attribute names (dataclass convention)
        attr_name = key.lower()
        if hasattr(config_instance, attr_name):
            setattr(config_instance, attr_name, value)
            print(f"  ✓ Updated {key} = {value}")
    
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
    atr_period: int = ATR_PERIOD
    macd_params: Dict[str, int] = None
    
    # Risk management
    stop_loss_atr_mult: float = STOP_LOSS_ATR_MULTIPLIER
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
            print("📝 Config loaded from file with custom weights")
        
        # Initialize nested dicts
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
