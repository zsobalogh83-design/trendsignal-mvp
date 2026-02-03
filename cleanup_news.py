"""
TrendSignal MVP - News Database Cleanup Script
Removes news records with incorrect timestamps before redeployment
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import get_db, NewsModel
from datetime import datetime, timezone


def cleanup_all_news():
    """Remove ALL news records to start fresh with correct timestamps"""
    db = next(get_db())
    
    try:
        # Count existing records
        total_count = db.query(NewsModel).count()
        print(f"📊 Found {total_count} news records in database")
        
        if total_count == 0:
            print("✅ Database is already clean")
            return
        
        # Show breakdown by ticker
        print("\n📈 Records by ticker:")
        from sqlalchemy import func
        ticker_counts = db.query(
            NewsModel.ticker_symbol,
            func.count(NewsModel.id)
        ).group_by(NewsModel.ticker_symbol).all()
        
        for ticker, count in ticker_counts:
            print(f"  - {ticker}: {count} records")
        
        # Confirm deletion
        print(f"\n⚠️  This will DELETE all {total_count} news records!")
        response = input("Continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled")
            return
        
        # Delete all records
        deleted_count = db.query(NewsModel).delete()
        db.commit()
        
        print(f"\n✅ Successfully deleted {deleted_count} news records")
        print("🔄 Run news collection to populate with correct timestamps")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during cleanup: {e}")
    finally:
        db.close()


def cleanup_news_by_date(cutoff_date: str):
    """
    Remove news records published after a specific date
    Useful for removing only the incorrectly timestamped records
    
    Args:
        cutoff_date: ISO format date string (e.g., '2026-02-03')
    """
    db = next(get_db())
    
    try:
        cutoff = datetime.fromisoformat(cutoff_date).replace(tzinfo=timezone.utc)
        
        # Count records to delete
        count = db.query(NewsModel).filter(
            NewsModel.published_at >= cutoff
        ).count()
        
        print(f"📊 Found {count} news records published after {cutoff_date}")
        
        if count == 0:
            print("✅ No records to delete")
            return
        
        # Show breakdown
        print("\n📈 Records to delete by ticker:")
        from sqlalchemy import func
        ticker_counts = db.query(
            NewsModel.ticker_symbol,
            func.count(NewsModel.id)
        ).filter(
            NewsModel.published_at >= cutoff
        ).group_by(NewsModel.ticker_symbol).all()
        
        for ticker, cnt in ticker_counts:
            print(f"  - {ticker}: {cnt} records")
        
        # Confirm deletion
        print(f"\n⚠️  This will DELETE {count} news records!")
        response = input("Continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled")
            return
        
        # Delete records
        deleted_count = db.query(NewsModel).filter(
            NewsModel.published_at >= cutoff
        ).delete()
        db.commit()
        
        print(f"\n✅ Successfully deleted {deleted_count} news records")
        print("🔄 Run news collection to populate with correct timestamps")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during cleanup: {e}")
    finally:
        db.close()


def show_news_stats():
    """Display current news database statistics"""
    db = next(get_db())
    
    try:
        from sqlalchemy import func
        
        total_count = db.query(NewsModel).count()
        print(f"\n📊 News Database Statistics")
        print(f"{'='*50}")
        print(f"Total records: {total_count}")
        
        if total_count == 0:
            print("✅ Database is empty")
            return
        
        # By ticker
        print("\n📈 Records by ticker:")
        ticker_counts = db.query(
            NewsModel.ticker_symbol,
            func.count(NewsModel.id)
        ).group_by(NewsModel.ticker_symbol).all()
        
        for ticker, count in ticker_counts:
            print(f"  - {ticker}: {count} records")
        
        # By source
        print("\n📰 Records by source:")
        source_counts = db.query(
            NewsModel.source,
            func.count(NewsModel.id)
        ).group_by(NewsModel.source).all()
        
        for source, count in source_counts:
            print(f"  - {source}: {count} records")
        
        # Date range
        oldest = db.query(func.min(NewsModel.published_at)).scalar()
        newest = db.query(func.max(NewsModel.published_at)).scalar()
        
        print(f"\n📅 Date range:")
        print(f"  Oldest: {oldest}")
        print(f"  Newest: {newest}")
        
        # Average sentiment
        avg_sentiment = db.query(func.avg(NewsModel.sentiment_score)).scalar()
        print(f"\n📊 Average sentiment: {avg_sentiment:.4f}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("🧹 TrendSignal News Database Cleanup Utility")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python cleanup_news.py stats              # Show database statistics")
        print("  python cleanup_news.py all                # Delete all news records")
        print("  python cleanup_news.py date YYYY-MM-DD    # Delete records after date")
        print("\nExamples:")
        print("  python cleanup_news.py stats")
        print("  python cleanup_news.py all")
        print("  python cleanup_news.py date 2026-02-03")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'stats':
        show_news_stats()
    elif command == 'all':
        cleanup_all_news()
    elif command == 'date' and len(sys.argv) >= 3:
        cutoff_date = sys.argv[2]
        cleanup_news_by_date(cutoff_date)
    else:
        print("❌ Invalid command. Use 'stats', 'all', or 'date YYYY-MM-DD'")
        sys.exit(1)
