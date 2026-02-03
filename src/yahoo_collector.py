"""
TrendSignal - Yahoo Finance RSS Collector
Stable, unlimited news source with real-time updates

Version: 1.0
Date: 2025-02-03
"""

import feedparser
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional


class YahooFinanceCollector:
    """
    Yahoo Finance RSS news collector
    
    Advantages:
    - FREE with no API key required
    - Real-time news updates
    - No rate limits
    - Ticker-specific RSS feeds
    - High reliability
    """
    
    def __init__(self):
        """Initialize Yahoo Finance collector"""
        self.base_url = "https://finance.yahoo.com/rss/headline"
        print("✅ Yahoo Finance RSS collector ready (unlimited, real-time)")
    
    def collect_news(
        self, 
        ticker_symbol: str, 
        max_articles: int = 20
    ) -> List[Dict]:
        """
        Collect news for a ticker from Yahoo Finance RSS
        
        Args:
            ticker_symbol: Stock ticker (e.g., 'AAPL', 'MSFT')
            max_articles: Max number of articles to return
        
        Returns:
            List of news items
        """
        try:
            # Build RSS feed URL
            feed_url = f"{self.base_url}?s={ticker_symbol}"
            
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"  ℹ️ Yahoo Finance: No news found for {ticker_symbol}")
                return []
            
            news_items = []
            
            for entry in feed.entries[:max_articles]:
                # Parse publication date
                published_at = self._parse_datetime(entry.get('published', ''))
                
                # Extract title and summary
                title = entry.get('title', '')
                description = entry.get('summary', '')
                
                # Clean HTML tags from description if present
                if description:
                    import re
                    description = re.sub(r'<[^>]+>', '', description)
                
                news_items.append({
                    "title": title,
                    "description": description,
                    "url": entry.get('link', ''),
                    "source": "Yahoo Finance",
                    "published_at": published_at,
                    "credibility": 0.90  # Yahoo Finance high credibility
                })
            
            print(f"  ✅ Yahoo Finance: {len(news_items)} articles for {ticker_symbol}")
            return news_items
            
        except Exception as e:
            print(f"  ❌ Yahoo Finance error for {ticker_symbol}: {e}")
            return []
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse RSS datetime string to timezone-aware datetime object"""
        if not date_str:
            return datetime.now(timezone.utc)
        
        try:
            # Try feedparser's built-in parser
            parsed = feedparser._parse_date(date_str)
            if parsed:
                dt = datetime(*parsed[:6])
                # Make timezone-aware
                return dt.replace(tzinfo=timezone.utc)
        except:
            pass
        
        # Fallback to current time
        return datetime.now(timezone.utc)


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    print("🧪 Testing Yahoo Finance RSS Collector...")
    print("=" * 60)
    
    collector = YahooFinanceCollector()
    
    # Test with multiple tickers
    tickers = ["AAPL", "MSFT", "TSLA"]
    
    for ticker in tickers:
        print(f"\n📰 Collecting news for {ticker}...")
        news = collector.collect_news(ticker, max_articles=5)
        
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
