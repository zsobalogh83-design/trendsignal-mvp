"""
TrendSignal MVP - News Collection Module
Collect news from NewsAPI and Alpha Vantage

Version: 1.0
Date: 2024-12-27
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass

from config import TrendSignalConfig, get_config
from sentiment_analyzer import NewsItem

# Type hints only
if TYPE_CHECKING:
    from multilingual_sentiment import MultilingualSentimentAnalyzer


# ==========================================
# NEWS COLLECTOR
# ==========================================

class NewsCollector:
    """Collect news from multiple sources"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
    
    def collect_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 24
    ) -> List[NewsItem]:
        """
        Collect news from all enabled sources
        
        Args:
            ticker_symbol: Stock ticker (e.g., 'AAPL')
            company_name: Company name (e.g., 'Apple Inc.')
            lookback_hours: How far back to look
        
        Returns:
            List of NewsItem objects with sentiment analysis
        """
        # Import at runtime to avoid circular dependency
        from multilingual_sentiment import MultilingualSentimentAnalyzer
        
        all_news = []
        
        # Initialize ticker-aware multilingual sentiment analyzer
        sentiment_analyzer = MultilingualSentimentAnalyzer(self.config, ticker_symbol)
        
        # Collect from NewsAPI
        if self.config.newsapi_key and self.config.newsapi_key != "YOUR_NEWSAPI_KEY_HERE":
            newsapi_items = self._collect_from_newsapi(
                ticker_symbol, company_name, lookback_hours, sentiment_analyzer
            )
            all_news.extend(newsapi_items)
        
        # Collect from Alpha Vantage
        if self.config.alphavantage_key and self.config.alphavantage_key != "YOUR_ALPHAVANTAGE_KEY_HERE":
            alphavantage_items = self._collect_from_alphavantage(
                ticker_symbol, lookback_hours, sentiment_analyzer
            )
            all_news.extend(alphavantage_items)
        
        # Remove duplicates (by URL or title similarity)
        all_news = self._deduplicate_news(all_news)
        
        # Sort by published date (newest first)
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        
        return all_news
    
    def _collect_from_newsapi(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer'
    ) -> List[NewsItem]:
        """Collect news from NewsAPI"""
        url = "https://newsapi.org/v2/everything"
        
        # Calculate date range
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(hours=lookback_hours)
        
        params = {
            'q': f'{ticker_symbol} OR "{company_name}"',
            'from': from_date.isoformat(),
            'to': to_date.isoformat(),
            'language': 'en',
            'sortBy': 'publishedAt',
            'apiKey': self.config.newsapi_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            news_items = []
            for article in data.get('articles', []):
                # Analyze sentiment (ticker-aware)
                text = f"{article.get('title', '')}. {article.get('description', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                
                # Create NewsItem
                news_item = NewsItem(
                    title=article.get('title', ''),
                    description=article.get('description', ''),
                    url=article.get('url', ''),
                    published_at=datetime.fromisoformat(
                        article.get('publishedAt', '').replace('Z', '+00:00')
                    ),
                    source='NewsAPI',
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.85  # NewsAPI credibility
                )
                news_items.append(news_item)
            
            print(f"✅ NewsAPI: Collected {len(news_items)} news items")
            return news_items
            
        except Exception as e:
            print(f"❌ NewsAPI error: {e}")
            return []
    
    def _collect_from_alphavantage(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer'
    ) -> List[NewsItem]:
        """Collect news from Alpha Vantage"""
        url = "https://www.alphavantage.co/query"
        
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': ticker_symbol,
            'apikey': self.config.alphavantage_key,
            'limit': 50
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            news_items = []
            cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
            
            for item in data.get('feed', []):
                # Parse timestamp
                time_published = datetime.strptime(
                    item.get('time_published', ''),
                    '%Y%m%dT%H%M%S'
                )
                
                # Skip if too old
                if time_published < cutoff_time:
                    continue
                
                # Analyze sentiment (ticker-aware)
                text = f"{item.get('title', '')}. {item.get('summary', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                
                # Create NewsItem
                news_item = NewsItem(
                    title=item.get('title', ''),
                    description=item.get('summary', ''),
                    url=item.get('url', ''),
                    published_at=time_published,
                    source='Alpha Vantage',
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.80  # Alpha Vantage credibility
                )
                news_items.append(news_item)
            
            print(f"✅ Alpha Vantage: Collected {len(news_items)} news items")
            return news_items
            
        except Exception as e:
            print(f"❌ Alpha Vantage error: {e}")
            return []
    
    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        Remove duplicate news items
        
        Simple deduplication by URL and title similarity
        (Phase 2: TF-IDF + cosine similarity)
        """
        seen_urls = set()
        seen_titles = set()
        unique_items = []
        
        for item in news_items:
            # Skip if URL already seen
            if item.url in seen_urls:
                continue
            
            # Skip if very similar title already seen
            title_lower = item.title.lower()
            if title_lower in seen_titles:
                continue
            
            seen_urls.add(item.url)
            seen_titles.add(title_lower)
            unique_items.append(item)
        
        removed_count = len(news_items) - len(unique_items)
        if removed_count > 0:
            print(f"🔄 Removed {removed_count} duplicate news items")
        
        return unique_items


# ==========================================
# USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    print("✅ News Collector Module Loaded")
    print("📰 Sources: NewsAPI, Alpha Vantage")
    print("🔄 Deduplication: URL + Title similarity")
    print("🧠 Auto sentiment analysis with FinBERT")
