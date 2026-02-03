"""
TrendSignal - Finnhub API Collector
High-quality financial news with generous free tier

Version: 1.0
Date: 2025-02-03
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional


class FinnhubCollector:
    """
    Finnhub API news collector
    
    Advantages:
    - FREE tier: 60 requests/minute = 3600/hour
    - High-quality financial news
    - Real-time updates
    - Stock-specific news
    - Reliable API
    
    Get free API key: https://finnhub.io/register
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Finnhub collector
        
        Args:
            api_key: Finnhub API key (get from https://finnhub.io/register)
        """
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.request_count = 0
        print("✅ Finnhub collector ready (60 req/min, real-time)")
    
    def collect_news(
        self, 
        ticker_symbol: str,
        lookback_days: int = 7,
        max_articles: int = 50
    ) -> List[Dict]:
        """
        Collect company news for a ticker
        
        Args:
            ticker_symbol: Stock ticker (e.g., 'AAPL')
            lookback_days: Days to look back (max 365)
            max_articles: Max articles to return (Finnhub returns ~50)
        
        Returns:
            List of news items
        """
        try:
            # Calculate date range
            to_date = datetime.now(timezone.utc)
            from_date = to_date - timedelta(days=lookback_days)
            
            # Format dates for API (YYYY-MM-DD)
            from_str = from_date.strftime('%Y-%m-%d')
            to_str = to_date.strftime('%Y-%m-%d')
            
            # API endpoint
            url = f"{self.base_url}/company-news"
            params = {
                "symbol": ticker_symbol,
                "from": from_str,
                "to": to_str,
                "token": self.api_key
            }
            
            # Make request
            response = requests.get(url, params=params, timeout=10)
            self.request_count += 1
            
            if response.status_code == 200:
                articles = response.json()
                
                if not articles:
                    print(f"  ℹ️ Finnhub: No news found for {ticker_symbol}")
                    return []
                
                news_items = []
                
                for article in articles[:max_articles]:
                    # Parse Unix timestamp to datetime
                    timestamp = article.get('datetime', 0)
                    published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    
                    news_items.append({
                        "title": article.get('headline', ''),
                        "description": article.get('summary', ''),
                        "url": article.get('url', ''),
                        "source": article.get('source', 'Finnhub'),
                        "published_at": published_at,
                        "credibility": 0.85  # Finnhub high credibility
                    })
                
                print(f"  ✅ Finnhub: {len(news_items)} articles for {ticker_symbol}")
                return news_items
                
            elif response.status_code == 401:
                print(f"  ❌ Finnhub: Invalid API key")
                return []
            elif response.status_code == 429:
                print(f"  ⚠️ Finnhub: Rate limit exceeded (60/min)")
                return []
            else:
                print(f"  ⚠️ Finnhub: HTTP {response.status_code}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"  ⚠️ Finnhub: Request timeout")
            return []
        except Exception as e:
            print(f"  ❌ Finnhub error for {ticker_symbol}: {e}")
            return []


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    import os
    
    # Test with your API key
    API_KEY = os.getenv("FINNHUB_API_KEY", "YOUR_KEY_HERE")
    
    if API_KEY == "YOUR_KEY_HERE":
        print("⚠️ Please set FINNHUB_API_KEY environment variable or replace YOUR_KEY_HERE")
        print("   Get free API key: https://finnhub.io/register")
        exit(1)
    
    print("🧪 Testing Finnhub API Collector...")
    print("=" * 60)
    
    collector = FinnhubCollector(API_KEY)
    
    # Test with multiple tickers
    tickers = ["AAPL", "MSFT", "TSLA"]
    
    for ticker in tickers:
        print(f"\n📰 Collecting news for {ticker}...")
        news = collector.collect_news(ticker, lookback_days=3, max_articles=5)
        
        if news:
            print(f"\n✅ Found {len(news)} articles")
            print(f"\nFirst article:")
            print(f"  Title: {news[0]['title']}")
            print(f"  Source: {news[0]['source']}")
            print(f"  Published: {news[0]['published_at']}")
            print(f"  URL: {news[0]['url'][:60]}...")
        else:
            print(f"\n⚠️ No articles found for {ticker}")
        
        print("-" * 60)
    
    print(f"\n📊 Total requests used: {collector.request_count}")
