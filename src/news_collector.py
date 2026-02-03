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

# Import Yahoo Finance collector
try:
    from src.yahoo_collector import YahooFinanceCollector
    HAS_YAHOO = True
except ImportError:
    HAS_YAHOO = False
    print("⚠️ Yahoo Finance module not available")

# Import Finnhub collector
try:
    from src.finnhub_collector import FinnhubCollector
    HAS_FINNHUB = True
except ImportError:
    HAS_FINNHUB = False
    print("⚠️ Finnhub module not available")

if TYPE_CHECKING:
    from src.multilingual_sentiment import MultilingualSentimentAnalyzer


class NewsCollector:
    """Enhanced collector with Hungarian support, timezone-aware datetimes, and DB persistence"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None, db: Optional[Session] = None):
        self.config = config or get_config()
        self.db = db  # Optional database session
        
        # Initialize Yahoo Finance collector (always available, no API key needed)
        if HAS_YAHOO:
            try:
                self.yahoo_collector = YahooFinanceCollector()
            except Exception as e:
                self.yahoo_collector = None
                print(f"⚠️ Yahoo collector init failed: {e}")
        else:
            self.yahoo_collector = None
        
        # Initialize Finnhub collector
        if HAS_FINNHUB and self.config.finnhub_api_key:
            try:
                self.finnhub_collector = FinnhubCollector(self.config.finnhub_api_key)
            except Exception as e:
                self.finnhub_collector = None
                print(f"⚠️ Finnhub collector init failed: {e}")
        else:
            self.finnhub_collector = None
        
        # Initialize Hungarian collector
        if HAS_HUNGARIAN:
            try:
                self.hungarian_collector = HungarianNewsCollector(config)
            except Exception as e:
                self.hungarian_collector = None
                print(f"⚠️ Hungarian collector init failed: {e}")
        else:
            self.hungarian_collector = None
    
    def collect_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 72,  # Increased to 72h for better coverage
        save_to_db: bool = True
    ) -> List[NewsItem]:
        """
        Collect news from all sources (English + Hungarian if applicable)
        All datetimes are timezone-aware (UTC)
        Optionally saves to database
        
        Args:
            ticker_symbol: Stock ticker
            company_name: Company name
            lookback_hours: Hours to look back (default: 72h for stable coverage)
            save_to_db: If True and db session available, save to database
        
        Returns:
            List of NewsItem objects
        """
        from src.multilingual_sentiment import MultilingualSentimentAnalyzer
        
        all_news = []
        sentiment_analyzer = MultilingualSentimentAnalyzer(self.config, ticker_symbol)
        
        # ===== MULTI-SOURCE STRATEGY =====
        # Priority: Yahoo Finance (unlimited) > Finnhub (60/min) > Alpha Vantage (25/day backup)
        
        # US Blue Chips: Prioritize Yahoo + Finnhub
        is_us_ticker = not ticker_symbol.endswith('.BD')
        
        # 1. Yahoo Finance RSS (unlimited, real-time) - PRIMARY for US tickers
        if self.yahoo_collector and is_us_ticker:
            yahoo_items = self._collect_from_yahoo(
                ticker_symbol, lookback_hours, sentiment_analyzer
            )
            all_news.extend(yahoo_items)
            print(f"  📰 Yahoo Finance: {len(yahoo_items)} articles")
        
        # 2. Finnhub API (60 req/min) - SECONDARY for US tickers
        if self.finnhub_collector and is_us_ticker and len(all_news) < 10:
            finnhub_items = self._collect_from_finnhub(
                ticker_symbol, lookback_hours, sentiment_analyzer
            )
            all_news.extend(finnhub_items)
            print(f"  📰 Finnhub: {len(finnhub_items)} articles")
        
        # 3. Alpha Vantage (25 req/day) - BACKUP ONLY if insufficient news
        if is_us_ticker and self.config.alphavantage_key and len(all_news) < 5:
            alphavantage_items = self._collect_from_alphavantage(
                ticker_symbol, lookback_hours, sentiment_analyzer
            )
            all_news.extend(alphavantage_items)
            print(f"  📰 Alpha Vantage (backup): {len(alphavantage_items)} articles")
        
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
    
    def _collect_from_yahoo(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer'
    ) -> List[NewsItem]:
        """
        Collect from Yahoo Finance RSS (unlimited, real-time)
        
        Primary source for US blue chip tickers
        """
        try:
            news_items = self.yahoo_collector.collect_news(
                ticker_symbol=ticker_symbol,
                max_articles=20
            )
            
            # Convert to NewsItem format with sentiment analysis
            analyzed_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for item in news_items:
                # Filter by time
                if item['published_at'] < cutoff_time:
                    continue
                
                # Analyze sentiment
                text = f"{item['title']}. {item.get('description', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                
                news_item = NewsItem(
                    title=item['title'],
                    description=item.get('description', ''),
                    url=item['url'],
                    published_at=item['published_at'],
                    source="Yahoo Finance",
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.90  # Yahoo Finance high credibility
                )
                analyzed_items.append(news_item)
            
            return analyzed_items
            
        except Exception as e:
            print(f"  ❌ Yahoo Finance collection error: {e}")
            return []
    
    def _collect_from_finnhub(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer'
    ) -> List[NewsItem]:
        """
        Collect from Finnhub API (60 req/min)
        
        Secondary source for US blue chip tickers
        """
        try:
            # Convert hours to days (Finnhub uses days)
            lookback_days = max(1, lookback_hours // 24)
            
            news_items = self.finnhub_collector.collect_news(
                ticker_symbol=ticker_symbol,
                lookback_days=lookback_days,
                max_articles=20
            )
            
            # Convert to NewsItem format with sentiment analysis
            analyzed_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for item in news_items:
                # Filter by time
                if item['published_at'] < cutoff_time:
                    continue
                
                # Analyze sentiment
                text = f"{item['title']}. {item.get('description', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                
                news_item = NewsItem(
                    title=item['title'],
                    description=item.get('description', ''),
                    url=item['url'],
                    published_at=item['published_at'],
                    source=f"Finnhub-{item['source']}",
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.85  # Finnhub high credibility
                )
                analyzed_items.append(news_item)
            
            return analyzed_items
            
        except Exception as e:
            print(f"  ❌ Finnhub collection error: {e}")
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
    print("✅ Enhanced News Collector v2.0 - Stable Sources")
    print("📰 Yahoo Finance (unlimited) + Finnhub (60 req/min)")
    print("🇭🇺 Hungarian: Portfolio.hu + RSS feeds")
    print("🕐 Timezone-aware datetime handling")
    print("💾 Database persistence support")
