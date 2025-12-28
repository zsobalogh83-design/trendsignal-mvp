"""
TrendSignal MVP - Enhanced News Collection Module
Collect news from NewsAPI, Alpha Vantage, AND Hungarian sources

Version: 1.1
Date: 2024-12-27
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass

# FIXED IMPORT
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import TrendSignalConfig, get_config
from src.sentiment_analyzer import NewsItem

# Import Hungarian news module
try:
    from src.hungarian_news import HungarianNewsCollector
    HAS_HUNGARIAN = True
except ImportError:
    HAS_HUNGARIAN = False
    print("⚠️ Hungarian news module not available")

# Type hints only
if TYPE_CHECKING:
    from src.multilingual_sentiment import MultilingualSentimentAnalyzer


class NewsCollector:
    """Enhanced news collector with Hungarian support"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
        
        # Initialize Hungarian collector if available
        if HAS_HUNGARIAN:
            try:
                self.hungarian_collector = HungarianNewsCollector(config)
                print("✅ Hungarian news collector initialized")
            except:
                self.hungarian_collector = None
        else:
            self.hungarian_collector = None
    
    def collect_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 24
    ) -> List[NewsItem]:
        """
        Collect news from ALL sources (English + Hungarian)
        """
        from src.multilingual_sentiment import MultilingualSentimentAnalyzer
        
        all_news = []
        sentiment_analyzer = MultilingualSentimentAnalyzer(self.config, ticker_symbol)
        
        # Collect from NewsAPI (English)
        if self.config.newsapi_key and self.config.newsapi_key != "YOUR_NEWSAPI_KEY_HERE":
            newsapi_items = self._collect_from_newsapi(
                ticker_symbol, company_name, lookback_hours, sentiment_analyzer
            )
            all_news.extend(newsapi_items)
        
        # Collect from Alpha Vantage (English)
        if self.config.alphavantage_key and self.config.alphavantage_key != "YOUR_ALPHAVANTAGE_KEY_HERE":
            alphavantage_items = self._collect_from_alphavantage(
                ticker_symbol, lookback_hours, sentiment_analyzer
            )
            all_news.extend(alphavantage_items)
        
        # Collect from Hungarian sources (if ticker is Hungarian)
        if self.hungarian_collector and ticker_symbol.endswith('.BD'):
            hungarian_items = self.hungarian_collector.collect_hungarian_news(
                ticker_symbol, company_name, lookback_hours, sentiment_analyzer
            )
            all_news.extend(hungarian_items)
            print(f"🇭🇺 Added {len(hungarian_items)} Hungarian news items")
        
        # Remove duplicates
        all_news = self._deduplicate_news(all_news)
        
        # Sort by published date
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
                text = f"{article.get('title', '')}. {article.get('description', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                
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
                    credibility=0.85
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
                time_published = datetime.strptime(
                    item.get('time_published', ''),
                    '%Y%m%dT%H%M%S'
                )
                
                if time_published < cutoff_time:
                    continue
                
                text = f"{item.get('title', '')}. {item.get('summary', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                
                news_item = NewsItem(
                    title=item.get('title', ''),
                    description=item.get('summary', ''),
                    url=item.get('url', ''),
                    published_at=time_published,
                    source='Alpha Vantage',
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.80
                )
                news_items.append(news_item)
            
            print(f"✅ Alpha Vantage: Collected {len(news_items)} news items")
            return news_items
            
        except Exception as e:
            print(f"❌ Alpha Vantage error: {e}")
            return []
    
    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate news items"""
        seen_urls = set()
        seen_titles = set()
        unique_items = []
        
        for item in news_items:
            if item.url in seen_urls:
                continue
            
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


if __name__ == "__main__":
    print("✅ Enhanced News Collector Module")
    print("📰 Sources: NewsAPI, Alpha Vantage, Hungarian sites")
    print("🧠 Multi-language sentiment analysis")
