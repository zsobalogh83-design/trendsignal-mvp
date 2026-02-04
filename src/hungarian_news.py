"""
TrendSignal MVP - Hungarian News Collector
RSS feed aggregator with FinBERT sentiment analysis

FIXED: All datetimes are now timezone-aware (UTC)
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, TYPE_CHECKING
import re
from src.config import TrendSignalConfig
from src.sentiment_analyzer import NewsItem

if TYPE_CHECKING:
    from src.multilingual_sentiment import MultilingualSentimentAnalyzer


class HungarianNewsCollector:
    """Collects Hungarian financial news from RSS feeds and web sources"""
    
    # Enhanced keywords - company specific (DEPRECATED - now in database)
    # Kept for fallback compatibility
    COMPANY_KEYWORDS = {
        'OTP': [
            'otp', 'otp bank', 'otp nyrt', 'csányi', 'csányi sándor',
            'bankár', 'bankszektor', 'hitel', 'betét', 'digitális bank'
        ],
        'MOL': [
            'mol', 'mol nyrt', 'mol group', 'hernádi', 'hernádi zsolt',
            'olaj', 'gáz', 'üzemanyag', 'benzin', 'kőolaj', 'finomító',
            'downstream', 'upstream', 'petrolkémia'
        ],
        'RICHTER': [
            'richter', 'gedeon richter', 'orbán gábor',
            'gyógyszer', 'gyógyszeripar', 'pharma', 'biotech'
        ]
    }
    
    # RSS Feeds with realistic expectations
    RSS_FEEDS = {
        'portfolio.hu_befektetes': {
            'url': 'https://www.portfolio.hu/rss/befektetes.xml',
            'credibility': 0.90
        },
        'portfolio.hu_bank': {
            'url': 'https://www.portfolio.hu/rss/bank.xml',
            'credibility': 0.90
        },
        'portfolio.hu_gazdasag': {
            'url': 'https://www.portfolio.hu/rss/gazdasag.xml',
            'credibility': 0.85
        },
        'portfolio.hu_uzlet': {
            'url': 'https://www.portfolio.hu/rss/uzlet.xml',
            'credibility': 0.80
        },
        'telex.hu': {
            'url': 'https://telex.hu/rss/gazdasag',
            'credibility': 0.85
        },
        'hvg.hu': {
            'url': 'https://hvg.hu/rss/gazdasag',
            'credibility': 0.85
        },
        'index.hu': {
            'url': 'https://index.hu/gazdasag/rss/',
            'credibility': 0.80
        }
    }
    
    def __init__(self, config: TrendSignalConfig, db=None):
        self.config = config
        self.db = db  # 🆕 Database session for ticker config
        print("✅ Hungarian news collector initialized")
        print(f"🔤 Enhanced keywords ready for Hungarian news")
    
    def collect_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 24
    ) -> List[NewsItem]:
        """
        Collect Hungarian news for BÉT tickers
        
        Args:
            ticker_symbol: e.g., 'OTP.BD'
            company_name: e.g., 'OTP Bank'
            lookback_hours: Hours to look back
        
        Returns:
            List of NewsItem objects with Hungarian text and sentiment analysis
        """
        # Initialize sentiment analyzer
        from src.multilingual_sentiment import MultilingualSentimentAnalyzer
        sentiment_analyzer = MultilingualSentimentAnalyzer(self.config, ticker_symbol)
        
        # Extract company base name
        company_base = ticker_symbol.replace('.BD', '').upper()
        
        # Get company-specific keywords - 🆕 DATABASE-DRIVEN (no fallback)
        if self.db:
            try:
                from ticker_config import get_relevance_keywords
                keywords = get_relevance_keywords(ticker_symbol, self.db)
                print(f"🔍 Keywords for {company_base} (DB): {keywords[:3]}...")
            except Exception as e:
                print(f"❌ Database keyword load error for {ticker_symbol}: {e}")
                # Minimal fallback - just ticker name
                keywords = [company_base.lower()]
                print(f"⚠️ Using minimal fallback: {keywords}")
        else:
            print(f"⚠️ No database session available")
            keywords = [company_base.lower()]
            print(f"⚠️ Using minimal fallback: {keywords}")
        
        all_news = []
        
        # FIXED: Timezone-aware cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        # Collect from RSS feeds
        for feed_name, feed_info in self.RSS_FEEDS.items():
            try:
                feed_news = self._parse_rss_feed(
                    feed_url=feed_info['url'],
                    feed_name=feed_name,
                    keywords=keywords,
                    cutoff_time=cutoff_time,
                    credibility=feed_info['credibility'],
                    sentiment_analyzer=sentiment_analyzer,
                    ticker_symbol=ticker_symbol
                )
                all_news.extend(feed_news)
            except Exception as e:
                print(f"❌ {feed_name} error: {e}")
        
        # Deduplicate
        all_news = self._deduplicate(all_news)
        
        print(f"✅ Hungarian RSS: Collected {len(all_news)} total news items")
        
        return all_news
    
    def _parse_rss_feed(
        self,
        feed_url: str,
        feed_name: str,
        keywords: List[str],
        cutoff_time: datetime,
        credibility: float,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer',
        ticker_symbol: str
    ) -> List[NewsItem]:
        """
        Parse RSS feed and filter by keywords
        
        FIXED: All datetimes are timezone-aware + sentiment analysis added
        """
        try:
            # Parse feed
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                return []
            
            news_items = []
            
            for entry in feed.entries:
                # FIXED: Parse datetime and make it timezone-aware
                published_at = self._parse_pub_date(entry.get('published', ''))
                
                # FIXED: Both datetimes are now timezone-aware
                if published_at < cutoff_time:
                    continue
                
                # Get title and description
                title = entry.get('title', '')
                description = entry.get('summary', entry.get('description', ''))
                
                # Keyword matching
                text_combined = f"{title.lower()} {description.lower()}"
                if not any(keyword in text_combined for keyword in keywords):
                    continue
                
                # 🧠 SENTIMENT ANALYSIS - analyze Hungarian text
                text_for_sentiment = f"{title}. {description}"
                sentiment = sentiment_analyzer.analyze_text(text_for_sentiment, ticker_symbol)
                
                # Create NewsItem with sentiment
                news_item = NewsItem(
                    title=title,
                    description=description,
                    url=entry.get('link', ''),
                    published_at=published_at,
                    source=feed_name,
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=credibility
                )
                news_items.append(news_item)
            
            return news_items
            
        except Exception as e:
            raise Exception(f"RSS parse error: {e}")
    
    def _parse_pub_date(self, pub_date_str: str) -> datetime:
        """
        Parse various RSS date formats and return timezone-aware datetime
        
        FIXED: Always returns timezone-aware datetime in UTC
        """
        if not pub_date_str:
            return datetime.now(timezone.utc)
        
        # Common RSS date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # With timezone
            '%a, %d %b %Y %H:%M:%S',     # Without timezone
            '%Y-%m-%dT%H:%M:%S%z',       # ISO with timezone
            '%Y-%m-%dT%H:%M:%S',         # ISO without timezone
            '%Y-%m-%d %H:%M:%S',         # Simple format
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(pub_date_str, fmt)
                
                # CRITICAL FIX: If datetime is timezone-naive, add UTC timezone
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    # Convert to UTC if it has a different timezone
                    dt = dt.astimezone(timezone.utc)
                
                return dt
            except ValueError:
                continue
        
        # Fallback: try feedparser's parser
        try:
            import time
            parsed = feedparser._parse_date(pub_date_str)
            if parsed:
                dt = datetime(*parsed[:6])
                # CRITICAL FIX: Make it timezone-aware
                dt = dt.replace(tzinfo=timezone.utc)
                return dt
        except:
            pass
        
        # Last resort: current time (timezone-aware)
        print(f"⚠️ Could not parse date: {pub_date_str}, using current time")
        return datetime.now(timezone.utc)
    
    def _deduplicate(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate news items"""
        seen_urls = set()
        seen_titles = set()
        unique_items = []
        
        for item in news_items:
            # Skip if URL seen
            if item.url in seen_urls:
                continue
            
            # Skip if very similar title
            title_normalized = item.title.lower().strip()
            if title_normalized in seen_titles:
                continue
            
            seen_urls.add(item.url)
            seen_titles.add(title_normalized)
            unique_items.append(item)
        
        return unique_items


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    from src.config import get_config
    
    config = get_config()
    collector = HungarianNewsCollector(config)
    
    print("\n" + "=" * 60)
    print("🧪 Testing Hungarian News Collector")
    print("=" * 60)
    
    # Test OTP
    print("\n📰 Testing OTP.BD...")
    news = collector.collect_news("OTP.BD", "OTP Bank", lookback_hours=48)
    
    print(f"\n✅ Found {len(news)} OTP news items")
    if news:
        print(f"\nFirst item:")
        print(f"  Title: {news[0].title}")
        print(f"  Source: {news[0].source}")
        print(f"  Published: {news[0].published_at}")
        print(f"  Timezone: {news[0].published_at.tzinfo}")
    
    # Test MOL
    print("\n📰 Testing MOL.BD...")
    news = collector.collect_news("MOL.BD", "MOL Group", lookback_hours=48)
    
    print(f"\n✅ Found {len(news)} MOL news items")
    if news:
        print(f"\nFirst item:")
        print(f"  Title: {news[0].title}")
        print(f"  Source: {news[0].source}")
        print(f"  Published: {news[0].published_at}")
        print(f"  Timezone: {news[0].published_at.tzinfo}")
