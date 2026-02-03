"""
TrendSignal MVP - Source Package
Main modules for sentiment-driven trading signals

Version: 1.0
Date: 2024-12-27
"""

__version__ = "1.0.0"
__author__ = "Claude (Anthropic) + Zsolt Balogh"

# Import main classes for convenience
from .config import TrendSignalConfig, get_config
from .news_collector import NewsCollector
from .sentiment_analyzer import SentimentAnalyzer, SentimentAggregator
from .technical_analyzer import TechnicalAnalyzer
from .signal_generator import SignalGenerator, TradingSignal
from .hungarian_news import HungarianNewsCollector
from .ticker_keywords import TICKER_INFO, get_ticker_keywords, calculate_relevance_score

__all__ = [
    'TrendSignalConfig',
    'get_config',
    'NewsCollector',
    'SentimentAnalyzer',
    'SentimentAggregator',
    'TechnicalAnalyzer',
    'SignalGenerator',
    'TradingSignal',
    'HungarianNewsCollector',
    'TICKER_INFO',
    'get_ticker_keywords',
    'calculate_relevance_score',
]
