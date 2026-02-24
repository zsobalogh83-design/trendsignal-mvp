"""
TrendSignal MVP - Multilingual Sentiment Handler
Automatic language detection and appropriate sentiment analysis

Version: 1.0
Date: 2024-12-27
"""

from typing import Dict, Optional
import re
import threading

_multilingual_finbert_lock = threading.Lock()


# ==========================================
# LANGUAGE DETECTION
# ==========================================

def detect_language(text: str) -> str:
    """
    Simple language detection (Hungarian vs English)
    
    Uses character frequency and common words
    For production: use langdetect or polyglot library
    
    Args:
        text: Text to analyze
    
    Returns:
        'hu' or 'en'
    """
    text_lower = text.lower()
    
    # Hungarian-specific characters
    hungarian_chars = ['ő', 'ű', 'á', 'é', 'í', 'ó', 'ö', 'ü', 'ú']
    hu_char_count = sum(text_lower.count(char) for char in hungarian_chars)
    
    # If has Hungarian chars, likely Hungarian
    if hu_char_count >= 2:
        return 'hu'
    
    # Common Hungarian words
    hungarian_words = [
        'hogy', 'és', 'vagy', 'nem', 'van', 'lesz', 'volt', 'ben', 'nak', 'nek',
        'ról', 'től', 'nál', 'hoz', 'ban', 'ság', 'ség', 'nak', 'nek',
        'magyar', 'milliárd', 'milliő', 'forint', 'százalék',
        'növekedés', 'csökkenés', 'emelkedés', 'bank', 'nyrt', 'zrt'
    ]
    
    # Common English words
    english_words = [
        'the', 'and', 'or', 'to', 'of', 'in', 'for', 'on', 'at', 'by',
        'with', 'from', 'that', 'this', 'have', 'has', 'will', 'would',
        'stock', 'share', 'earnings', 'revenue', 'profit', 'inc', 'corp'
    ]
    
    # Count matches
    words = text_lower.split()
    hu_word_count = sum(1 for word in words if any(hw in word for hw in hungarian_words))
    en_word_count = sum(1 for word in words if word in english_words)
    
    # Decision
    if hu_word_count > en_word_count:
        return 'hu'
    else:
        return 'en'


# ==========================================
# MULTILINGUAL SENTIMENT ANALYZER
# ==========================================

class MultilingualSentimentAnalyzer:
    """
    Automatically route to appropriate sentiment analyzer based on language
    
    - English → FinBERT
    - Hungarian → Enhanced Keywords
    """
    
    def __init__(self, config=None, ticker_symbol=None):
        self.config = config
        self.ticker_symbol = ticker_symbol
        
        # Initialize both engines
        self._init_engines()
    
    def _init_engines(self):
        """Initialize FinBERT and keyword-based analyzers"""
        from config import USE_FINBERT
        
        # FinBERT for English
        self.finbert_available = False
        if USE_FINBERT:
            try:
                from finbert_analyzer import FinBERTAnalyzer
                with _multilingual_finbert_lock:
                    if not hasattr(MultilingualSentimentAnalyzer, '_finbert_instance'):
                        print("🧠 Loading FinBERT for English sentiment...")
                        MultilingualSentimentAnalyzer._finbert_instance = FinBERTAnalyzer()
                self.finbert = MultilingualSentimentAnalyzer._finbert_instance
                self.finbert_available = True
                print("   ✅ FinBERT ready for English news")
            except Exception as e:
                print(f"   ⚠️ FinBERT not available: {e}")
                self.finbert = None
        else:
            self.finbert = None
        
        # Enhanced keywords for Hungarian (always available)
        from sentiment_analyzer import SentimentAnalyzer
        self.keyword_analyzer = SentimentAnalyzer(self.config, self.ticker_symbol)
        # Force mock mode for Hungarian
        self.keyword_analyzer.use_finbert = False
        print("🔤 Enhanced keywords ready for Hungarian news")
    
    def analyze_text(self, text: str, ticker_symbol: Optional[str] = None) -> Dict[str, float]:
        """
        Analyze sentiment with automatic language detection
        
        Args:
            text: News text
            ticker_symbol: Optional ticker for context
        
        Returns:
            Sentiment dictionary with language info
        """
        # Detect language
        language = detect_language(text)
        
        ticker = ticker_symbol or self.ticker_symbol
        
        # Route to appropriate analyzer
        if language == 'en' and self.finbert_available:
            # English → FinBERT
            result = self.finbert.analyze(text)
            result['language'] = 'en'
            result['method'] = 'finbert'
        else:
            # Hungarian (or English fallback) → Keywords
            result = self.keyword_analyzer._mock_sentiment_analysis(text, ticker)
            result['language'] = language
            result['method'] = 'keywords'
        
        return result
    
    def analyze_batch(self, texts: list, ticker_symbol: Optional[str] = None) -> list:
        """
        Analyze multiple texts efficiently
        
        Groups by language and uses appropriate batch processing
        """
        results = []
        
        # Separate by language
        english_texts = []
        hungarian_texts = []
        indices = {'en': [], 'hu': []}
        
        for i, text in enumerate(texts):
            lang = detect_language(text)
            if lang == 'en':
                english_texts.append(text)
                indices['en'].append(i)
            else:
                hungarian_texts.append(text)
                indices['hu'].append(i)
        
        # Process English with FinBERT (batch)
        en_results = []
        if english_texts and self.finbert_available:
            en_results = self.finbert.analyze_batch(english_texts)
            for r in en_results:
                r['language'] = 'en'
                r['method'] = 'finbert'
        
        # Process Hungarian with keywords (one by one)
        hu_results = []
        for text in hungarian_texts:
            r = self.keyword_analyzer._mock_sentiment_analysis(text, ticker_symbol)
            r['language'] = 'hu'
            r['method'] = 'keywords'
            hu_results.append(r)
        
        # Reconstruct original order
        all_results = [None] * len(texts)
        for i, idx in enumerate(indices['en']):
            all_results[idx] = en_results[i] if i < len(en_results) else None
        for i, idx in enumerate(indices['hu']):
            all_results[idx] = hu_results[i] if i < len(hu_results) else None
        
        return [r for r in all_results if r is not None]


# ==========================================
# USAGE EXAMPLES
# ==========================================

if __name__ == "__main__":
    print("=" * 70)
    print("🌐 Multilingual Sentiment Analyzer Test")
    print("=" * 70)
    
    # Test language detection
    print("\n🔍 Language Detection Test:\n")
    
    test_texts = [
        "Apple reports strong quarterly earnings",
        "Az OTP Bank növelte nettó nyereségét",
        "Tesla delivery numbers exceed expectations",
        "A MOL kiterjeszti finomítói kapacitását",
    ]
    
    for text in test_texts:
        lang = detect_language(text)
        emoji = "🇬🇧" if lang == 'en' else "🇭🇺"
        print(f"{emoji} {lang.upper()}: {text}")
    
    print("\n" + "=" * 70)
    
    # Test multilingual analyzer
    print("\n🧪 Multilingual Sentiment Test:\n")
    
    analyzer = MultilingualSentimentAnalyzer()
    
    mixed_texts = [
        ("Apple beats earnings expectations", 'AAPL'),
        ("Az OTP Bank erős negyedéves eredményt jelentett", 'OTP.BD'),
        ("Tesla faces production challenges", 'TSLA'),
        ("A MOL nyereség csökkenése aggasztó", 'MOL.BD'),
    ]
    
    for text, ticker in mixed_texts:
        result = analyzer.analyze_text(text, ticker)
        lang_flag = "🇬🇧" if result['language'] == 'en' else "🇭🇺"
        method = "🧠" if result['method'] == 'finbert' else "🔤"
        
        print(f"{lang_flag}{method} {result['label']:8s} {result['score']:+.3f} | {text[:50]}")
    
    print("\n" + "=" * 70)
    print("✅ Multilingual Sentiment Complete!")
