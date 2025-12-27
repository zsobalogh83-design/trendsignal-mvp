"""
TrendSignal MVP - FinBERT Sentiment Analyzer
Real FinBERT implementation for financial sentiment analysis

Version: 2.0 (FinBERT Integration)
Date: 2024-12-27
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from typing import Dict, Optional
import warnings
warnings.filterwarnings('ignore')


# ==========================================
# FINBERT SENTIMENT ANALYZER
# ==========================================

class FinBERTAnalyzer:
    """
    Real FinBERT-based sentiment analyzer
    
    Model: ProsusAI/finbert (fine-tuned BERT for financial sentiment)
    """
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize FinBERT model
        
        Args:
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        print("🧠 Loading FinBERT model...")
        
        # Auto-detect device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        print(f"   Device: {self.device}")
        
        # Load tokenizer and model
        model_name = "ProsusAI/finbert"
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            print(f"   ✅ FinBERT loaded successfully!")
            
        except Exception as e:
            print(f"   ❌ Error loading FinBERT: {e}")
            raise
    
    def analyze(self, text: str, max_length: int = 512) -> Dict[str, float]:
        """
        Analyze sentiment using FinBERT
        
        Args:
            text: News text (title + description)
            max_length: Maximum token length
        
        Returns:
            {
                'score': -1.0 to +1.0 (normalized),
                'confidence': 0.0 to 1.0,
                'label': 'positive' | 'neutral' | 'negative',
                'probabilities': {'positive': x, 'neutral': y, 'negative': z}
            }
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            max_length=max_length,
            padding=True
        ).to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1)[0]
        
        # FinBERT outputs: [positive, negative, neutral]
        # Note: Order is different from typical sentiment models!
        pos_prob = probs[0].item()
        neg_prob = probs[1].item()
        neu_prob = probs[2].item()
        
        # ✅ CORRECTED FinBERT Formula (neutral is included!)
        sentiment_score = (pos_prob - neg_prob) / (pos_prob + neu_prob + neg_prob)
        
        # Determine label
        if pos_prob > neg_prob and pos_prob > neu_prob:
            label = 'positive'
        elif neg_prob > pos_prob and neg_prob > neu_prob:
            label = 'negative'
        else:
            label = 'neutral'
        
        # Confidence is the max probability
        confidence = max(pos_prob, neg_prob, neu_prob)
        
        return {
            'score': sentiment_score,
            'confidence': confidence,
            'label': label,
            'probabilities': {
                'positive': pos_prob,
                'neutral': neu_prob,
                'negative': neg_prob
            }
        }
    
    def analyze_batch(self, texts: list, max_length: int = 512) -> list:
        """
        Analyze multiple texts in batch (more efficient)
        
        Args:
            texts: List of text strings
            max_length: Maximum token length
        
        Returns:
            List of sentiment dictionaries
        """
        # Tokenize batch
        inputs = self.tokenizer(
            texts,
            return_tensors='pt',
            truncation=True,
            max_length=max_length,
            padding=True
        ).to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1)
        
        results = []
        for i in range(len(texts)):
            pos_prob = probs[i][0].item()
            neg_prob = probs[i][1].item()
            neu_prob = probs[i][2].item()
            
            sentiment_score = (pos_prob - neg_prob) / (pos_prob + neu_prob + neg_prob)
            
            if pos_prob > neg_prob and pos_prob > neu_prob:
                label = 'positive'
            elif neg_prob > pos_prob and neg_prob > neu_prob:
                label = 'negative'
            else:
                label = 'neutral'
            
            confidence = max(pos_prob, neg_prob, neu_prob)
            
            results.append({
                'score': sentiment_score,
                'confidence': confidence,
                'label': label,
                'probabilities': {
                    'positive': pos_prob,
                    'neutral': neu_prob,
                    'negative': neg_prob
                }
            })
        
        return results


# ==========================================
# WRAPPER FOR BACKWARD COMPATIBILITY
# ==========================================

class SentimentAnalyzerFinBERT:
    """
    Wrapper for FinBERT that matches original SentimentAnalyzer interface
    """
    
    def __init__(self, config=None, ticker_symbol=None):
        self.config = config
        self.ticker_symbol = ticker_symbol
        
        # Initialize FinBERT (singleton pattern)
        if not hasattr(SentimentAnalyzerFinBERT, '_finbert_instance'):
            SentimentAnalyzerFinBERT._finbert_instance = FinBERTAnalyzer()
        
        self.finbert = SentimentAnalyzerFinBERT._finbert_instance
    
    def analyze_text(self, text: str, ticker_symbol: Optional[str] = None) -> Dict[str, float]:
        """
        Analyze text sentiment (matches original interface)
        
        Args:
            text: News text
            ticker_symbol: Optional ticker (not used in FinBERT, for compatibility)
        
        Returns:
            Sentiment dictionary
        """
        return self.finbert.analyze(text)


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧠 FinBERT Sentiment Analyzer Test")
    print("=" * 70)
    
    # Initialize
    analyzer = FinBERTAnalyzer()
    
    # Test cases
    test_texts = [
        "Apple reports record Q4 earnings, beating analyst expectations significantly",
        "Tesla faces production delays and supply chain disruptions",
        "Microsoft announces new cloud partnership",
        "Company maintains steady performance in line with forecasts",
    ]
    
    print("\n📊 Test Results:\n")
    
    for i, text in enumerate(test_texts):
        result = analyzer.analyze(text)
        
        print(f"{i+1}. Text: {text[:60]}...")
        print(f"   Score: {result['score']:+.3f} | Label: {result['label']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Probs: pos={result['probabilities']['positive']:.3f}, "
              f"neu={result['probabilities']['neutral']:.3f}, "
              f"neg={result['probabilities']['negative']:.3f}")
        print()
    
    print("=" * 70)
    print("✅ FinBERT Test Complete!")
