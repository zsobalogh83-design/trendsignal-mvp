"""
TrendSignal MVP - Hungarian News Sources Module
RSS feed collection from Portfolio.hu, Telex.hu, HVG.hu, Index.hu

Version: 1.0
Date: 2024-12-27
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from sentiment_analyzer import NewsItem
from multilingual_sentiment import MultilingualSentimentAnalyzer
from config import TrendSignalConfig, get_config
from ticker_keywords import calculate_relevance_score, get_all_relevant_keywords


# ==========================================
# HUNGARIAN RSS FEED SOURCES
# ==========================================

HUNGARIAN_RSS_SOURCES = {
    'portfolio_befektetes': {
        'url': 'https://www.portfolio.hu/rss/befektetes.xml',
        'name': 'Portfolio.hu Befektetés',
        'credibility': 0.90,
        'language': 'hu',
        'category': 'investment'
    },
    'portfolio_bank': {
        'url': 'https://www.portfolio.hu/rss/bank.xml',
        'name': 'Portfolio.hu Bank',
        'credibility': 0.90,
        'language': 'hu',
        'category': 'banking'
    },
    'portfolio_gazdasag': {
        'url': 'https://www.portfolio.hu/rss/gazdasag.xml',
        'name': 'Portfolio.hu Gazdaság',
        'credibility': 0.85,
        'language': 'hu',
        'category': 'economy'
    },
    'portfolio_uzlet': {
        'url': 'https://www.portfolio.hu/rss/uzlet.xml',
        'name': 'Portfolio.hu Üzlet',
        'credibility': 0.85,
        'language': 'hu',
        'category': 'business'
    },
    'telex_gazdasag': {
        'url': 'https://telex.hu/rss',
        'name': 'Telex.hu',
        'credibility': 0.80,
        'language': 'hu',
        'category': 'general'
    },
    'hvg_gazdasag': {
        'url': 'https://hvg.hu/rss',
        'name': 'HVG.hu',
        'credibility': 0.85,
        'language': 'hu',
        'category': 'general'
    },
    'index': {
        'url': 'https://index.hu/24ora/rss/',
        'name': 'Index.hu',
        'credibility': 0.75,
        'language': 'hu',
        'category': 'general'
    }
}


# ==========================================
# HUNGARIAN NEWS COLLECTOR
# ==========================================

class HungarianNewsCollector:
    """Collect news from Hungarian RSS sources"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
        # Use multilingual analyzer (auto-switches based on language)
        self.sentiment_analyzer = MultilingualSentimentAnalyzer(config)
        self.sources = HUNGARIAN_RSS_SOURCES
    
    def collect_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 24,
        sources: Optional[List[str]] = None
    ) -> List[NewsItem]:
        """
        Collect news from Hungarian RSS sources
        
        Args:
            ticker_symbol: Stock ticker (e.g., 'OTP.BD')
            company_name: Company name (e.g., 'OTP Bank')
            lookback_hours: How far back to look
            sources: List of source keys to use (None = all)
        
        Returns:
            List of NewsItem objects with sentiment analysis
        """
        all_news = []
        
        # Determine which sources to use
        if sources is None:
            active_sources = self.sources
        else:
            active_sources = {k: v for k, v in self.sources.items() if k in sources}
        
        # Collect from each source
        for source_key, source_info in active_sources.items():
            news_items = self._collect_from_rss(
                source_info,
                ticker_symbol,
                company_name,
                lookback_hours
            )
            all_news.extend(news_items)
        
        # Remove duplicates
        all_news = self._deduplicate_news(all_news)
        
        # Sort by published date
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        
        print(f"✅ Hungarian RSS: Collected {len(all_news)} total news items")
        
        return all_news
    
    def _collect_from_rss(
        self,
        source_info: Dict,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int
    ) -> List[NewsItem]:
        """Collect news from a single RSS feed"""
        try:
            # Parse RSS feed
            feed = feedparser.parse(source_info['url'])
            
            if not feed.entries:
                print(f"⚠️ {source_info['name']}: No entries in feed")
                return []
            
            news_items = []
            cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
            
            for entry in feed.entries:
                # Parse publish date
                try:
                    if hasattr(entry, 'published_parsed'):
                        published_dt = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed'):
                        published_dt = datetime(*entry.updated_parsed[:6])
                    else:
                        # Skip if no date
                        continue
                except:
                    continue
                
                # Skip if too old
                if published_dt < cutoff_time:
                    continue
                
                # Extract title and description
                title = entry.get('title', '')
                description = entry.get('description', '') or entry.get('summary', '')
                url = entry.get('link', '')
                
                # Check relevance using ticker-aware scoring
                relevance_score = calculate_relevance_score(
                    f"{title} {description}",
                    ticker_symbol
                )
                
                # Accept if relevance >= 0.5
                if relevance_score < 0.5:
                    continue
                
                # Analyze sentiment (multilingual auto-detect)
                text = f"{title}. {description}"
                sentiment = self.sentiment_analyzer.analyze_text(text, ticker_symbol)
                
                # Create NewsItem
                news_item = NewsItem(
                    title=title,
                    description=self._clean_html(description),
                    url=url,
                    published_at=published_dt,
                    source=source_info['name'],
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=source_info['credibility']
                )
                news_items.append(news_item)
            
            if news_items:
                print(f"✅ {source_info['name']}: Collected {len(news_items)} relevant items")
            
            return news_items
            
        except Exception as e:
            print(f"❌ {source_info['name']} error: {e}")
            return []
    
    def _is_relevant(
        self,
        title: str,
        description: str,
        ticker_symbol: str,
        company_name: str
    ) -> bool:
        """
        Check if news is relevant to ticker
        
        Enhanced for BÉT tickers with broader matching
        Phase 2: NER + zero-shot classification
        """
        text = f"{title} {description}".lower()
        
        # Extract ticker without suffix
        # e.g., "OTP.BD" → "otp"
        ticker_base = ticker_symbol.split('.')[0].lower()
        
        # Direct ticker mention (highest relevance)
        if ticker_base in text:
            return True
        
        # Check for full company name
        if company_name.lower() in text:
            return True
        
        # Extract company name significant parts
        company_parts = company_name.lower().split()
        
        # For BÉT tickers, be more lenient
        if '.BD' in ticker_symbol.upper():
            # Hungarian ticker - accept broader matches
            
            # Generic words to still ignore
            generic_words = {'nyrt', 'zrt', 'kft', 'inc', 'ltd', 'corp', 'corporation', 'plc'}
            significant_parts = [p for p in company_parts if p not in generic_words and len(p) > 2]
            
            # Accept if ANY significant part matches
            for part in significant_parts:
                if part in text:
                    return True
            
            # Special handling for banking/finance sector
            if ticker_base in ['otp', 'k&h', 'erste', 'mkb']:
                # Accept general banking news with high relevance indicators
                banking_indicators = ['bank', 'hitel', 'betét', 'kamat', 'jegybank', 'mnb']
                finance_indicators = ['befektetés', 'tőzsde', 'részvény', 'portfolio', 'pénzügy']
                
                has_banking = any(ind in text for ind in banking_indicators)
                has_finance = any(ind in text for ind in finance_indicators)
                
                if has_banking and has_finance:
                    return True  # Relevant financial/banking news
            
            # Special handling for energy sector
            if ticker_base in ['mol', 'mvm']:
                energy_indicators = ['olaj', 'gáz', 'energia', 'üzemanyag', 'benzin']
                if any(ind in text for ind in energy_indicators):
                    return True
            
            # Special handling for pharma
            if ticker_base in ['richter', 'egis']:
                pharma_indicators = ['gyógyszer', 'pharma', 'klinikai', 'fda', 'vakcina']
                if any(ind in text for ind in pharma_indicators):
                    return True
        
        else:
            # US/International ticker - stricter matching
            generic_words = {'nyrt', 'zrt', 'kft', 'inc', 'ltd', 'corp', 'corporation', 'plc'}
            significant_parts = [p for p in company_parts if p not in generic_words and len(p) > 3]
            
            for part in significant_parts:
                if part in text:
                    return True
        
        return False
    
    def _clean_html(self, html_text: str) -> str:
        """Remove HTML tags from text"""
        import re
        # Remove CDATA
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', html_text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate news items by URL and title similarity"""
        seen_urls = set()
        seen_titles = set()
        unique_items = []
        
        for item in news_items:
            # Skip if URL already seen
            if item.url in seen_urls:
                continue
            
            # Skip if very similar title
            title_lower = item.title.lower()
            if title_lower in seen_titles:
                continue
            
            seen_urls.add(item.url)
            seen_titles.add(title_lower)
            unique_items.append(item)
        
        removed_count = len(news_items) - len(unique_items)
        if removed_count > 0:
            print(f"🔄 Removed {removed_count} duplicate Hungarian news items")
        
        return unique_items


# ==========================================
# ENHANCED NEWS COLLECTOR (ENGLISH + HUNGARIAN)
# ==========================================

class EnhancedNewsCollector:
    """
    Enhanced news collector supporting both English and Hungarian sources
    
    Combines:
    - NewsAPI (English)
    - Alpha Vantage (English)
    - Portfolio.hu (Hungarian)
    - Telex, HVG, Index (Hungarian)
    """
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
        self.hungarian_collector = HungarianNewsCollector(config)
        
        # Import English collector
        from news_collector import NewsCollector
        self.english_collector = NewsCollector(config)
    
    def collect_all_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 24,
        include_hungarian: bool = True,
        include_english: bool = True
    ) -> List[NewsItem]:
        """
        Collect news from all sources (English + Hungarian)
        
        Args:
            ticker_symbol: Stock ticker
            company_name: Company name
            lookback_hours: Lookback period
            include_hungarian: Include Hungarian sources
            include_english: Include English sources
        
        Returns:
            Combined list of NewsItem objects
        """
        all_news = []
        
        # Collect English news
        if include_english:
            english_news = self.english_collector.collect_news(
                ticker_symbol, company_name, lookback_hours
            )
            all_news.extend(english_news)
        
        # Collect Hungarian news
        if include_hungarian:
            hungarian_news = self.hungarian_collector.collect_news(
                ticker_symbol, company_name, lookback_hours
            )
            all_news.extend(hungarian_news)
        
        # Final deduplication (cross-language)
        all_news = self._deduplicate_cross_language(all_news)
        
        # Sort by date
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        
        print(f"\n📊 Total collected: {len(all_news)} news items")
        print(f"   English: {len([n for n in all_news if n.source not in ['Portfolio.hu Befektetés', 'Portfolio.hu Bank', 'Portfolio.hu Gazdaság', 'Portfolio.hu Üzlet', 'Telex.hu', 'HVG.hu', 'Index.hu']])}")
        print(f"   Hungarian: {len([n for n in all_news if n.source in ['Portfolio.hu Befektetés', 'Portfolio.hu Bank', 'Portfolio.hu Gazdaság', 'Portfolio.hu Üzlet', 'Telex.hu', 'HVG.hu', 'Index.hu']])}")
        
        return all_news
    
    def _deduplicate_cross_language(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        Deduplicate across languages
        
        Simple URL-based for now
        Phase 2: Multilingual embedding similarity
        """
        seen_urls = set()
        unique_items = []
        
        for item in news_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)
        
        return unique_items


# ==========================================
# TICKER-SPECIFIC RSS FEEDS (BÉT Companies)
# ==========================================

BET_COMPANY_KEYWORDS = {
    'OTP.BD': ['otp', 'otp bank'],
    'MOL.BD': ['mol', 'mol nyrt', 'mol group'],
    'RICHTER.BD': ['richter', 'richter gedeon', 'gedeon richter'],
    'MTELEKOM.BD': ['magyar telekom', 'telekom', 'mtelekom'],
    '4IG.BD': ['4ig', 'jászai gellért', '4ig csoport'],
}


def get_bet_company_keywords(ticker_symbol: str) -> List[str]:
    """Get additional search keywords for BÉT companies"""
    return BET_COMPANY_KEYWORDS.get(ticker_symbol, [])


# ==========================================
# USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    print("✅ Hungarian News Collector Module Loaded")
    print("\n📰 Hungarian RSS Sources:")
    for key, source in HUNGARIAN_RSS_SOURCES.items():
        print(f"  • {source['name']:30s} (credibility: {source['credibility']:.0%})")
    
    print("\n🇭🇺 BÉT Company Keywords:")
    for ticker, keywords in BET_COMPANY_KEYWORDS.items():
        print(f"  • {ticker:12s}: {', '.join(keywords)}")
    
    print("\n🎯 Usage:")
    print("  collector = EnhancedNewsCollector()")
    print("  news = collector.collect_all_news('OTP.BD', 'OTP Bank')")
