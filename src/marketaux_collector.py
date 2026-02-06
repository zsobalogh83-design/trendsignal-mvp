"""
TrendSignal - Marketaux API Collector
High-quality financial news with built-in AI sentiment analysis

Version: 1.0
Date: 2026-02-06
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional


class MarketauxCollector:
    """
    Marketaux API news collector
    
    Advantages:
    - FREE tier: 100 requests/day
    - 5,000+ news sources globally
    - Built-in AI sentiment analysis
    - Real-time updates
    - Ticker-specific filtering
    - Highlight extraction (entity mentions)
    - 30+ languages
    
    Get free API key: https://www.marketaux.com
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Marketaux collector
        
        Args:
            api_key: Marketaux API token
        """
        self.api_key = api_key
        self.base_url = "https://api.marketaux.com/v1"
        self.request_count = 0
        print("✅ Marketaux collector ready (100 req/day, AI sentiment)")
    
    def collect_news(
        self, 
        ticker_symbol: str,
        lookback_days: int = 3,
        max_articles: int = 20
    ) -> List[Dict]:
        """
        Collect company news for a ticker with AI sentiment
        
        Args:
            ticker_symbol: Stock ticker (e.g., 'AAPL')
            lookback_days: Days to look back (default: 3)
            max_articles: Max articles to return
        
        Returns:
            List of news items with built-in sentiment
        """
        try:
            # Calculate date range
            to_date = datetime.now(timezone.utc)
            from_date = to_date - timedelta(days=lookback_days)
            
            # Format for API (ISO 8601)
            from_str = from_date.strftime('%Y-%m-%dT%H:%M')
            
            # API endpoint
            url = f"{self.base_url}/news/all"
            
            params = {
                'api_token': self.api_key,
                'symbols': ticker_symbol,
                'filter_entities': 'true',  # Only news mentioning the ticker
                'language': 'en',
                'published_after': from_str,
                'limit': max_articles
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            self.request_count += 1
            
            news_items = []
            
            for article in data.get('data', []):
                # Parse publication date (ISO format)
                published_str = article.get('published_at', '')
                if published_str:
                    # Remove 'Z' and parse
                    published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                else:
                    published_at = datetime.now(timezone.utc)
                
                # Extract ticker-specific sentiment from entities
                sentiment_score = 0.0
                for entity in article.get('entities', []):
                    if entity.get('symbol') == ticker_symbol:
                        sentiment_score = entity.get('sentiment_score', 0.0)
                        break
                
                # Clean description
                description = article.get('description', '') or article.get('snippet', '')
                
                news_items.append({
                    "title": article.get('title', ''),
                    "description": description,
                    "url": article.get('url', ''),
                    "source": article.get('source', 'Marketaux'),
                    "published_at": published_at,
                    "sentiment_score": sentiment_score,  # ✅ Built-in AI sentiment!
                    "credibility": 0.88  # High credibility (5000+ sources)
                })
            
            print(f"  ✅ Marketaux: {len(news_items)} articles for {ticker_symbol}")
            return news_items
            
        except Exception as e:
            print(f"  ❌ Marketaux error for {ticker_symbol}: {e}")
            return []
    
    def get_trending_stocks(self, limit: int = 10) -> List[Dict]:
        """
        Get trending stocks based on news volume
        
        Args:
            limit: Number of trending stocks to return
        
        Returns:
            List of trending entities with sentiment
        """
        try:
            url = f"{self.base_url}/entity/trending/aggregation"
            
            params = {
                'api_token': self.api_key,
                'countries': 'us',
                'min_doc_count': 5,
                'language': 'en',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            self.request_count += 1
            
            return data.get('data', [])
            
        except Exception as e:
            print(f"❌ Marketaux trending error: {e}")
            return []


if __name__ == "__main__":
    print("✅ Marketaux News Collector")
    print("📊 Features:")
    print("  - 100 requests/day (free tier)")
    print("  - 5,000+ global news sources")
    print("  - Built-in AI sentiment analysis")
    print("  - Ticker-specific filtering")
    print("  - Real-time updates")
