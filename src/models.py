"""
Database models - SIMPLIFIED VERSION
NO relationships() - only ForeignKey constraints
This prevents SQLAlchemy registry conflicts

Version: 2.0 - Simplified
Date: 2026-02-04
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.sql import func
from database import Base

# ===== CORE TABLES =====

class Ticker(Base):
    """Stock ticker/company information"""
    __tablename__ = "tickers"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100))
    market = Column(String(20))
    industry = Column(String(50))
    market_cap = Column(BigInteger)
    priority = Column(String(10), default='medium')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Language & Localization
    primary_language = Column(String(5), default='en')
    sector = Column(String(50))
    currency = Column(String(3))
    
    # Keywords (JSON arrays)
    relevance_keywords = Column(Text)
    sentiment_keywords_positive = Column(Text)
    sentiment_keywords_negative = Column(Text)
    
    # News Sources
    news_sources_preferred = Column(Text)
    news_sources_blocked = Column(Text)


class NewsSource(Base):
    """News data sources"""
    __tablename__ = "news_sources"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20))
    url = Column(Text)
    credibility_weight = Column(Float, default=0.80)
    is_enabled = Column(Boolean, default=True)
    polling_frequency_hours = Column(Integer, default=2)
    created_at = Column(DateTime, server_default=func.now())


class NewsItem(Base):
    """Individual news articles"""
    __tablename__ = "news_items"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    url_hash = Column(String(32), unique=True, nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("news_sources.id"))
    
    title = Column(Text, nullable=False)
    description = Column(Text)
    full_text = Column(Text)
    author = Column(String(200))
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, server_default=func.now())
    
    language = Column(String(10))
    
    is_relevant = Column(Boolean)
    relevance_score = Column(Float)
    
    sentiment_score = Column(Float)
    sentiment_confidence = Column(Float)
    sentiment_label = Column(String(20))
    
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("news_items.id"), nullable=True)
    cluster_id = Column(String(50))


class NewsTicker(Base):
    """Many-to-many: news <-> tickers"""
    __tablename__ = "news_tickers"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False)
    ticker_id = Column(Integer, ForeignKey("tickers.id", ondelete="CASCADE"), nullable=False)
    relevance_score = Column(Float)


class NewsCategory(Base):
    """News categories"""
    __tablename__ = "news_categories"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(50), nullable=False)
    confidence = Column(Float)


class PriceData(Base):
    """Historical price data"""
    __tablename__ = "price_data"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    ticker_symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    interval = Column(String(5), nullable=False)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    
    price_change = Column(Float)
    price_change_pct = Column(Float)
    
    fetched_at = Column(DateTime, server_default=func.now())


class TechnicalIndicator(Base):
    """Calculated technical indicators"""
    __tablename__ = "technical_indicators"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker_symbol = Column(String(10), nullable=False, index=True)
    interval = Column(String(5), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Trend indicators
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    ema_12 = Column(Float)
    ema_26 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    adx = Column(Float)
    
    # Momentum indicators
    rsi = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)
    cci = Column(Float)
    
    # Volatility indicators
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    atr = Column(Float)
    
    # Volume indicators
    volume_sma = Column(BigInteger)
    obv = Column(BigInteger)
    
    close_price = Column(Float)
    technical_score = Column(Float)
    technical_confidence = Column(Float)
    score_components = Column(Text)
    
    calculated_at = Column(DateTime, server_default=func.now())


class Signal(Base):
    """Generated trading signals"""
    __tablename__ = "signals"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    ticker_symbol = Column(String(10), nullable=False, index=True)
    technical_indicator_id = Column(Integer, ForeignKey("technical_indicators.id"), nullable=True)
    
    decision = Column(String(20), nullable=False)
    strength = Column(String(20))
    
    combined_score = Column(Float)
    sentiment_score = Column(Float)
    technical_score = Column(Float)
    risk_score = Column(Float)
    
    overall_confidence = Column(Float)
    sentiment_confidence = Column(Float)
    technical_confidence = Column(Float)
    
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward_ratio = Column(Float)
    
    reasoning_json = Column(Text)
    
    status = Column(String(20), default='active', index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    expires_at = Column(DateTime)


class SignalCalculation(Base):
    """Audit trail for signal calculations"""
    __tablename__ = "signal_calculations"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker_symbol = Column(String(10), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=False), nullable=False, index=True)
    
    # INPUT VALUES
    current_price = Column(Float, index=True)
    atr = Column(Float)
    atr_pct = Column(Float, index=True)
    rsi = Column(Float, index=True)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    adx = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)
    
    volatility = Column(Float, index=True)
    nearest_support = Column(Float)
    nearest_resistance = Column(Float)
    news_count = Column(Integer, index=True)
    
    # SCORE VALUES
    sentiment_score = Column(Float, index=True)
    sentiment_confidence = Column(Float, index=True)
    technical_score = Column(Float, index=True)
    technical_confidence = Column(Float, index=True)
    risk_score = Column(Float, index=True)
    risk_confidence = Column(Float)
    combined_score = Column(Float, index=True)
    
    # CONFIGURATION
    weight_sentiment = Column(Float, index=True)
    weight_technical = Column(Float, index=True)
    weight_risk = Column(Float, index=True)
    
    threshold_buy = Column(Float)
    threshold_sell = Column(Float)
    threshold_hold_zone = Column(Float)
    
    # TECHNICAL PARAMETERS
    config_rsi_oversold = Column(Float)
    config_rsi_overbought = Column(Float)
    config_adx_strong = Column(Float)
    config_atr_stop_multiplier = Column(Float)
    config_atr_profit_multiplier = Column(Float)
    config_sr_support_max_distance_pct = Column(Float)
    config_sr_resistance_max_distance_pct = Column(Float)
    config_sr_buffer = Column(Float)
    config_dbscan_eps = Column(Float)
    config_dbscan_min_samples = Column(Integer)
    config_dbscan_order = Column(Integer)
    config_dbscan_lookback = Column(Integer)
    
    # RISK PARAMETERS
    config_risk_volatility_weight = Column(Float)
    config_risk_proximity_weight = Column(Float)
    config_risk_trend_strength_weight = Column(Float)
    
    # TECHNICAL COMPONENT WEIGHTS
    config_tech_sma_weight = Column(Float)
    config_tech_rsi_weight = Column(Float)
    config_tech_macd_weight = Column(Float)
    config_tech_bollinger_weight = Column(Float)
    config_tech_stochastic_weight = Column(Float)
    config_tech_volume_weight = Column(Float)
    
    # OUTPUT VALUES
    decision = Column(String(20), index=True)
    strength = Column(String(20))
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward_ratio = Column(Float)
    
    # CONTRIBUTIONS
    sentiment_contribution = Column(Float)
    technical_contribution = Column(Float)
    risk_contribution = Column(Float)
    
    # DETAILED JSON DATA
    news_inputs = Column(Text)
    config_snapshot = Column(Text)
    technical_details = Column(Text)
    risk_details = Column(Text)
    reasoning = Column(Text)
    entry_exit_details = Column(Text)
    
    calculation_duration_ms = Column(Integer)
