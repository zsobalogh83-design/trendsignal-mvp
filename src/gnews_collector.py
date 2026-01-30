"""
TrendSignal - GNews API Collector
Real-time news collection without 24h delay

Version: 1.0
Date: 2025-01-30
"""

import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional
import time


class GNewsCollector:
    """
    GNews API news collector
    
    Advantages over NewsAPI.org:
    - No 24h delay (real-time)
    - 100 requests/day (free tier)
    - Better for day trading
    """
    
    def __init__(self, api_key: str):
        """
        Initialize GNews collector
        
        Args:
            api_key: GNews API key
        """
        self.api_key = api_key
        self.base_url = "https://gnews.io/api/v4"
        self.request_count = 0
        self.max_requests = 100  # Free tier daily limit
        
    def collect_news(
        self, 
        ticker_symbol: str, 
        max_articles: int = 10,
        language: str = "en"
    ) -> List[Dict]:
        """
        Collect news for a ticker
        
        Args:
            ticker_symbol: Stock ticker (e.g., 'AAPL')
            max_articles: Max number of articles (1-10)
            language: Language code (en, hu, etc.)
        
        Returns:
            List of news items
        """
        if self.request_count >= self.max_requests:
            print(f"  ⚠️ GNews daily limit reached ({self.max_requests} requests)")
            return []
        
        try:
            # Build query - ticker symbol + stock market keywords
            query = f"{ticker_symbol} stock OR {ticker_symbol} shares"
            
            # API endpoint
            url = f"{self.base_url}/search"
            params = {
                "q": query,
                "token": self.api_key,
                "lang": language,
                "max": min(max_articles, 10),  # GNews max is 10 per request
                "sortby": "publishedAt",  # Most recent first
            }
            
            # Make request
            response = requests.get(url, params=params, timeout=10)
            self.request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                print(f"  ✅ GNews: {len(articles)} articles for {ticker_symbol}")
                
                # Convert to standard format
                news_items = []
                for article in articles:
                    news_items.append({
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", "GNews"),
                        "published_at": self._parse_datetime(article.get("publishedAt")),
                        "credibility": 0.80  # Default credibility
                    })
                
                return news_items
                
            elif response.status_code == 403:
                print(f"  ❌ GNews: Invalid API key or quota exceeded")
                return []
            elif response.status_code == 429:
                print(f"  ⚠️ GNews: Rate limit exceeded")
                return []
            else:
                print(f"  ⚠️ GNews: HTTP {response.status_code}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"  ⚠️ GNews: Request timeout")
            return []
        except Exception as e:
            print(f"  ❌ GNews error: {e}")
            return []
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse GNews datetime string to datetime object"""
        try:
            # GNews format: "2025-01-30T14:30:00Z"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.replace(tzinfo=timezone.utc)
        except:
            return datetime.now(timezone.utc)
    
    def reset_daily_count(self):
        """Reset request counter (call this daily)"""
        self.request_count = 0
        print(f"🔄 GNews request counter reset")


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    # Test with your API key
    API_KEY = "422e63bafec92ab1e705b47455a16ce5"
    
    collector = GNewsCollector(API_KEY)
    
    print("🧪 Testing GNews API...")
    print("=" * 60)
    
    # Test AAPL
    news = collector.collect_news("AAPL", max_articles=5)
    
    if news:
        print(f"\n✅ Found {len(news)} articles for AAPL")
        print(f"\nFirst article:")
        print(f"  Title: {news[0]['title']}")
        print(f"  Source: {news[0]['source']}")
        print(f"  Published: {news[0]['published_at']}")
    else:
        print("\n❌ No articles found")
    
    print(f"\n📊 Requests used: {collector.request_count}/100")
