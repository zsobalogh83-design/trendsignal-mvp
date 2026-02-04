"""
TrendSignal - Ticker Configuration Helper
Database-driven ticker configuration with fallback to ticker_keywords.py

Version: 1.0
Date: 2025-02-04
"""

import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session


class TickerConfigLoader:
    """
    Load ticker configuration from database with fallback to hardcoded values
    
    Priority:
    1. Database (ticker.relevance_keywords, etc.)
    2. Fallback to ticker_keywords.py (if database is empty)
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize config loader
        
        Args:
            db: Optional database session
        """
        self.db = db
        self._cache = {}  # Cache loaded configs
    
    def get_relevance_keywords(self, ticker_symbol: str) -> List[str]:
        """
        Get relevance matching keywords for ticker from database
        
        Returns:
            List of keywords for news filtering
        """
        if not self.db:
            print(f"⚠️ No database session, cannot load keywords for {ticker_symbol}")
            return [ticker_symbol.split('.')[0].lower()]  # Minimal fallback
        
        try:
            from models import Ticker
            
            ticker = self.db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
            
            if ticker and ticker.relevance_keywords:
                keywords = json.loads(ticker.relevance_keywords)
                return keywords
            else:
                print(f"⚠️ No keywords in database for {ticker_symbol}")
                return [ticker_symbol.split('.')[0].lower()]  # Minimal fallback
                
        except Exception as e:
            print(f"❌ Database keyword load error for {ticker_symbol}: {e}")
            return [ticker_symbol.split('.')[0].lower()]  # Minimal fallback
    
    def get_sentiment_boost_keywords(self, ticker_symbol: str) -> Dict[str, List[str]]:
        """
        Get sentiment boost keywords for ticker from database
        
        Returns:
            {'positive': [...], 'negative': [...]}
        """
        if not self.db:
            print(f"⚠️ No database session, cannot load sentiment keywords for {ticker_symbol}")
            return {'positive': [], 'negative': []}
        
        try:
            from models import Ticker
            
            ticker = self.db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
            
            if ticker:
                result = {
                    'positive': [],
                    'negative': []
                }
                
                if ticker.sentiment_keywords_positive:
                    result['positive'] = json.loads(ticker.sentiment_keywords_positive)
                
                if ticker.sentiment_keywords_negative:
                    result['negative'] = json.loads(ticker.sentiment_keywords_negative)
                
                return result
            else:
                print(f"⚠️ Ticker {ticker_symbol} not found in database")
                return {'positive': [], 'negative': []}
                    
        except Exception as e:
            print(f"❌ Database sentiment keywords load error for {ticker_symbol}: {e}")
            return {'positive': [], 'negative': []}
    
    def get_ticker_language(self, ticker_symbol: str) -> str:
        """
        Get primary language for ticker
        
        Returns:
            'hu', 'en', etc.
        """
        if self.db:
            try:
                from models import Ticker
                
                ticker = self.db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                
                if ticker and ticker.primary_language:
                    return ticker.primary_language
            except Exception as e:
                print(f"⚠️ Database language load failed for {ticker_symbol}: {e}")
        
        # Fallback - detect from ticker symbol
        if ticker_symbol.endswith('.BD'):
            return 'hu'
        else:
            return 'en'
    
    def get_news_sources(self, ticker_symbol: str) -> Dict[str, List[str]]:
        """
        Get preferred and blocked news sources for ticker
        
        Returns:
            {'preferred': [...], 'blocked': [...]}
        """
        if self.db:
            try:
                from models import Ticker
                
                ticker = self.db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                
                if ticker:
                    result = {
                        'preferred': [],
                        'blocked': []
                    }
                    
                    if ticker.news_sources_preferred:
                        result['preferred'] = json.loads(ticker.news_sources_preferred)
                    
                    if ticker.news_sources_blocked:
                        result['blocked'] = json.loads(ticker.news_sources_blocked)
                    
                    # Return if we have data
                    if result['preferred'] or result['blocked']:
                        return result
                        
            except Exception as e:
                print(f"⚠️ Database news sources load failed for {ticker_symbol}: {e}")
        
        # Fallback - market-based defaults
        if ticker_symbol.endswith('.BD'):
            return {
                'preferred': ['portfolio.hu_befektetes', 'portfolio.hu_bank', 'hvg.hu', 'index.hu'],
                'blocked': []
            }
        else:
            return {
                'preferred': ['yahoo_finance', 'finnhub', 'reuters'],
                'blocked': []
            }
    
    def get_ticker_info(self, ticker_symbol: str) -> Dict:
        """
        Get complete ticker information
        
        Returns:
            Dict with all ticker config
        """
        # Check cache first
        if ticker_symbol in self._cache:
            return self._cache[ticker_symbol]
        
        result = {
            'symbol': ticker_symbol,
            'name': '',
            'market': '',
            'sector': '',
            'currency': '',
            'language': self.get_ticker_language(ticker_symbol),
            'relevance_keywords': self.get_relevance_keywords(ticker_symbol),
            'sentiment_keywords': self.get_sentiment_boost_keywords(ticker_symbol),
            'news_sources': self.get_news_sources(ticker_symbol)
        }
        
        if self.db:
            try:
                from models import Ticker
                
                ticker = self.db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
                
                if ticker:
                    result['name'] = ticker.name or ''
                    result['market'] = ticker.market or ''
                    result['sector'] = ticker.sector or ''
                    result['currency'] = ticker.currency or ''
            except Exception as e:
                print(f"⚠️ Database ticker info load failed for {ticker_symbol}: {e}")
        
        # Cache it
        self._cache[ticker_symbol] = result
        
        return result


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def get_ticker_config(ticker_symbol: str, db: Optional[Session] = None) -> Dict:
    """
    Convenience function to get ticker config
    
    Args:
        ticker_symbol: Ticker symbol
        db: Optional database session
    
    Returns:
        Complete ticker configuration dict
    """
    loader = TickerConfigLoader(db)
    return loader.get_ticker_info(ticker_symbol)


def get_sentiment_keywords(ticker_symbol: str, db: Optional[Session] = None) -> Dict[str, List[str]]:
    """
    Convenience function to get sentiment keywords
    
    Args:
        ticker_symbol: Ticker symbol
        db: Optional database session
    
    Returns:
        {'positive': [...], 'negative': [...]}
    """
    loader = TickerConfigLoader(db)
    return loader.get_sentiment_boost_keywords(ticker_symbol)


def get_relevance_keywords(ticker_symbol: str, db: Optional[Session] = None) -> List[str]:
    """
    Convenience function to get relevance keywords
    
    Args:
        ticker_symbol: Ticker symbol
        db: Optional database session
    
    Returns:
        List of relevance keywords
    """
    loader = TickerConfigLoader(db)
    return loader.get_relevance_keywords(ticker_symbol)


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    print("=" * 80)
    print("TICKER CONFIG LOADER - Testing")
    print("=" * 80)
    print()
    
    # Test with database
    try:
        from database import SessionLocal
        
        db = SessionLocal()
        
        # Test OTP.BD
        print("📊 Testing OTP.BD...")
        config = get_ticker_config('OTP.BD', db)
        
        print(f"  Name: {config['name']}")
        print(f"  Market: {config['market']}")
        print(f"  Language: {config['language']}")
        print(f"  Sector: {config['sector']}")
        print(f"  Currency: {config['currency']}")
        print(f"  Relevance Keywords: {len(config['relevance_keywords'])} items")
        print(f"    Sample: {', '.join(config['relevance_keywords'][:5])}...")
        print(f"  Sentiment Keywords:")
        print(f"    Positive: {len(config['sentiment_keywords']['positive'])} items")
        print(f"    Negative: {len(config['sentiment_keywords']['negative'])} items")
        
        db.close()
        
        print("\n✅ Database-driven config loading works!")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print("\n⚠️ Falling back to ticker_keywords.py")
        
        # Test fallback
        print("\n📊 Testing AAPL (fallback mode)...")
        config = get_ticker_config('AAPL', db=None)
        print(f"  Language: {config['language']}")
        print(f"  Keywords: {len(config['relevance_keywords'])} items")
