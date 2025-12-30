"""
Initialize TrendSignal Database
Creates all tables and optionally seeds initial data
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from database import Base, engine, SessionLocal
from models import *

def init_database():
    """Create all database tables"""
    print("=" * 60)
    print("🗄️  TrendSignal Database Initialization")
    print("=" * 60)
    print()
    
    print("📋 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")
    print()
    
    # List created tables
    print("📊 Created tables:")
    for table in Base.metadata.sorted_tables:
        print(f"   - {table.name}")
    print()

def seed_initial_data():
    """Seed database with initial data"""
    db = SessionLocal()
    
    try:
        print("🌱 Seeding initial data...")
        
        # Add news sources
        sources = [
            NewsSource(
                name="NewsAPI",
                type="api",
                url="https://newsapi.org/v2",
                credibility_weight=0.85,
                is_enabled=True
            ),
            NewsSource(
                name="Alpha Vantage News",
                type="api",
                url="https://www.alphavantage.co",
                credibility_weight=0.80,
                is_enabled=True
            ),
            NewsSource(
                name="Yahoo Finance",
                type="api",
                url="https://finance.yahoo.com",
                credibility_weight=0.75,
                is_enabled=True
            ),
        ]
        
        db.add_all(sources)
        db.commit()
        print(f"   ✅ Added {len(sources)} news sources")
        
        # Add sample tickers
        tickers = [
            Ticker(symbol="AAPL", name="Apple Inc.", market="NASDAQ", priority="high", is_active=True),
            Ticker(symbol="MSFT", name="Microsoft Corporation", market="NASDAQ", priority="high", is_active=True),
            Ticker(symbol="GOOGL", name="Alphabet Inc.", market="NASDAQ", priority="medium", is_active=True),
            Ticker(symbol="TSLA", name="Tesla Inc.", market="NASDAQ", priority="medium", is_active=True),
            Ticker(symbol="OTP.BD", name="OTP Bank Nyrt.", market="BET", priority="high", is_active=True),
            Ticker(symbol="MOL.BD", name="MOL Magyar Olaj- és Gázipari Nyrt.", market="BET", priority="medium", is_active=True),
        ]
        
        db.add_all(tickers)
        db.commit()
        print(f"   ✅ Added {len(tickers)} sample tickers")
        
        print()
        print("✅ Database seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

def check_database():
    """Check database status"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("📊 Database Status")
        print("=" * 60)
        print()
        
        # Count records
        ticker_count = db.query(Ticker).count()
        source_count = db.query(NewsSource).count()
        news_count = db.query(NewsItem).count()
        signal_count = db.query(Signal).count()
        
        print(f"Tickers:      {ticker_count}")
        print(f"News Sources: {source_count}")
        print(f"News Items:   {news_count}")
        print(f"Signals:      {signal_count}")
        print()
        
        if ticker_count > 0:
            print("Sample Tickers:")
            tickers = db.query(Ticker).limit(5).all()
            for ticker in tickers:
                status = "✅" if ticker.is_active else "❌"
                print(f"   {status} {ticker.symbol:8s} - {ticker.name}")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        # Initialize and seed
        init_database()
        seed_initial_data()
        check_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "--check":
        # Just check status
        check_database()
    else:
        # Just initialize
        init_database()
        print()
        print("💡 To seed initial data, run:")
        print("   python init_db.py --seed")
        print()
        print("💡 To check database status, run:")
        print("   python init_db.py --check")
