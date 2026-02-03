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
    
    Args:
        news_item: NewsItem object with original published_at
        ticker_symbol: Stock ticker symbol
        db: Database session
    
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        from src.database import NewsModel
        
        # Check for duplicates by URL
        existing = db.query(NewsModel).filter(
            NewsModel.url == news_item.url,
            NewsModel.ticker_symbol == ticker_symbol
        ).first()
        
        if existing:
            # Update if sentiment changed significantly
            if abs(existing.sentiment_score - news_item.sentiment_score) > 0.1:
                existing.sentiment_score = news_item.sentiment_score
                existing.sentiment_label = news_item.sentiment_label
                existing.updated_at = datetime.now(timezone.utc)
                db.commit()
                return True
            return False  # Already exists, no update needed
        
        # Create new record with ORIGINAL published_at timestamp
        news_record = NewsModel(
            ticker_symbol=ticker_symbol,
            title=news_item.title,
            description=news_item.description,
            url=news_item.url,
            source=news_item.source,
            published_at=news_item.published_at,  # Ã¢Å“â€¦ CRITICAL FIX: Use original timestamp
            sentiment_score=news_item.sentiment_score,
            sentiment_label=news_item.sentiment_label,
            credibility=news_item.credibility
        )
        
        db.add(news_record)
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Ã¢ÂÅ’ Error saving news to DB: {e}")
        return False


def get_recent_news_from_db(
    ticker_symbol: str,
    db: Session,
    lookback_hours: int = 24,
    min_credibility: float = 0.0
) -> List[NewsItem]:
    """
    Retrieve recent news from database with original timestamps
    
    Args:
        ticker_symbol: Stock ticker symbol
        db: Database session
        lookback_hours: Hours to look back (default: 24h)
        min_credibility: Minimum credibility score filter
    
    Returns:
        List of NewsItem objects with ORIGINAL published_at timestamps
    """
    try:
        from src.database import NewsModel
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        news_records = db.query(NewsModel).filter(
            NewsModel.ticker_symbol == ticker_symbol,
            NewsModel.published_at >= cutoff_time,  # Ã¢Å“â€¦ Filter by ORIGINAL timestamp
            NewsModel.credibility >= min_credibility
        ).order_by(NewsModel.published_at.desc()).all()
        
        news_items = []
        for news_record in news_records:
            news_item = NewsItem(
                title=news_record.title,
                description=news_record.description,
                url=news_record.url,
                published_at=news_record.published_at,  # Ã¢Å“â€¦ Use ORIGINAL timestamp from DB
                source=news_record.source,
                sentiment_score=news_record.sentiment_score,
                sentiment_confidence=0.0,  # Not stored in DB yet
                sentiment_label=news_record.sentiment_label,
                credibility=news_record.credibility
            )
            news_items.append(news_item)
        
        return news_items
        
    except Exception as e:
        print(f"Ã¢ÂÅ’ Error retrieving news from DB: {e}")
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
        from src.database import NewsModel
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        deleted_count = db.query(NewsModel).filter(
            NewsModel.published_at < cutoff_date
        ).delete()
        
        db.commit()
        print(f"Ã°Å¸â€”â€˜Ã¯Â¸Â Cleaned up {deleted_count} old news records (>{days_old} days)")
        return deleted_count
        
    except Exception as e:
        db.rollback()
        print(f"Ã¢ÂÅ’ Error cleaning up old news: {e}")
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
        from src.database import NewsModel
        from sqlalchemy import func
        
        query = db.query(NewsModel)
        if ticker_symbol:
            query = query.filter(NewsModel.ticker_symbol == ticker_symbol)
        
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
        
        # Get unique tickers and sources
        tickers = db.query(NewsModel.ticker_symbol).distinct().all()
        sources = db.query(NewsModel.source).distinct().all()
        
        # Get sentiment stats
        avg_sentiment = db.query(func.avg(NewsModel.sentiment_score)).scalar()
        
        # Get oldest and newest news timestamps
        oldest = db.query(func.min(NewsModel.published_at)).scalar()
        newest = db.query(func.max(NewsModel.published_at)).scalar()
        
        return {
            'total_count': total_count,
            'tickers': [t[0] for t in tickers],
            'sources': [s[0] for s in sources],
            'avg_sentiment': float(avg_sentiment) if avg_sentiment else 0.0,
            'oldest_news': oldest,
            'newest_news': newest
        }
        
    except Exception as e:
        print(f"Ã¢ÂÅ’ Error getting news stats: {e}")
        return {}


if __name__ == "__main__":
    print("Ã¢Å“â€¦ Database Helper Functions v2.0")
    print("Ã°Å¸â€Â§ Fixed: Preserves ORIGINAL published_at timestamps")
    print("Ã°Å¸â€œÅ  Features:")
    print("  - Duplicate detection by URL")
    print("  - Original timestamp preservation")
    print("  - Cleanup utilities")
    print("  - News statistics")