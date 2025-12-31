"""
Database Integration Helpers
Functions to save and retrieve news, price data, and technical indicators
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hashlib
import json
from typing import List, Optional
import pandas as pd

from models import (
    NewsItem as NewsItemDB,
    NewsSource,
    NewsTicker,
    NewsCategory,
    Ticker,
    PriceData,
    TechnicalIndicator
)


# ==========================================
# NEWS HELPERS
# ==========================================

def save_news_item_to_db(news_item, ticker_symbol: str, db: Session) -> Optional[NewsItemDB]:
    """
    Save a news item to database with proper relationships
    
    Args:
        news_item: NewsItem object from sentiment_analyzer
        ticker_symbol: Stock ticker symbol
        db: Database session
    
    Returns:
        Saved NewsItemDB object or None if error
    """
    try:
        # Get or create news source
        source = db.query(NewsSource).filter(NewsSource.name == news_item.source).first()
        if not source:
            source = NewsSource(
                name=news_item.source,
                type='api',
                credibility_weight=news_item.credibility,
                is_enabled=True
            )
            db.add(source)
            db.commit()
            db.refresh(source)
        
        # Create URL hash for duplicate detection
        url_hash = hashlib.md5(news_item.url.encode()).hexdigest()
        
        # Check if news already exists
        existing = db.query(NewsItemDB).filter(NewsItemDB.url_hash == url_hash).first()
        if existing:
            # Update ticker association if needed
            ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
            if ticker:
                existing_assoc = db.query(NewsTicker).filter(
                    NewsTicker.news_id == existing.id,
                    NewsTicker.ticker_id == ticker.id
                ).first()
                
                if not existing_assoc:
                    new_assoc = NewsTicker(
                        news_id=existing.id,
                        ticker_id=ticker.id,
                        relevance_score=1.0
                    )
                    db.add(new_assoc)
                    db.commit()
            
            return existing
        
        # Create new news item
        db_news = NewsItemDB(
            url=news_item.url,
            url_hash=url_hash,
            source_id=source.id,
            title=news_item.title,
            description=news_item.description,
            published_at=news_item.published_at,
            fetched_at=datetime.now(timezone.utc),
            language='en',  # Could be detected
            is_relevant=True,
            relevance_score=1.0,
            sentiment_score=news_item.sentiment_score,
            sentiment_confidence=news_item.sentiment_confidence,
            sentiment_label=news_item.sentiment_label,
            is_duplicate=False
        )
        
        db.add(db_news)
        db.commit()
        db.refresh(db_news)
        
        # Create ticker association
        ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
        if ticker:
            news_ticker = NewsTicker(
                news_id=db_news.id,
                ticker_id=ticker.id,
                relevance_score=1.0
            )
            db.add(news_ticker)
            db.commit()
        
        return db_news
        
    except Exception as e:
        print(f"❌ Error saving news to DB: {e}")
        db.rollback()
        return None


def get_recent_news_from_db(ticker_symbol: str, hours: int, db: Session) -> List[NewsItemDB]:
    """Get recent news for a ticker from database"""
    try:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
        if not ticker:
            return []
        
        news_items = db.query(NewsItemDB).join(NewsTicker).filter(
            NewsTicker.ticker_id == ticker.id,
            NewsItemDB.published_at >= cutoff
        ).order_by(NewsItemDB.published_at.desc()).all()
        
        return news_items
        
    except Exception as e:
        print(f"❌ Error fetching news from DB: {e}")
        return []


# ==========================================
# PRICE DATA HELPERS
# ==========================================

def save_price_data_to_db(df: pd.DataFrame, ticker_symbol: str, interval: str, db: Session) -> int:
    """
    Save price data DataFrame to database
    
    Args:
        df: Pandas DataFrame with OHLCV data
        ticker_symbol: Stock ticker
        interval: Data interval ('5m', '1h', '1d')
        db: Database session
    
    Returns:
        Number of records saved
    """
    try:
        # Get ticker
        ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
        if not ticker:
            ticker = Ticker(symbol=ticker_symbol, name=ticker_symbol, is_active=True)
            db.add(ticker)
            db.commit()
            db.refresh(ticker)
        
        saved_count = 0
        
        for timestamp, row in df.iterrows():
            # Convert timestamp to timezone-aware datetime
            if hasattr(timestamp, 'tz_localize'):
                timestamp = timestamp.tz_localize(timezone.utc) if timestamp.tz is None else timestamp
            elif not hasattr(timestamp, 'tzinfo') or timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            # Check if record exists
            existing = db.query(PriceData).filter(
                PriceData.ticker_symbol == ticker_symbol,
                PriceData.timestamp == timestamp,
                PriceData.interval == interval
            ).first()
            
            if existing:
                continue
            
            # Calculate price change
            price_change = row['Close'] - row['Open']
            price_change_pct = (price_change / row['Open']) * 100 if row['Open'] != 0 else 0
            
            # Create price record
            price_record = PriceData(
                ticker_id=ticker.id,
                ticker_symbol=ticker_symbol,
                timestamp=timestamp,
                interval=interval,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']),
                price_change=float(price_change),
                price_change_pct=float(price_change_pct),
                fetched_at=datetime.now(timezone.utc)
            )
            
            db.add(price_record)
            saved_count += 1
        
        db.commit()
        
        if saved_count > 0:
            print(f"💾 Saved {saved_count} price records for {ticker_symbol} ({interval})")
        
        return saved_count
        
    except Exception as e:
        print(f"❌ Error saving price data to DB: {e}")
        db.rollback()
        return 0


def get_price_data_from_db(
    ticker_symbol: str,
    interval: str,
    days: int,
    db: Session
) -> Optional[pd.DataFrame]:
    """Get price data from database as DataFrame"""
    try:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        records = db.query(PriceData).filter(
            PriceData.ticker_symbol == ticker_symbol,
            PriceData.interval == interval,
            PriceData.timestamp >= cutoff
        ).order_by(PriceData.timestamp).all()
        
        if not records:
            return None
        
        # Convert to DataFrame
        data = {
            'Open': [r.open for r in records],
            'High': [r.high for r in records],
            'Low': [r.low for r in records],
            'Close': [r.close for r in records],
            'Volume': [r.volume for r in records]
        }
        
        index = [r.timestamp for r in records]
        df = pd.DataFrame(data, index=index)
        df.index.name = 'Datetime'
        
        print(f"✅ Loaded {len(df)} price records from DB for {ticker_symbol} ({interval})")
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading price data from DB: {e}")
        return None


# ==========================================
# TECHNICAL INDICATOR HELPERS
# ==========================================

def save_technical_indicators_to_db(
    ticker_symbol: str,
    interval: str,
    timestamp: datetime,
    indicators: dict,
    db: Session
) -> Optional[TechnicalIndicator]:
    """Save technical indicators to database"""
    try:
        # Check if record exists
        existing = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.ticker_symbol == ticker_symbol,
            TechnicalIndicator.interval == interval,
            TechnicalIndicator.timestamp == timestamp
        ).first()
        
        if existing:
            return existing
        
        # Create new record
        tech_record = TechnicalIndicator(
            ticker_symbol=ticker_symbol,
            interval=interval,
            timestamp=timestamp,
            sma_20=indicators.get('sma_20'),
            sma_50=indicators.get('sma_50'),
            sma_200=indicators.get('sma_200'),
            ema_12=indicators.get('ema_12'),
            ema_26=indicators.get('ema_26'),
            macd=indicators.get('macd'),
            macd_signal=indicators.get('macd_signal'),
            macd_histogram=indicators.get('macd_histogram'),
            adx=indicators.get('adx'),
            rsi=indicators.get('rsi'),
            stoch_k=indicators.get('stoch_k'),
            stoch_d=indicators.get('stoch_d'),
            cci=indicators.get('cci'),
            bb_upper=indicators.get('bb_upper'),
            bb_middle=indicators.get('bb_middle'),
            bb_lower=indicators.get('bb_lower'),
            atr=indicators.get('atr'),
            volume_sma=indicators.get('volume_sma'),
            obv=indicators.get('obv'),
            close_price=indicators.get('close_price'),
            calculated_at=datetime.now(timezone.utc)
        )
        
        db.add(tech_record)
        db.commit()
        db.refresh(tech_record)
        
        return tech_record
        
    except Exception as e:
        print(f"❌ Error saving technical indicators to DB: {e}")
        db.rollback()
        return None
