"""
TrendSignal MVP - Enhanced News Collector with Database Integration
English + Hungarian news with timezone-aware datetime handling and DB persistence
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Import Marketaux collector
try:
    from src.marketaux_collector import MarketauxCollector
    HAS_MARKETAUX = True
except ImportError:
    HAS_MARKETAUX = False
    print("⚠️ Marketaux module not available")

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
        
        # Initialize Marketaux collector
        if HAS_MARKETAUX and self.config.marketaux_api_key:
            try:
                self.marketaux_collector = MarketauxCollector(self.config.marketaux_api_key)
            except Exception as e:
                self.marketaux_collector = None
                print(f"⚠️ Marketaux collector init failed: {e}")
        else:
            self.marketaux_collector = None
        
        # Initialize Hungarian collector
        if HAS_HUNGARIAN:
            try:
                self.hungarian_collector = HungarianNewsCollector(config, db=self.db)
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
        # US tickers: Yahoo + Marketaux + Finnhub (comprehensive English coverage)
        # Hungarian tickers: Only Hungarian RSS feeds (magyar specific sources)
        
        is_us_ticker = not ticker_symbol.endswith('.BD')
        
        # ===== US TICKERS: Multi-source English news (PARALLEL) =====
        if is_us_ticker:
            print(f"🔍 DEBUG: US ticker detected: {ticker_symbol}")

            source_tasks = {}
            if self.yahoo_collector:
                print(f"🔍 DEBUG: Yahoo collector exists, scheduling...")
                source_tasks['yahoo'] = lambda: self._collect_from_yahoo(ticker_symbol, lookback_hours, sentiment_analyzer)
            else:
                print(f"⚠️ DEBUG: Yahoo collector is None")

            print(f"🔍 DEBUG: self.marketaux_collector = {self.marketaux_collector}")
            if self.marketaux_collector:
                print(f"🔍 DEBUG: Marketaux collector EXISTS, scheduling...")
                source_tasks['marketaux'] = lambda: self._collect_from_marketaux(ticker_symbol, lookback_hours)
            else:
                print(f"⚠️ DEBUG: Marketaux collector is None - WHY?")
                print(f"⚠️ DEBUG: config.marketaux_api_key = {bool(self.config.marketaux_api_key)}")

            if self.finnhub_collector:
                source_tasks['finnhub'] = lambda: self._collect_from_finnhub(ticker_symbol, lookback_hours, sentiment_analyzer)

            if source_tasks:
                with ThreadPoolExecutor(max_workers=len(source_tasks)) as src_executor:
                    src_futures = {src_executor.submit(fn): name for name, fn in source_tasks.items()}
                    for future in as_completed(src_futures):
                        source_name = src_futures[future]
                        try:
                            items = future.result()
                            all_news.extend(items)
                            print(f"  📰 {source_name.capitalize()}: {len(items)} articles")
                        except Exception as e:
                            print(f"  ⚠️ {source_name} failed: {e}")
        
        # ===== HUNGARIAN TICKERS: Only Hungarian sources =====
        # Skip English APIs - not relevant for BÉT stocks
        
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
    
    def _collect_from_marketaux(
        self,
        ticker_symbol: str,
        lookback_hours: int
    ) -> List[NewsItem]:
        """
        Collect from Marketaux API with BUILT-IN AI sentiment
        
        Advantage: No need for FinBERT analysis, sentiment already provided!
        """
        try:
            lookback_days = max(1, lookback_hours // 24)
            
            news_items = self.marketaux_collector.collect_news(
                ticker_symbol=ticker_symbol,
                lookback_days=lookback_days,
                max_articles=20
            )
            
            # Convert to NewsItem format - sentiment ALREADY analyzed!
            analyzed_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for item in news_items:
                # Filter by time
                if item['published_at'] < cutoff_time:
                    continue
                
                # ✅ Use Marketaux's AI sentiment (no FinBERT needed!)
                sentiment_score = item.get('sentiment_score', 0.0)
                
                # Convert -1 to +1 score to label
                if sentiment_score > 0.3:
                    sentiment_label = 'positive'
                    confidence = min(abs(sentiment_score), 1.0)
                elif sentiment_score < -0.3:
                    sentiment_label = 'negative'
                    confidence = min(abs(sentiment_score), 1.0)
                else:
                    sentiment_label = 'neutral'
                    confidence = 0.5
                
                news_item = NewsItem(
                    title=item['title'],
                    description=item.get('description', ''),
                    url=item['url'],
                    published_at=item['published_at'],
                    source=f"Marketaux-{item['source']}",
                    sentiment_score=sentiment_score,  # ✅ AI-powered
                    sentiment_confidence=confidence,
                    sentiment_label=sentiment_label,
                    credibility=item.get('credibility', 0.88)
                )
                analyzed_items.append(news_item)
            
            return analyzed_items
            
        except Exception as e:
            print(f"  ❌ Marketaux collection error: {e}")
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
    print("✅ Enhanced News Collector v2.2 - Optimized for US/Hungarian split")
    print("🇺🇸 US Tickers: Yahoo (∞) + Marketaux (100/day) + Finnhub (60/min)")
    print("🇭🇺 Hungarian: Portfolio.hu + RSS feeds only")
    print("📊 Quota usage: ~8 US tickers × 64 refreshes = ~512 Marketaux + ~512 Finnhub per day")
    print("⚠️ Marketaux quota will exhaust mid-day, falls back to Yahoo + Finnhub")
    print("💾 Database persistence support")
