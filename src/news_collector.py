"""
TrendSignal MVP - Enhanced News Collector with Database Integration
English + Hungarian news with timezone-aware datetime handling and DB persistence
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import TrendSignalConfig, get_config
from src.sentiment_analyzer import NewsItem

# Import Hungarian collector
try:
    from src.hungarian_news import HungarianNewsCollector
    HAS_HUNGARIAN = True
except ImportError:
    HAS_HUNGARIAN = False
    print("⚠️ Hungarian news module not available")

if TYPE_CHECKING:
    from src.multilingual_sentiment import MultilingualSentimentAnalyzer


class NewsCollector:
    """Enhanced collector with Hungarian support, timezone-aware datetimes, and DB persistence"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None, db: Optional[Session] = None):
        self.config = config or get_config()
        self.db = db  # Optional database session
        
        # Initialize Hungarian collector
        if HAS_HUNGARIAN:
            try:
                self.hungarian_collector = HungarianNewsCollector(config)
                print("✅ Hungarian news collector ready")
            except Exception as e:
                self.hungarian_collector = None
                print(f"⚠️ Hungarian collector init failed: {e}")
        else:
            self.hungarian_collector = None
    
    def collect_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 24,
        save_to_db: bool = True
    ) -> List[NewsItem]:
        """
        Collect news from all sources (English + Hungarian if applicable)
        All datetimes are timezone-aware (UTC)
        Optionally saves to database
        
        Args:
            ticker_symbol: Stock ticker
            company_name: Company name
            lookback_hours: Hours to look back
            save_to_db: If True and db session available, save to database
        
        Returns:
            List of NewsItem objects
        """
        from src.multilingual_sentiment import MultilingualSentimentAnalyzer
        
        all_news = []
        sentiment_analyzer = MultilingualSentimentAnalyzer(self.config, ticker_symbol)
        
        # Collect English news (NewsAPI + AlphaVantage)
        if self.config.newsapi_key and self.config.newsapi_key != "YOUR_NEWSAPI_KEY_HERE":
            newsapi_items = self._collect_from_newsapi(
                ticker_symbol, company_name, lookback_hours, sentiment_analyzer
            )
            all_news.extend(newsapi_items)
        
        if self.config.alphavantage_key and self.config.alphavantage_key != "YOUR_ALPHAVANTAGE_KEY_HERE":
            alphavantage_items = self._collect_from_alphavantage(
                ticker_symbol, lookback_hours, sentiment_analyzer
            )
            all_news.extend(alphavantage_items)
        
        # Collect Hungarian news for BÉT tickers
        if self.hungarian_collector and ticker_symbol.endswith('.BD'):
            print(f"🇭🇺 Collecting Hungarian news for {ticker_symbol}...")
            hungarian_items = self.hungarian_collector.collect_news(
                ticker_symbol=ticker_symbol,
                company_name=company_name,
                lookback_hours=lookback_hours
            )
            all_news.extend(hungarian_items)
            print(f"✅ Added {len(hungarian_items)} Hungarian news items")
        
        # Deduplicate
        all_news = self._deduplicate_news(all_news)
        
        # Sort by date
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        
        # Save to database if enabled
        if save_to_db and self.db and len(all_news) > 0:
            self._save_news_to_db(all_news, ticker_symbol)
        
        return all_news
    
    def _save_news_to_db(self, news_items: List[NewsItem], ticker_symbol: str):
        """Save news items to database"""
        try:
            from src.db_helpers import save_news_item_to_db
            
            saved_count = 0
            for item in news_items:
                if save_news_item_to_db(item, ticker_symbol, self.db):
                    saved_count += 1
            
            if saved_count > 0:
                print(f"💾 Saved {saved_count} news items to database")
                
        except Exception as e:
            print(f"⚠️ Could not save news to DB: {e}")
    
    def _collect_from_newsapi(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer'
    ) -> List[NewsItem]:
        """Collect from NewsAPI with timezone-aware datetimes"""
        url = "https://newsapi.org/v2/everything"
        
        # FIXED: Use timezone-aware datetimes
        to_date = datetime.now(timezone.utc)
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
                
                # FIXED: Parse with timezone awareness
                published_str = article.get('publishedAt', '')
                if published_str:
                    published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                else:
                    published_at = datetime.now(timezone.utc)
                
                news_item = NewsItem(
                    title=article.get('title', ''),
                    description=article.get('description', ''),
                    url=article.get('url', ''),
                    published_at=published_at,
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
        """Collect from Alpha Vantage with timezone-aware datetimes"""
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
            # FIXED: Timezone-aware cutoff
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for item in data.get('feed', []):
                # FIXED: Parse and make timezone-aware
                time_str = item.get('time_published', '')
                if time_str:
                    time_published = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
                    time_published = time_published.replace(tzinfo=timezone.utc)
                else:
                    time_published = datetime.now(timezone.utc)
                
                # FIXED: Both datetimes now timezone-aware
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
        """Remove duplicates"""
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
        
        removed = len(news_items) - len(unique_items)
        if removed > 0:
            print(f"🔄 Removed {removed} duplicates")
        
        return unique_items


if __name__ == "__main__":
    print("✅ Enhanced News Collector with Database Integration")
    print("🌐 English: NewsAPI + Alpha Vantage")
    print("🇭🇺 Hungarian: Portfolio.hu + RSS feeds")
    print("🕐 Timezone-aware datetime handling")
    print("💾 Database persistence support")
