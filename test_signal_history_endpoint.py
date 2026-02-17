"""
Test script for /api/v1/signals/history endpoint
Run this after starting the API server to verify the endpoint works correctly
"""

import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1/signals"

def test_endpoint(description, url, expected_keys=None):
    """Test a single endpoint and validate response"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"URL: {url}")
    print('-'*60)
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"Total signals: {data.get('total', 'N/A')}")
            print(f"Signals returned: {len(data.get('signals', []))}")
            
            if expected_keys:
                for key in expected_keys:
                    if key in data:
                        print(f"✓ Key '{key}' present")
                    else:
                        print(f"✗ Key '{key}' MISSING!")
            
            # Show first signal if available
            if data.get('signals') and len(data['signals']) > 0:
                signal = data['signals'][0]
                print(f"\nFirst signal:")
                print(f"  Ticker: {signal['ticker_symbol']}")
                print(f"  Decision: {signal['decision']} ({signal['strength']})")
                print(f"  Score: {signal['combined_score']:.2f}")
                print(f"  Date: {signal['created_at']}")
                print(f"  Status: {signal['status']}")
            
            return data
        else:
            print(f"❌ FAILED")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return None


def main():
    print("\n" + "="*60)
    print("SIGNAL HISTORY ENDPOINT TEST SUITE")
    print("="*60)
    
    # Test 1: Basic history call (no filters)
    test_endpoint(
        "Get all historical signals",
        f"{BASE_URL}/history",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 2: Date range filter (last 30 days)
    today = datetime.now()
    from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    test_endpoint(
        f"Get signals from last 30 days",
        f"{BASE_URL}/history?from_date={from_date}&to_date={to_date}",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 3: Filter by ticker
    test_endpoint(
        "Get signals for AAPL only",
        f"{BASE_URL}/history?ticker_symbols=AAPL",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 4: Filter by decision
    test_endpoint(
        "Get BUY signals only",
        f"{BASE_URL}/history?decisions=BUY",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 5: Filter by strength
    test_endpoint(
        "Get STRONG signals only",
        f"{BASE_URL}/history?strengths=STRONG",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 6: Multiple filters combined
    test_endpoint(
        "Get STRONG BUY signals for AAPL",
        f"{BASE_URL}/history?ticker_symbols=AAPL&decisions=BUY&strengths=STRONG",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 7: Multiple tickers
    test_endpoint(
        "Get signals for AAPL, MSFT, TSLA",
        f"{BASE_URL}/history?ticker_symbols=AAPL&ticker_symbols=MSFT&ticker_symbols=TSLA",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 8: Score range filter
    test_endpoint(
        "Get signals with score between 30 and 70",
        f"{BASE_URL}/history?min_score=30&max_score=70",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 9: Pagination
    test_endpoint(
        "Get first 10 signals (pagination)",
        f"{BASE_URL}/history?limit=10&offset=0",
        expected_keys=['signals', 'total', 'filters_applied']
    )
    
    # Test 10: Invalid date format (should fail)
    test_endpoint(
        "Invalid date format (should return 400)",
        f"{BASE_URL}/history?from_date=2025-13-45",  # Invalid date
        expected_keys=None
    )
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60)
    
    # Compare with regular signals endpoint
    print("\n\nCOMPARISON: /history vs regular /signals")
    print("="*60)
    
    print("\nRegular endpoint (active signals):")
    active = requests.get(f"{BASE_URL}?status=active").json()
    print(f"  Active signals: {active.get('total', 0)}")
    
    print("\nHistory endpoint (expired/archived):")
    history = requests.get(f"{BASE_URL}/history").json()
    print(f"  Historical signals: {history.get('total', 0)}")
    
    print("\n✅ Tests completed!")


if __name__ == "__main__":
    main()
