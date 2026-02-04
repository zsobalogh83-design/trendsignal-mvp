"""
TrendSignal MVP - Database Helper Functions
Utility functions for database operations with proper timestamp handling

Version: 2.1 - Added Price Data & Technical Indicator Persistence
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from src.sentiment_analyzer import NewsItem


def save_news_item_to_db(news_item: NewsItem, ticker_symbol: str, db: Session) -> bool:
    """
    Save a single NewsItem to database with ORIGINAL published_at timestamp
    Uses proper many-to-many relationship through news_tickers table
    
    Args:
        news_item: NewsItem object with original published_at
        ticker_symbol: Stock ticker symbol
        db: Database session
    
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        from src.models import NewsItem as NewsItemModel, NewsTicker, Ticker as TickerModel, NewsSource
        import hashlib
        
        # Get or create ticker
        ticker = db.query(TickerModel).filter(TickerModel.symbol == ticker_symbol).first()
        if not ticker:
            print(f"⚠️ Ticker {ticker_symbol} not found in database, skipping news save")
            return False
        
        # Generate URL hash for duplicate detection
        url_hash = hashlib.md5(news_item.url.encode()).hexdigest()
        
        # Check for duplicates by URL hash
        existing = db.query(NewsItemModel).filter(
            NewsItemModel.url_hash == url_hash
        ).first()
        
        if existing:
            # Check if already linked to this ticker
            existing_link = db.query(NewsTicker).filter(
                NewsTicker.news_id == existing.id,
                NewsTicker.ticker_id == ticker.id
            ).first()
            
            if not existing_link:
                # Link existing news to this ticker
                link = NewsTicker(
                    news_id=existing.id,
                    ticker_id=ticker.id,
                    relevance_score=1.0
                )
                db.add(link)
                db.commit()
                return True
            
            # Already linked, update sentiment if changed
            if abs(existing.sentiment_score - news_item.sentiment_score) > 0.1:
                existing.sentiment_score = news_item.sentiment_score
                existing.sentiment_label = news_item.sentiment_label
                db.commit()
                return True
            
            return False  # Already exists and linked, no update needed
        
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
            db.flush()
        
        # Create new news item record with ORIGINAL published_at timestamp
        news_record = NewsItemModel(
            url=news_item.url,
            url_hash=url_hash,
            source_id=source.id,
            title=news_item.title,
            description=news_item.description,
            published_at=news_item.published_at,  # ✅ CRITICAL: Use original timestamp
            fetched_at=datetime.now(timezone.utc),
            language='en',  # Default, could be detected
            is_relevant=True,
            relevance_score=1.0,
            sentiment_score=news_item.sentiment_score,
            sentiment_confidence=news_item.sentiment_confidence,
            sentiment_label=news_item.sentiment_label,
            is_duplicate=False
        )
        
        db.add(news_record)
        db.flush()  # Get news_record.id
        
        # Link to ticker through news_tickers
        link = NewsTicker(
            news_id=news_record.id,
            ticker_id=ticker.id,
            relevance_score=1.0
        )
        db.add(link)
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving news to DB: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_recent_news_from_db(
    ticker_symbol: str,
    db: Session,
    lookback_hours: int = 24,
    min_credibility: float = 0.0
) -> List[NewsItem]:
    """
    Retrieve recent news from database with original timestamps
    Uses proper many-to-many relationship through news_tickers table
    
    Args:
        ticker_symbol: Stock ticker symbol
        db: Database session
        lookback_hours: Hours to look back (default: 24h)
        min_credibility: Minimum credibility score filter
    
    Returns:
        List of NewsItem objects with ORIGINAL published_at timestamps
    """
    try:
        from src.models import NewsItem as NewsItemModel, NewsTicker, Ticker as TickerModel
        
        # Get ticker
        ticker = db.query(TickerModel).filter(TickerModel.symbol == ticker_symbol).first()
        if not ticker:
            print(f"⚠️ Ticker {ticker_symbol} not found")
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        # Query through relationship table
        news_records = db.query(NewsItemModel).join(
            NewsTicker, NewsItemModel.id == NewsTicker.news_id
        ).filter(
            NewsTicker.ticker_id == ticker.id,
            NewsItemModel.published_at >= cutoff_time,
            NewsItemModel.sentiment_score.isnot(None)  # Must have sentiment
        ).order_by(NewsItemModel.published_at.desc()).all()
        
        news_items = []
        for news_record in news_records:
            news_item = NewsItem(
                title=news_record.title,
                description=news_record.description or '',
                url=news_record.url,
                published_at=news_record.published_at,
                source=news_record.source.name if news_record.source else 'Unknown',
                sentiment_score=news_record.sentiment_score,
                sentiment_confidence=news_record.sentiment_confidence or 0.0,
                sentiment_label=news_record.sentiment_label,
                credibility=news_record.source.credibility_weight if news_record.source else 0.8
            )
            news_items.append(news_item)
        
        return news_items
        
    except Exception as e:
        print(f"❌ Error retrieving news from DB: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_price_data_from_db(
    ticker_symbol: str,
    interval: str,
    days: int,
    db: Session
) -> Optional['pd.DataFrame']:
    """
    Retrieve price data from database with FRESHNESS CHECK
    
    Cache is considered STALE if:
    - Last candle is older than expected for the interval
    - 5m: 10 minutes stale
    - 15m: 20 minutes stale  
    - 1h: 90 minutes stale
    - 1d: 1 day stale
    
    Args:
        ticker_symbol: Stock ticker symbol
        interval: Candle interval ('5m', '15m', '1h', '1d')
        days: Number of days to look back
        db: Database session
    
    Returns:
        DataFrame with OHLCV data or None if not found/stale
    """
    try:
        import pandas as pd
        from src.models import PriceData, Ticker as TickerModel
        
        # Get ticker
        ticker = db.query(TickerModel).filter(TickerModel.symbol == ticker_symbol).first()
        if not ticker:
            return None
        
        # Calculate cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Query price data
        price_records = db.query(PriceData).filter(
            PriceData.ticker_id == ticker.id,
            PriceData.interval == interval,
            PriceData.timestamp >= cutoff_time
        ).order_by(PriceData.timestamp.asc()).all()
        
        if not price_records:
            return None
        
        # ✅ FRESHNESS CHECK: Is the latest candle recent enough?
        latest_timestamp = price_records[-1].timestamp
        now = datetime.now(timezone.utc)
        
        # Make latest_timestamp timezone-aware if needed
        if latest_timestamp.tzinfo is None:
            latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
        
        age_minutes = (now - latest_timestamp).total_seconds() / 60
        
        # Define staleness thresholds by interval
        staleness_threshold = {
            '5m': 10,   # 10 minutes for 5m candles
            '15m': 20,  # 20 minutes for 15m candles
            '1h': 90,   # 90 minutes for 1h candles
            '1d': 1440  # 1 day for daily candles
        }
        
        max_age = staleness_threshold.get(interval, 30)
        
        if age_minutes > max_age:
            print(f"🔄 Cache STALE for {ticker_symbol} ({interval}): latest={latest_timestamp}, age={age_minutes:.1f}min > {max_age}min")
            return None  # Cache is stale, force refresh
        
        print(f"✅ Cache FRESH for {ticker_symbol} ({interval}): latest={latest_timestamp}, age={age_minutes:.1f}min")
        
        # Convert to DataFrame
        data = {
            'Open': [r.open for r in price_records],
            'High': [r.high for r in price_records],
            'Low': [r.low for r in price_records],
            'Close': [r.close for r in price_records],
            'Volume': [r.volume for r in price_records],
            'Dividends': [0.0] * len(price_records),
            'Stock Splits': [0.0] * len(price_records)
        }
        
        df = pd.DataFrame(data, index=[r.timestamp for r in price_records])
        df.index.name = 'Datetime'
        
        return df
        
    except Exception as e:
        print(f"❌ Error retrieving price data from DB: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_price_data_to_db(
    df: 'pd.DataFrame',
    ticker_symbol: str,
    interval: str,
    db: Session
) -> bool:
    """
    Save price data to database with proper UTC timezone handling
    
    Args:
        df: DataFrame with OHLCV data (yfinance format)
        ticker_symbol: Stock ticker symbol
        interval: Candle interval ('5m', '15m', '1h', '1d')
        db: Database session
    
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        from src.models import PriceData, Ticker as TickerModel
        
        # Get or create ticker
        ticker = db.query(TickerModel).filter(TickerModel.symbol == ticker_symbol).first()
        if not ticker:
            ticker = TickerModel(
                symbol=ticker_symbol,
                name=ticker_symbol,
                is_active=True
            )
            db.add(ticker)
            db.flush()
        
        # Convert DataFrame to records
        saved_count = 0
        updated_count = 0
        
        for timestamp, row in df.iterrows():
            # ✅ CRITICAL: Ensure timestamp is UTC
            if timestamp.tzinfo is None:
                # Naive timestamp, assume UTC
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            elif timestamp.tzinfo != timezone.utc:
                # Convert to UTC
                timestamp = timestamp.astimezone(timezone.utc)
            
            # Check if record already exists
            existing = db.query(PriceData).filter(
                PriceData.ticker_id == ticker.id,
                PriceData.ticker_symbol == ticker_symbol,
                PriceData.interval == interval,
                PriceData.timestamp == timestamp
            ).first()
            
            if existing:
                # Update existing record
                existing.open = float(row['Open'])
                existing.high = float(row['High'])
                existing.low = float(row['Low'])
                existing.close = float(row['Close'])
                existing.volume = int(row['Volume'])
                updated_count += 1
            else:
                # Create new record
                price_record = PriceData(
                    ticker_id=ticker.id,
                    ticker_symbol=ticker_symbol,  # ✅ FIX: Add ticker_symbol
                    interval=interval,
                    timestamp=timestamp,  # ✅ Already UTC
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume'])
                )
                db.add(price_record)
                saved_count += 1
        
        db.commit()
        
        if saved_count > 0 or updated_count > 0:
            print(f"💾 Saved {saved_count} new, updated {updated_count} price records for {ticker_symbol} ({interval})")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving price data to DB: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_technical_indicators_to_db(
    ticker_symbol: str,
    interval: str,
    timestamp: datetime,
    indicators: dict,
    db: Session,
    technical_score: Optional[float] = None,
    technical_confidence: Optional[float] = None,
    score_components: Optional[str] = None
) -> Optional[int]:
    """
    Save technical indicators to database with proper UTC timezone handling
    
    Args:
        ticker_symbol: Stock ticker symbol
        interval: Candle interval ('5m', '15m', '1h', '1d')
        timestamp: Timestamp of the indicators (any timezone)
        indicators: Dictionary with indicator values
        db: Database session
        technical_score: Optional technical score
        technical_confidence: Optional confidence score
        score_components: Optional JSON string or dict with score components
    
    Returns:
        Record ID if saved successfully, None otherwise
    """
    try:
        from src.models import TechnicalIndicator
        import json
        
        # ✅ CRITICAL: Ensure timestamp is UTC
        if timestamp.tzinfo is None:
            # Naive timestamp, assume UTC
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        elif timestamp.tzinfo != timezone.utc:
            # Convert to UTC
            timestamp = timestamp.astimezone(timezone.utc)
        
        # ✅ FIX: Convert score_components dict to JSON string
        if score_components is not None and isinstance(score_components, dict):
            score_components = json.dumps(score_components)
        
        # Check if record already exists (TechnicalIndicator uses ticker_symbol directly)
        existing = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.ticker_symbol == ticker_symbol,
            TechnicalIndicator.interval == interval,
            TechnicalIndicator.timestamp == timestamp
        ).first()
        
        if existing:
            # Update existing record
            existing.sma_20 = indicators.get('sma_20')
            existing.sma_50 = indicators.get('sma_50')
            existing.sma_200 = indicators.get('sma_200')
            existing.ema_12 = indicators.get('ema_12')
            existing.ema_26 = indicators.get('ema_26')
            existing.rsi = indicators.get('rsi')
            existing.macd = indicators.get('macd')
            existing.macd_signal = indicators.get('macd_signal')
            existing.macd_histogram = indicators.get('macd_histogram')
            existing.bb_upper = indicators.get('bb_upper')
            existing.bb_middle = indicators.get('bb_middle')
            existing.bb_lower = indicators.get('bb_lower')
            existing.atr = indicators.get('atr')
            existing.adx = indicators.get('adx')
            existing.stoch_k = indicators.get('stoch_k')
            existing.stoch_d = indicators.get('stoch_d')
            existing.obv = indicators.get('obv')
            existing.cci = indicators.get('cci')
            existing.close_price = indicators.get('close_price')
            existing.technical_score = technical_score
            existing.technical_confidence = technical_confidence
            existing.score_components = score_components
            
            db.commit()
            return existing.id
        else:
            # Create new record
            tech_record = TechnicalIndicator(
                ticker_symbol=ticker_symbol,  # ✅ Use ticker_symbol directly
                interval=interval,
                timestamp=timestamp,  # ✅ Already UTC
                sma_20=indicators.get('sma_20'),
                sma_50=indicators.get('sma_50'),
                sma_200=indicators.get('sma_200'),
                ema_12=indicators.get('ema_12'),
                ema_26=indicators.get('ema_26'),
                rsi=indicators.get('rsi'),
                macd=indicators.get('macd'),
                macd_signal=indicators.get('macd_signal'),
                macd_histogram=indicators.get('macd_histogram'),
                bb_upper=indicators.get('bb_upper'),
                bb_middle=indicators.get('bb_middle'),
                bb_lower=indicators.get('bb_lower'),
                atr=indicators.get('atr'),
                adx=indicators.get('adx'),
                stoch_k=indicators.get('stoch_k'),
                stoch_d=indicators.get('stoch_d'),
                obv=indicators.get('obv'),
                cci=indicators.get('cci'),
                close_price=indicators.get('close_price'),
                technical_score=technical_score,
                technical_confidence=technical_confidence,
                score_components=score_components  # ✅ Now a JSON string
            )
            
            db.add(tech_record)
            db.commit()
            
            return tech_record.id
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving technical indicators to DB: {e}")
        import traceback
        traceback.print_exc()
        return None


def cleanup_old_news(db: Session, days_old: int = 7) -> int:
    """
    Remove news older than specified days
    
    Args:
        db: Database session
        days_old: Remove news older than this many days
    
    Returns:
        Number of records deleted
    """
    try:
        from src.models import NewsItem as NewsItemModel
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        deleted_count = db.query(NewsItemModel).filter(
            NewsItemModel.published_at < cutoff_date
        ).delete()
        
        db.commit()
        print(f"🗑️ Cleaned up {deleted_count} old news records (>{days_old} days)")
        return deleted_count
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning up old news: {e}")
        return 0


def get_news_stats(db: Session, ticker_symbol: Optional[str] = None) -> dict:
    """
    Get statistics about news in database
    
    Args:
        db: Database session
        ticker_symbol: Optional ticker to filter by
    
    Returns:
        Dictionary with news statistics
    """
    try:
        from src.models import NewsItem as NewsItemModel, NewsTicker, Ticker as TickerModel, NewsSource
        from sqlalchemy import func
        
        query = db.query(NewsItemModel)
        
        # Filter by ticker if specified
        if ticker_symbol:
            ticker = db.query(TickerModel).filter(TickerModel.symbol == ticker_symbol).first()
            if ticker:
                query = query.join(NewsTicker).filter(NewsTicker.ticker_id == ticker.id)
        
        total_count = query.count()
        
        if total_count == 0:
            return {
                'total_count': 0,
                'tickers': [],
                'sources': [],
                'avg_sentiment': 0.0,
                'oldest_news': None,
                'newest_news': None
            }
        
        # Get unique sources
        sources = db.query(NewsSource.name).distinct().all()
        
        # Get sentiment stats
        avg_sentiment = query.with_entities(func.avg(NewsItemModel.sentiment_score)).scalar()
        
        # Get oldest and newest news timestamps
        oldest = query.with_entities(func.min(NewsItemModel.published_at)).scalar()
        newest = query.with_entities(func.max(NewsItemModel.published_at)).scalar()
        
        # Get tickers (if not filtered by specific ticker)
        if not ticker_symbol:
            tickers = db.query(TickerModel.symbol).join(NewsTicker).join(NewsItemModel).distinct().all()
            ticker_list = [t[0] for t in tickers]
        else:
            ticker_list = [ticker_symbol]
        
        return {
            'total_count': total_count,
            'tickers': ticker_list,
            'sources': [s[0] for s in sources],
            'avg_sentiment': float(avg_sentiment) if avg_sentiment else 0.0,
            'oldest_news': oldest,
            'newest_news': newest
        }
        
    except Exception as e:
        print(f"❌ Error getting news stats: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == "__main__":
    print("✅ Database Helper Functions v2.1")
    print("🔧 Fixed: Preserves ORIGINAL published_at timestamps")
    print("📊 Features:")
    print("  - Duplicate detection by URL")
    print("  - Original timestamp preservation")
    print("  - Price data caching")
    print("  - Technical indicator persistence")
    print("  - Cleanup utilities")
    print("  - News statistics")
