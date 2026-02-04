"""
TrendSignal - Ticker Data Migration
Migrate hardcoded ticker keywords and metadata to database

Usage:
    python migrate_ticker_data.py
"""

import sys
import json
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))

from database import SessionLocal
from models import Ticker
from ticker_keywords import (
    TICKER_INFO, 
    TICKER_KEYWORDS, 
    TICKER_SENTIMENT_KEYWORDS,
    get_all_relevant_keywords
)

print("=" * 80)
print("TICKER DATA MIGRATION - ticker_keywords.py → Database")
print("=" * 80)
print()

def migrate_ticker_data():
    """Migrate ticker metadata and keywords to database"""
    
    db = SessionLocal()
    
    try:
        migrated_count = 0
        updated_count = 0
        
        for symbol, info in TICKER_INFO.items():
            print(f"\n📊 Processing {symbol}...")
            
            # Get or create ticker
            ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
            
            if not ticker:
                print(f"  ➕ Creating new ticker: {symbol}")
                ticker = Ticker(
                    symbol=symbol,
                    name=info.get('name', ''),
                    is_active=True
                )
                db.add(ticker)
                migrated_count += 1
            else:
                print(f"  🔄 Updating existing ticker: {symbol}")
                updated_count += 1
            
            # ===== BASIC METADATA =====
            ticker.name = info.get('name', ticker.name)
            ticker.market = info.get('market', ticker.market)
            ticker.sector = info.get('sector')
            ticker.industry = info.get('industry')
            ticker.currency = info.get('currency')
            
            # Language detection
            ticker.primary_language = 'hu' if symbol.endswith('.BD') else 'en'
            
            # ===== RELEVANCE KEYWORDS =====
            # Flatten all keywords from TICKER_KEYWORDS
            ticker_kw = TICKER_KEYWORDS.get(symbol, {})
            all_keywords = []
            
            for key, values in ticker_kw.items():
                if isinstance(values, list):
                    all_keywords.extend(values)
            
            # Remove duplicates and store as JSON
            unique_keywords = list(set(all_keywords))
            ticker.relevance_keywords = json.dumps(unique_keywords, ensure_ascii=False)
            
            print(f"     Keywords: {len(unique_keywords)} items")
            print(f"     Sample: {', '.join(unique_keywords[:5])}...")
            
            # ===== SENTIMENT KEYWORDS =====
            sentiment_kw = TICKER_SENTIMENT_KEYWORDS.get(symbol, {})
            
            positive_kw = sentiment_kw.get('positive', [])
            negative_kw = sentiment_kw.get('negative', [])
            
            ticker.sentiment_keywords_positive = json.dumps(positive_kw, ensure_ascii=False)
            ticker.sentiment_keywords_negative = json.dumps(negative_kw, ensure_ascii=False)
            
            print(f"     Sentiment: +{len(positive_kw)} / -{len(negative_kw)} keywords")
            
            # ===== NEWS SOURCES (market-based defaults) =====
            if symbol.endswith('.BD'):
                # Hungarian tickers
                preferred_sources = [
                    'portfolio.hu_befektetes',
                    'portfolio.hu_bank',
                    'portfolio.hu_gazdasag',
                    'hvg.hu',
                    'index.hu'
                ]
                blocked_sources = []  # None by default
            else:
                # US tickers
                preferred_sources = [
                    'yahoo_finance',
                    'finnhub',
                    'reuters',
                    'bloomberg'
                ]
                blocked_sources = []
            
            ticker.news_sources_preferred = json.dumps(preferred_sources)
            ticker.news_sources_blocked = json.dumps(blocked_sources)
            
            print(f"     News sources: {len(preferred_sources)} preferred")
        
        # Commit all changes
        db.commit()
        
        print()
        print("=" * 80)
        print("MIGRATION SUMMARY:")
        print(f"  New tickers created: {migrated_count}")
        print(f"  Existing tickers updated: {updated_count}")
        print(f"  Total tickers: {migrated_count + updated_count}")
        print("=" * 80)
        print()
        
        # Display sample ticker
        sample_ticker = db.query(Ticker).filter(Ticker.symbol == 'OTP.BD').first()
        if sample_ticker:
            print("📋 Sample Ticker (OTP.BD):")
            print(f"  Name: {sample_ticker.name}")
            print(f"  Market: {sample_ticker.market}")
            print(f"  Language: {sample_ticker.primary_language}")
            print(f"  Sector: {sample_ticker.sector}")
            print(f"  Currency: {sample_ticker.currency}")
            
            if sample_ticker.relevance_keywords:
                keywords = json.loads(sample_ticker.relevance_keywords)
                print(f"  Relevance Keywords: {len(keywords)} items")
                print(f"    Sample: {', '.join(keywords[:5])}...")
            
            if sample_ticker.sentiment_keywords_positive:
                pos_kw = json.loads(sample_ticker.sentiment_keywords_positive)
                print(f"  Positive Keywords: {len(pos_kw)} items")
                print(f"    Sample: {', '.join(pos_kw[:3])}...")
        
        print()
        print("✅ Migration completed successfully!")
        print()
        print("💡 Next steps:")
        print("   1. Verify data: SELECT * FROM tickers WHERE symbol = 'OTP.BD';")
        print("   2. Test keyword loading in news_collector.py")
        print("   3. Update frontend UI to display/edit these fields")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    
    finally:
        db.close()

if __name__ == "__main__":
    migrate_ticker_data()
