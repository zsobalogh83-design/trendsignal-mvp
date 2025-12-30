"""
Test script to generate and verify signals
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_generate_signals():
    """Generate signals via API"""
    print("=" * 60)
    print("🎯 Generating Signals via API")
    print("=" * 60)
    print()
    
    url = f"{BASE_URL}/api/v1/signals/generate"
    
    print(f"POST {url}")
    print("Waiting for signal generation...")
    print()
    
    try:
        response = requests.post(url, timeout=300)  # 5 min timeout
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print()
            print(f"Generated: {data.get('message')}")
            print(f"Saved to DB: {data.get('saved')}")
            print(f"Tickers: {', '.join(data.get('tickers', []))}")
            print()
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_get_signals():
    """Get signals from API"""
    print("=" * 60)
    print("📊 Fetching Signals from Database")
    print("=" * 60)
    print()
    
    url = f"{BASE_URL}/api/v1/signals"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            signals = data.get('signals', [])
            
            print(f"✅ Found {len(signals)} signals in database")
            print()
            
            for signal in signals:
                emoji = "🟢" if "BUY" in signal['decision'] else "🔴" if "SELL" in signal['decision'] else "⚪"
                print(f"{emoji} {signal['ticker_symbol']:8s} | "
                      f"{signal['strength']:8s} {signal['decision']:4s} | "
                      f"Score: {signal['combined_score']:+6.1f} | "
                      f"Conf: {signal['overall_confidence']:.0%}")
            
            print()
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_database_status():
    """Check database status"""
    print("=" * 60)
    print("🗄️  Database Status")
    print("=" * 60)
    print()
    
    url = f"{BASE_URL}/api/v1/database/status"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('statistics', {})
            
            print(f"Status:         {data.get('status')}")
            print(f"Tickers:        {stats.get('tickers')}")
            print(f"Signals:        {stats.get('signals')}")
            print(f"Active Signals: {stats.get('active_signals')}")
            print(f"News Items:     {stats.get('news_items')}")
            print(f"News Sources:   {stats.get('news_sources')}")
            print()
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TrendSignal API Test Suite")
    print()
    
    # Test 1: Database status
    test_database_status()
    
    # Test 2: Generate signals
    print("⏳ This may take 2-3 minutes (downloading price data + analysis)...")
    print()
    success = test_generate_signals()
    
    if success:
        print()
        
        # Test 3: Get signals
        test_get_signals()
        
        print()
        print("=" * 60)
        print("✅ ALL TESTS COMPLETED!")
        print("=" * 60)
        
        # Final status check
        print()
        test_database_status()
    else:
        print()
        print("❌ Signal generation failed")
