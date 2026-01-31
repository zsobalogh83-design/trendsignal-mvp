"""
Database models based on TrendSignal MVP specification
SQLAlchemy ORM models for SQLite
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
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
    market = Column(String(20))  # 'BET', 'NYSE', 'NASDAQ'
    industry = Column(String(50))
    market_cap = Column(BigInteger)
    priority = Column(String(10), default='medium')  # 'high', 'medium', 'low'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    signals = relationship("Signal", back_populates="ticker", lazy="dynamic")
    price_data = relationship("PriceData", back_populates="ticker", lazy="dynamic")


class NewsSource(Base):
    """News data sources (APIs, RSS feeds)"""
    __tablename__ = "news_sources"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20))  # 'api', 'rss', 'scraper'
    url = Column(Text)
    credibility_weight = Column(Float, default=0.80)
    is_enabled = Column(Boolean, default=True)
    polling_frequency_hours = Column(Integer, default=2)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    news_items = relationship("NewsItem", back_populates="source", lazy="dynamic")


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
    
    # Relevance
    is_relevant = Column(Boolean)
    relevance_score = Column(Float)
    
    # Sentiment
    sentiment_score = Column(Float)  # -1.00 to +1.00
    sentiment_confidence = Column(Float)
    sentiment_label = Column(String(20))  # positive/neutral/negative
    
    # Duplicate handling
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("news_items.id"), nullable=True)
    cluster_id = Column(String(50))
    
    # Relationships
    source = relationship("NewsSource", back_populates="news_items", lazy="select")
    categories = relationship("NewsCategory", back_populates="news_item", cascade="all, delete-orphan", lazy="dynamic")
    tickers = relationship("NewsTicker", back_populates="news_item", cascade="all, delete-orphan", lazy="dynamic")


class NewsTicker(Base):
    """Many-to-many relationship between news and tickers"""
    __tablename__ = "news_tickers"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False)
    ticker_id = Column(Integer, ForeignKey("tickers.id", ondelete="CASCADE"), nullable=False)
    relevance_score = Column(Float)
    
    # Relationships
    news_item = relationship("NewsItem", back_populates="tickers", lazy="select")
    ticker = relationship("Ticker", lazy="select")


class NewsCategory(Base):
    """Categories for news items (multi-label)"""
    __tablename__ = "news_categories"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(50), nullable=False)
    confidence = Column(Float)
    
    # Relationships
    news_item = relationship("NewsItem", back_populates="categories", lazy="select")


class PriceData(Base):
    """Historical price data (OHLCV)"""
    __tablename__ = "price_data"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    ticker_symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    interval = Column(String(5), nullable=False)  # '1m', '5m', '1h', '1d'
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    
    price_change = Column(Float)
    price_change_pct = Column(Float)
    
    fetched_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    ticker = relationship("Ticker", back_populates="price_data", lazy="select")


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
    calculated_at = Column(DateTime, server_default=func.now())


class Signal(Base):
    """Generated trading signals"""
    __tablename__ = "signals"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    ticker_symbol = Column(String(10), nullable=False, index=True)
    
    # Decision
    decision = Column(String(20), nullable=False)  # BUY/SELL/HOLD
    strength = Column(String(20))  # STRONG/MODERATE/WEAK
    
    # Scores
    combined_score = Column(Float)
    sentiment_score = Column(Float)
    technical_score = Column(Float)
    risk_score = Column(Float)
    
    # Confidence
    overall_confidence = Column(Float)
    sentiment_confidence = Column(Float)
    technical_confidence = Column(Float)
    
    # Entry/Exit levels
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward_ratio = Column(Float)
    
    # Reasoning (JSON string)
    reasoning_json = Column(Text)
    
    # Lifecycle
    status = Column(String(20), default='active', index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    expires_at = Column(DateTime)
    
    # Relationships
    ticker = relationship("Ticker", back_populates="signals", lazy="select")
