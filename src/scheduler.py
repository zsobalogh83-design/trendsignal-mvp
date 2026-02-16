"""
TrendSignal MVP - Scheduler Module
Automated signal generation during trading hours

Version: 1.0
Date: 2025-02-04
"""

import sys
import os  # 🆕 HIÁNYZOTT!
from pathlib import Path
from datetime import datetime, time
from typing import List
import pytz

# Add src to path
src_path = Path(__file__).parent / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))

from config import get_config
from main import run_batch_analysis


# ==========================================
# MARKET HOURS CHECKING
# ==========================================

def is_bet_open() -> bool:
    """Check if Budapest Stock Exchange is open"""
    config = get_config()
    
    # Get current time in Budapest timezone
    bet_tz = pytz.timezone(config.bet_timezone)
    now = datetime.now(bet_tz)
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Parse market hours
    open_time = datetime.strptime(config.bet_market_open, "%H:%M").time()
    close_time = datetime.strptime(config.bet_market_close, "%H:%M").time()
    current_time = now.time()
    
    # Check if current time is within market hours
    return open_time <= current_time <= close_time


def is_us_market_open() -> bool:
    """Check if US markets (NYSE/NASDAQ) are open"""
    config = get_config()
    
    # Get current time in US Eastern timezone
    us_tz = pytz.timezone(config.us_timezone)
    now = datetime.now(us_tz)
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Parse market hours
    open_time = datetime.strptime(config.us_market_open, "%H:%M").time()
    close_time = datetime.strptime(config.us_market_close, "%H:%M").time()
    current_time = now.time()
    
    # Check if current time is within market hours
    return open_time <= current_time <= close_time


def get_active_tickers() -> List[dict]:
    """
    Get list of tickers for markets that are currently open
    READS FROM DATABASE (not config.all_tickers)
    
    Returns:
        List of ticker dictionaries for active markets
    """
    # Import database components
    from database import SessionLocal
    from models import Ticker
    
    bet_open = is_bet_open()
    us_open = is_us_market_open()
    
    if not bet_open and not us_open:
        print("⏸️  No markets currently open")
        return []
    
    # Query database for active tickers
    db = SessionLocal()
    try:
        active_tickers = []
        
        # Get all active tickers from database
        tickers = db.query(Ticker).filter(Ticker.is_active == True).all()
        
        # Filter by market hours
        for ticker in tickers:
            # BÉT/Hungarian market
            if bet_open and ticker.market in ['HU', 'BÉT', 'BET']:
                active_tickers.append({
                    'symbol': ticker.symbol,
                    'name': ticker.name,
                    'market': 'BET'  # Normalize to BET for consistency
                })
            
            # US market
            elif us_open and ticker.market == 'US':
                active_tickers.append({
                    'symbol': ticker.symbol,
                    'name': ticker.name,
                    'market': 'US'
                })
        
        # Log results
        if bet_open:
            bet_count = len([t for t in active_tickers if t['market'] == 'BET'])
            print(f"🟢 BÉT market is OPEN - {bet_count} active tickers")
        
        if us_open:
            us_count = len([t for t in active_tickers if t['market'] == 'US'])
            print(f"🟢 US market is OPEN - {us_count} active tickers")
        
        return active_tickers
        
    finally:
        db.close()


# ==========================================
# SCHEDULED SIGNAL GENERATION
# ==========================================

def generate_signals_for_active_markets():
    """
    Generate signals for all tickers in currently open markets
    This function is called by APScheduler every 15 minutes
    """
    print("\n" + "=" * 70)
    print(f"🔄 SCHEDULED SIGNAL REFRESH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Get tickers for active markets
    active_tickers = get_active_tickers()
    
    if not active_tickers:
        print("⏸️  Skipping - no markets open")
        return
    
    print(f"\n📊 Generating signals for {len(active_tickers)} tickers:")
    for ticker in active_tickers:
        print(f"  - {ticker['symbol']} ({ticker['name']})")
    print()
    
    # Run batch analysis
    try:
        signals = run_batch_analysis(
            tickers=active_tickers,
            use_db=True
        )
        
        # 🆕 Save signals to database
        try:
            # Import database components
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
            from signals_api import save_signal_to_db
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
            from database import SessionLocal
            
            db = SessionLocal()
            try:
                saved_count = 0
                for signal in signals:
                    if save_signal_to_db(signal, db):
                        saved_count += 1
                print(f"💾 Saved {saved_count}/{len(signals)} signals to database")
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️ Database save failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 70)
        print(f"✅ Scheduled refresh complete - Generated {len(signals)} signals")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Scheduled refresh failed: {e}")
        import traceback
        traceback.print_exc()


# ==========================================
# MANUAL TRIGGER (for API endpoint)
# ==========================================

def trigger_signal_refresh_now():
    """
    Manually trigger signal generation for active markets
    Used by API endpoint for on-demand refresh
    
    Returns:
        dict with status and message
    """
    print("\n" + "=" * 70)
    print(f"🔘 MANUAL SIGNAL REFRESH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Get tickers for active markets
    active_tickers = get_active_tickers()
    
    if not active_tickers:
        return {
            "status": "skipped",
            "message": "No markets currently open",
            "signals_generated": 0
        }
    
    print(f"\n📊 Generating signals for {len(active_tickers)} tickers:")
    for ticker in active_tickers:
        print(f"  - {ticker['symbol']} ({ticker['name']})")
    print()
    
    # Run batch analysis
    try:
        signals = run_batch_analysis(
            tickers=active_tickers,
            use_db=True
        )
        
        # 🆕 Save signals to database
        try:
            # Import database components
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
            from signals_api import save_signal_to_db
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
            from database import SessionLocal
            
            db = SessionLocal()
            try:
                saved_count = 0
                for signal in signals:
                    if save_signal_to_db(signal, db):
                        saved_count += 1
                print(f"💾 Saved {saved_count}/{len(signals)} signals to database")
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️ Database save failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 70)
        print(f"✅ Manual refresh complete - Generated {len(signals)} signals")
        print("=" * 70)
        
        return {
            "status": "success",
            "message": f"Generated {len(signals)} signals",
            "signals_generated": len(signals),
            "tickers": [t['symbol'] for t in active_tickers]
        }
        
    except Exception as e:
        error_msg = f"Signal refresh failed: {str(e)}"
        print(f"\n❌ {error_msg}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": error_msg,
            "signals_generated": 0
        }


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    print("Testing scheduler functions...")
    print()
    
    # Test market hours checking
    print("🔍 Market Status Check:")
    print(f"  BÉT Open: {is_bet_open()}")
    print(f"  US Open:  {is_us_market_open()}")
    print()
    
    # Test active tickers
    print("📋 Active Tickers:")
    active = get_active_tickers()
    if active:
        for t in active:
            print(f"  - {t['symbol']} ({t['market']})")
    else:
        print("  None (markets closed)")
    print()
    
    # Test manual trigger
    print("🔘 Testing Manual Trigger:")
    result = trigger_signal_refresh_now()
    print(f"\nResult: {result}")
