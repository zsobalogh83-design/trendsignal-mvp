"""
TrendSignal MVP - Sentiment Analysis Module
FinBERT-based sentiment analysis with corrected formula

Version: 1.0
Date: 2024-12-27
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from config import TrendSignalConfig, get_config


# ==========================================
# SENTIMENT ANALYSIS (FinBERT)
# ==========================================

class SentimentAnalyzer:
    """
    Sentiment analyzer using FinBERT
    
    Note: FinBERT will be loaded in Phase 2 (requires transformers library)
    For MVP/PoC: Using mock sentiment or simple keyword-based approach
    """
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
        self.model = None  # Will be loaded in Phase 2
        self.tokenizer = None
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text using FinBERT
        
        Args:
            text: News title or description
        
        Returns:
            {
                'score': -1.0 to +1.0,
                'confidence': 0.0 to 1.0,
                'label': 'positive' | 'neutral' | 'negative',
                'probabilities': {'positive': x, 'neutral': y, 'negative': z}
            }
        """
        # Phase 2: Load FinBERT model
        # from transformers import AutoTokenizer, AutoModelForSequenceClassification
        # self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        # self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        
        # For now: Mock implementation (replace with FinBERT in Phase 2)
        return self._mock_sentiment_analysis(text)
    
    def _mock_sentiment_analysis(self, text: str) -> Dict[str, float]:
        """
        Mock sentiment analysis (placeholder for FinBERT)
        
        In production, this will be replaced with actual FinBERT inference
        """
        text_lower = text.lower()
        
        # English + Hungarian keyword-based sentiment (temporary)
        positive_keywords = [
            # English
            'beat', 'exceed', 'growth', 'profit', 'upgrade', 'strong', 
            'positive', 'gain', 'rally', 'bullish', 'record', 'success',
            'improve', 'rise', 'surge', 'boom', 'optimistic', 'outperform',
            # Hungarian
            'növekedés', 'nyereség', 'profit', 'erős', 'pozitív', 'emelkedés',
            'sikeres', 'rekord', 'javulás', 'bővülés', 'fellendülés', 'optimista',
            'felminősítés', 'felértékelés', 'túlteljesít', 'meghaladta',
            'jó eredmény', 'pozitív', 'erősödik', 'felértékelődik'
        ]
        negative_keywords = [
            # English
            'miss', 'decline', 'loss', 'downgrade', 'weak', 'negative',
            'fall', 'drop', 'bearish', 'concern', 'risk', 'crisis',
            'disappoint', 'underperform', 'warning', 'trouble',
            # Hungarian
            'csökkenés', 'veszteség', 'gyenge', 'negatív', 'esés', 'zuhanás',
            'válság', 'probléma', 'aggály', 'kockázat', 'rossz', 'bukás',
            'leminősítés', 'alulteljesít', 'figyelmeztetés', 'gond',
            'visszaesés', 'gyengülés', 'leértékelés', 'romlás'
        ]
        
        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            # Neutral
            probs = {'positive': 0.33, 'neutral': 0.34, 'negative': 0.33}
        else:
            pos_prob = pos_count / total if total > 0 else 0.33
            neg_prob = neg_count / total if total > 0 else 0.33
            neu_prob = 1.0 - pos_prob - neg_prob
            probs = {'positive': pos_prob, 'neutral': neu_prob, 'negative': neg_prob}
        
        # ✅ CORRECTED FinBERT Formula (neutral is included!)
        sentiment_score = (probs['positive'] - probs['negative']) / (
            probs['positive'] + probs['neutral'] + probs['negative']
        )
        
        # Determine label
        if sentiment_score > 0.1:
            label = 'positive'
        elif sentiment_score < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        # Confidence (how certain we are)
        confidence = max(probs.values())
        
        return {
            'score': sentiment_score,
            'confidence': confidence,
            'label': label,
            'probabilities': probs
        }


# ==========================================
# DECAY MODEL
# ==========================================

def calculate_decay_weight(news_age_hours: float, config: TrendSignalConfig) -> float:
    """
    Calculate time-based decay weight
    
    Args:
        news_age_hours: Age of news in hours
        config: Configuration with decay weights
    
    Returns:
        Decay weight (0.0 to 1.0)
    """
    if news_age_hours < 2:
        return config.decay_weights['0-2h']
    elif news_age_hours < 6:
        return config.decay_weights['2-6h']
    elif news_age_hours < 12:
        return config.decay_weights['6-12h']
    elif news_age_hours < 24:
        return config.decay_weights['12-24h']
    else:
        return 0.0  # Expired


# ==========================================
# NEWS ITEM DATACLASS
# ==========================================

@dataclass
class NewsItem:
    """Individual news item"""
    title: str
    description: str
    url: str
    published_at: datetime
    source: str
    sentiment_score: float
    sentiment_confidence: float
    sentiment_label: str
    credibility: float = 0.80
    
    def get_age_hours(self, reference_time: Optional[datetime] = None) -> float:
        """Calculate news age in hours"""
        ref = reference_time or datetime.utcnow()
        age = ref - self.published_at
        return age.total_seconds() / 3600


# ==========================================
# AGGREGATED SENTIMENT RESULT
# ==========================================

@dataclass
class AggregatedSentiment:
    """Result of sentiment aggregation for a ticker"""
    weighted_avg: float  # -1.0 to +1.0
    confidence: float    # 0.0 to 1.0
    news_count: int
    time_distribution: Dict[str, Dict[str, float]]
    news_items: List[NewsItem]


# ==========================================
# SENTIMENT AGGREGATOR
# ==========================================

class SentimentAggregator:
    """Aggregate multiple news items with decay model"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
        self.analyzer = SentimentAnalyzer(config)
    
    def aggregate_sentiment(
        self,
        news_items: List[NewsItem],
        reference_time: Optional[datetime] = None
    ) -> AggregatedSentiment:
        """
        Aggregate sentiment from multiple news items with decay model
        
        Args:
            news_items: List of NewsItem objects
            reference_time: Reference time (default: now)
        
        Returns:
            AggregatedSentiment with weighted average and metadata
        """
        if not news_items:
            return AggregatedSentiment(
                weighted_avg=0.0,
                confidence=0.0,
                news_count=0,
                time_distribution={},
                news_items=[]
            )
        
        ref_time = reference_time or datetime.utcnow()
        
        # Calculate weighted sentiment
        weighted_sum = 0.0
        weight_sum = 0.0
        
        # Time distribution tracking
        time_buckets = {
            '0-2h': {'sentiments': [], 'count': 0},
            '2-6h': {'sentiments': [], 'count': 0},
            '6-12h': {'sentiments': [], 'count': 0},
            '12-24h': {'sentiments': [], 'count': 0},
        }
        
        for news in news_items:
            age_hours = news.get_age_hours(ref_time)
            
            # Skip news older than 24h
            if age_hours >= 24:
                continue
            
            # Calculate decay weight
            decay = calculate_decay_weight(age_hours, self.config)
            
            # Contextual weight (source credibility)
            context_weight = news.credibility
            
            # Final weight
            final_weight = decay * context_weight
            
            # Add to weighted sum
            weighted_sum += news.sentiment_score * final_weight
            weight_sum += final_weight
            
            # Track in time buckets
            bucket = self._get_time_bucket(age_hours)
            if bucket:
                time_buckets[bucket]['sentiments'].append(news.sentiment_score)
                time_buckets[bucket]['count'] += 1
        
        # Calculate weighted average
        weighted_avg = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        # Calculate time distribution averages
        time_dist = {}
        for bucket, data in time_buckets.items():
            if data['count'] > 0:
                time_dist[bucket] = {
                    'avg': np.mean(data['sentiments']),
                    'count': data['count']
                }
        
        # Calculate confidence
        confidence = self._calculate_confidence(news_items, time_dist)
        
        return AggregatedSentiment(
            weighted_avg=weighted_avg,
            confidence=confidence,
            news_count=len([n for n in news_items if n.get_age_hours(ref_time) < 24]),
            time_distribution=time_dist,
            news_items=news_items
        )
    
    def _get_time_bucket(self, age_hours: float) -> Optional[str]:
        """Get time bucket for given age"""
        if age_hours < 2:
            return '0-2h'
        elif age_hours < 6:
            return '2-6h'
        elif age_hours < 12:
            return '6-12h'
        elif age_hours < 24:
            return '12-24h'
        else:
            return None
    
    def _calculate_confidence(
        self,
        news_items: List[NewsItem],
        time_dist: Dict[str, Dict]
    ) -> float:
        """
        Calculate confidence in aggregated sentiment
        
        Factors:
        - News volume (more = higher)
        - Sentiment consistency (aligned = higher)
        - Source credibility (trusted = higher)
        - Recency (fresh = higher)
        """
        if not news_items:
            return 0.0
        
        # 1. Volume confidence (0-1)
        # More news = higher confidence (logarithmic scale)
        news_count = len(news_items)
        volume_conf = min(np.log1p(news_count) / np.log1p(10), 1.0)  # Max at 10 news
        
        # 2. Consistency confidence (0-1)
        # How aligned are the sentiments?
        sentiments = [n.sentiment_score for n in news_items]
        if len(sentiments) > 1:
            std_dev = np.std(sentiments)
            consistency_conf = max(0, 1.0 - std_dev)  # Lower std = higher conf
        else:
            consistency_conf = 0.5
        
        # 3. Credibility confidence (0-1)
        avg_credibility = np.mean([n.credibility for n in news_items])
        
        # 4. Recency confidence (0-1)
        # More fresh news = higher confidence
        if time_dist:
            fresh_count = time_dist.get('0-2h', {}).get('count', 0)
            recent_count = time_dist.get('2-6h', {}).get('count', 0)
            total_count = sum(d.get('count', 0) for d in time_dist.values())
            recency_conf = (fresh_count * 1.0 + recent_count * 0.7) / total_count if total_count > 0 else 0.5
        else:
            recency_conf = 0.5
        
        # Weighted average (using config weights)
        weights = self.config.__dict__.get('confidence_weights', {
            'news_volume': 0.30,
            'sentiment_consistency': 0.25,
            'technical_alignment': 0.25,  # Will be added in signal_generator
            'source_credibility': 0.20,
        })
        
        confidence = (
            volume_conf * weights.get('news_volume', 0.30) +
            consistency_conf * weights.get('sentiment_consistency', 0.25) +
            avg_credibility * weights.get('source_credibility', 0.20) +
            recency_conf * 0.25  # Recency factor
        )
        
        return min(confidence, 1.0)


# ==========================================
# USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    print("✅ Sentiment Analyzer Module Loaded")
    print("🧠 FinBERT formula: (pos - neg) / (pos + neu + neg)")
    print("⏱️ Decay model: 0-2h (100%), 2-6h (85%), 6-12h (60%), 12-24h (35%)")
    print("📊 Confidence factors: Volume, Consistency, Credibility, Recency")
