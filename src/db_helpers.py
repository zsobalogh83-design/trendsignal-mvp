"""
TrendSignal MVP - Database Helper Functions
Utility functions for database operations with proper timestamp handling
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
    print("✅ Database Helper Functions v2.0")
    print("🔧 Fixed: Preserves ORIGINAL published_at timestamps")
    print("📊 Features:")
    print("  - Duplicate detection by URL")
    print("  - Original timestamp preservation")
    print("  - Cleanup utilities")
    print("  - News statistics")
