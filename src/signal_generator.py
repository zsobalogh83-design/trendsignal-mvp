"""
TrendSignal MVP - Signal Generator Module
Combines sentiment and technical analysis to generate trading signals

Version: 1.1 - Dynamic Config Support
Date: 2024-12-28
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


# ==========================================
# DATA CLASSES
# ==========================================

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    ticker_symbol: str
    ticker_name: str
    timestamp: datetime
    
    # Decision
    decision: str  # BUY, SELL, HOLD
    strength: str  # STRONG, MODERATE, WEAK, NEUTRAL
    
    # Scores
    combined_score: float
    sentiment_score: float
    technical_score: float
    risk_score: float
    
    # Confidence
    overall_confidence: float
    sentiment_confidence: float
    technical_confidence: float
    
    # Entry/Exit levels
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Supporting data
    news_count: int = 0
    reasoning: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def display(self):
        """Pretty print the signal"""
        print("\n" + "=" * 70)
        print(f"🎯 TRADING SIGNAL: {self.ticker_symbol} - {self.ticker_name}")
        print("=" * 70)
        
        # Decision with color
        decision_emoji = "🟢" if "BUY" in self.decision else "🔴" if "SELL" in self.decision else "⚪"
        print(f"\n{decision_emoji} Decision: {self.strength} {self.decision}")
        print(f"   Combined Score: {self.combined_score:+.2f}")
        print(f"   Confidence: {self.overall_confidence:.0%}")
        
        # Component breakdown
        print(f"\n📊 Score Breakdown:")
        print(f"   Sentiment: {self.sentiment_score:+7.2f} (Conf: {self.sentiment_confidence:.0%})")
        print(f"   Technical: {self.technical_score:+7.2f} (Conf: {self.technical_confidence:.0%})")
        print(f"   Risk:      {self.risk_score:+7.2f}")
        
        # Entry/Exit
        if self.entry_price:
            print(f"\n💰 Entry/Exit Levels:")
            print(f"   Entry:       {self.entry_price:.2f}")
            print(f"   Stop-Loss:   {self.stop_loss:.2f} ({((self.stop_loss/self.entry_price-1)*100):+.2f}%)")
            print(f"   Take-Profit: {self.take_profit:.2f} ({((self.take_profit/self.entry_price-1)*100):+.2f}%)")
            print(f"   R:R Ratio:   1:{self.risk_reward_ratio:.2f}")
        
        print(f"\n📰 Based on {self.news_count} news items")
        print(f"⏰ Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70 + "\n")


# ==========================================
# SIGNAL GENERATOR CLASS
# ==========================================

class SignalGenerator:
    """
    Generate trading signals from sentiment and technical analysis
    WITH DYNAMIC CONFIG SUPPORT
    """
    
    def __init__(self, config=None):
        """
        Initialize signal generator
        
        Args:
            config: TrendSignalConfig instance (optional, uses default if None)
        """
        if config is None:
            from src.config import get_config
            self.config = get_config()
        else:
            self.config = config
        
        logger.info("SignalGenerator initialized")
    
    def generate_signal(
        self,
        ticker_symbol: str,
        ticker_name: str,
        sentiment_data: Dict,
        technical_data: Dict,
        risk_data: Dict,
        news_count: int = 0
    ) -> TradingSignal:
        """
        Generate trading signal with DYNAMIC config weights
        
        Args:
            ticker_symbol: Ticker symbol (e.g., "TSLA")
            ticker_name: Company name (e.g., "Tesla Inc")
            sentiment_data: Dict with weighted_avg, confidence, key_news
            technical_data: Dict with score, confidence, current_price, indicators
            risk_data: Dict with score, volatility, support/resistance
            news_count: Number of news items analyzed
        
        Returns:
            TradingSignal object
        """
        # ===== CRITICAL: RELOAD CONFIG =====
        from src.config import get_config
        self.config = get_config()
        self.config.reload()  # Reload from file
        
        # ===== EXTRACT COMPONENT SCORES =====
        sentiment_score = sentiment_data.get("weighted_avg", 0) * 100  # -100 to +100
        technical_score = technical_data.get("score", 0)  # -100 to +100
        risk_score = risk_data.get("score", 0)  # -100 to +100
        
        # Extract confidences
        sentiment_confidence = sentiment_data.get("confidence", 0.5)
        technical_confidence = technical_data.get("confidence", 0.5)
        
        # ===== DYNAMIC WEIGHTS FROM CONFIG =====
        sentiment_weight = self.config.SENTIMENT_WEIGHT
        technical_weight = self.config.TECHNICAL_WEIGHT
        risk_weight = self.config.RISK_WEIGHT
        
        # Log weights being used
        print(f"[{ticker_symbol}] Using weights: S={sentiment_weight:.2f}, T={technical_weight:.2f}, R={risk_weight:.2f}")
        
        # ===== CALCULATE CONTRIBUTIONS =====
        sentiment_contribution = sentiment_score * sentiment_weight
        technical_contribution = technical_score * technical_weight
        risk_contribution = risk_score * risk_weight
        
        # ===== COMBINED SCORE =====
        combined_score = sentiment_contribution + technical_contribution + risk_contribution
        
        # Debug logging
        print(f"[{ticker_symbol}] Scores: S={sentiment_score:.1f}, T={technical_score:.1f}, R={risk_score:.1f}")
        print(f"[{ticker_symbol}] Contributions: S={sentiment_contribution:.1f}, T={technical_contribution:.1f}, R={risk_contribution:.1f}")
        print(f"[{ticker_symbol}] COMBINED SCORE: {combined_score:.2f}")
        
        # ===== OVERALL CONFIDENCE =====
        overall_confidence = (
            sentiment_confidence * sentiment_weight +
            technical_confidence * technical_weight +
            0.5 * risk_weight  # Risk has implicit 0.5 confidence
        )
        
        # ===== DETERMINE DECISION =====
        decision, strength = self._determine_decision(combined_score, overall_confidence)
        
        print(f"[{ticker_symbol}] DECISION: {strength} {decision} (Conf: {overall_confidence:.0%})")
        
        # ===== CALCULATE ENTRY/EXIT LEVELS =====
        current_price = technical_data.get("current_price")
        entry_price, stop_loss, take_profit, rr_ratio = self._calculate_levels(
            decision, current_price, technical_data
        )
        
        # ===== BUILD REASONING =====
        reasoning = {
            "sentiment": {
                "score": sentiment_score,
                "contribution": sentiment_contribution,
                "confidence": sentiment_confidence,
                "key_news": sentiment_data.get("key_news", [])[:3]  # Top 3 news
            },
            "technical": {
                "score": technical_score,
                "contribution": technical_contribution,
                "confidence": technical_confidence,
                "key_indicators": technical_data.get("key_signals", [])
            },
            "risk": {
                "score": risk_score,
                "contribution": risk_contribution,
                "volatility": risk_data.get("volatility", "N/A"),
                "support_resistance": {
                    "support": risk_data.get("nearest_support"),
                    "resistance": risk_data.get("nearest_resistance")
                }
            }
        }
        
        # ===== CREATE SIGNAL OBJECT =====
        signal = TradingSignal(
            ticker_symbol=ticker_symbol,
            ticker_name=ticker_name,
            timestamp=datetime.now(),
            decision=decision,
            strength=strength,
            combined_score=round(combined_score, 2),
            sentiment_score=round(sentiment_score, 2),
            technical_score=round(technical_score, 2),
            risk_score=round(risk_score, 2),
            overall_confidence=round(overall_confidence, 3),
            sentiment_confidence=round(sentiment_confidence, 3),
            technical_confidence=round(technical_confidence, 3),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            news_count=news_count,
            reasoning=reasoning
        )
        
        return signal
    
    def _determine_decision(self, combined_score: float, confidence: float) -> Tuple[str, str]:
        """
        Determine BUY/SELL/HOLD decision using DYNAMIC thresholds from config
        
        Returns:
            Tuple of (decision, strength)
        """
        # Get thresholds from config
        strong_buy_score = self.config.STRONG_BUY_SCORE
        strong_buy_conf = self.config.STRONG_BUY_CONFIDENCE
        moderate_buy_score = self.config.MODERATE_BUY_SCORE
        moderate_buy_conf = self.config.MODERATE_BUY_CONFIDENCE
        
        strong_sell_score = self.config.STRONG_SELL_SCORE
        strong_sell_conf = self.config.STRONG_SELL_CONFIDENCE
        moderate_sell_score = self.config.MODERATE_SELL_SCORE
        moderate_sell_conf = self.config.MODERATE_SELL_CONFIDENCE
        
        # Decision logic
        if combined_score >= strong_buy_score and confidence >= strong_buy_conf:
            return "BUY", "STRONG"
        
        elif combined_score >= moderate_buy_score and confidence >= moderate_buy_conf:
            return "BUY", "MODERATE"
        
        elif combined_score <= strong_sell_score and confidence >= strong_sell_conf:
            return "SELL", "STRONG"
        
        elif combined_score <= moderate_sell_score and confidence >= moderate_sell_conf:
            return "SELL", "MODERATE"
        
        else:
            # Weak signals or HOLD
            if combined_score > 0 and combined_score < moderate_buy_score:
                return "BUY", "WEAK"
            elif combined_score < 0 and combined_score > moderate_sell_score:
                return "SELL", "WEAK"
            else:
                return "HOLD", "NEUTRAL"
    
    def _calculate_levels(
        self,
        decision: str,
        current_price: Optional[float],
        technical_data: Dict
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Calculate entry, stop-loss, take-profit levels
        
        Returns:
            Tuple of (entry_price, stop_loss, take_profit, risk_reward_ratio)
        """
        if decision == "HOLD" or current_price is None:
            return None, None, None, None
        
        # Get ATR
        atr = technical_data.get("atr", current_price * 0.02)
        
        # Get support/resistance
        nearest_support = technical_data.get("nearest_support", current_price * 0.97)
        nearest_resistance = technical_data.get("nearest_resistance", current_price * 1.03)
        
        entry_price = current_price
        
        if "BUY" in decision:
            # Stop-loss: below support
            stop_loss = nearest_support - (atr * self.config.stop_loss_atr_mult)
            stop_loss = max(stop_loss, current_price * 0.974)  # Max 2.6% loss
            
            # Take-profit: at resistance
            take_profit = nearest_resistance
            
        else:  # SELL
            # Stop-loss: above resistance
            stop_loss = nearest_resistance + (atr * self.config.stop_loss_atr_mult)
            stop_loss = min(stop_loss, current_price * 1.026)  # Max 2.6% loss
            
            # Take-profit: at support
            take_profit = nearest_support
        
        # Calculate R:R ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        return (
            round(entry_price, 2),
            round(stop_loss, 2),
            round(take_profit, 2),
            round(rr_ratio, 2)
        )


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def create_mock_signal(ticker_symbol: str = "TEST", ticker_name: str = "Test Stock") -> TradingSignal:
    """Create a mock signal for testing"""
    return TradingSignal(
        ticker_symbol=ticker_symbol,
        ticker_name=ticker_name,
        timestamp=datetime.now(),
        decision="BUY",
        strength="STRONG",
        combined_score=72.5,
        sentiment_score=68.0,
        technical_score=58.5,
        risk_score=45.0,
        overall_confidence=0.81,
        sentiment_confidence=0.82,
        technical_confidence=0.68,
        entry_price=100.0,
        stop_loss=97.4,
        take_profit=105.0,
        risk_reward_ratio=1.92,
        news_count=8,
        reasoning={
            "sentiment": {"key_news": ["Positive earnings", "Analyst upgrade"]},
            "technical": {"key_indicators": ["Golden Cross", "RSI bullish"]},
            "risk": {"volatility": "Low"}
        }
    )


# ==========================================
# BATCH SIGNAL GENERATION
# ==========================================

def generate_signals_for_tickers(
    tickers: List[Dict],
    sentiment_data_dict: Dict,
    technical_data_dict: Dict,
    config=None
) -> List[TradingSignal]:
    """
    Generate signals for multiple tickers
    
    Args:
        tickers: List of ticker dicts with 'symbol' and 'name'
        sentiment_data_dict: Dict mapping ticker_symbol -> sentiment_data
        technical_data_dict: Dict mapping ticker_symbol -> technical_data
        config: TrendSignalConfig instance (optional)
    
    Returns:
        List of TradingSignal objects
    """
    generator = SignalGenerator(config)
    signals = []
    
    for ticker in tickers:
        try:
            ticker_symbol = ticker['symbol']
            ticker_name = ticker.get('name', ticker_symbol)
            
            print(f"\n{'='*60}")
            print(f"Generating signal for {ticker_symbol}...")
            print(f"{'='*60}")
            
            # Get sentiment data from dict
            sentiment_data_raw = sentiment_data_dict.get(ticker_symbol, {})
            
            # Handle if sentiment_data is a list (news items) or dict (aggregated)
            if isinstance(sentiment_data_raw, list):
                # It's a list of news items - create aggregated structure
                sentiment_data = {
                    "weighted_avg": 0,
                    "confidence": 0.5,
                    "key_news": [],
                    "news_count": len(sentiment_data_raw)
                }
            elif isinstance(sentiment_data_raw, dict):
                # It's already aggregated
                sentiment_data = sentiment_data_raw
            else:
                # Fallback
                sentiment_data = {
                    "weighted_avg": 0,
                    "confidence": 0.5,
                    "key_news": [],
                    "news_count": 0
                }
            
            # Get technical data from dict
            technical_data_raw = technical_data_dict.get(ticker_symbol, {})
            
            # Handle if technical_data is a list or dict
            if isinstance(technical_data_raw, list):
                # Shouldn't happen, but handle gracefully
                technical_data = {
                    "score": 0,
                    "confidence": 0.5,
                    "current_price": None,
                    "key_signals": []
                }
            elif isinstance(technical_data_raw, dict):
                technical_data = technical_data_raw
            else:
                technical_data = {
                    "score": 0,
                    "confidence": 0.5,
                    "current_price": None,
                    "key_signals": []
                }
            
            # Calculate risk score (basic implementation)
            risk_data = {
                "score": 0,  # Neutral by default
                "volatility": technical_data.get("atr_pct", 2.0),
                "nearest_support": technical_data.get("nearest_support"),
                "nearest_resistance": technical_data.get("nearest_resistance")
            }
            
            # Generate signal
            signal = generator.generate_signal(
                ticker_symbol=ticker_symbol,
                ticker_name=ticker_name,
                sentiment_data=sentiment_data,
                technical_data=technical_data,
                risk_data=risk_data,
                news_count=sentiment_data.get("news_count", 0)
            )
            
            signals.append(signal)
            print(f"✅ Signal generated: {signal.strength} {signal.decision}")
            
        except Exception as e:
            logger.error(f"Error generating signal for {ticker.get('symbol', 'UNKNOWN')}: {e}")
            import traceback
            traceback.print_exc()
    
    return signals


if __name__ == "__main__":
    # Test signal generation
    print("Testing Signal Generator...")
    
    generator = SignalGenerator()
    
    # Mock data
    sentiment_data = {
        "weighted_avg": 0.68,
        "confidence": 0.82,
        "key_news": ["Q3 earnings beat", "Analyst upgrade"]
    }
    
    technical_data = {
        "score": 58.5,
        "confidence": 0.68,
        "current_price": 195.50,
        "atr": 5.2,
        "nearest_support": 190.0,
        "nearest_resistance": 205.0,
        "key_signals": ["Golden Cross", "RSI: 58"]
    }
    
    risk_data = {
        "score": 45.0,
        "volatility": 2.6,
        "nearest_support": 190.0,
        "nearest_resistance": 205.0
    }
    
    signal = generator.generate_signal(
        ticker_symbol="TSLA",
        ticker_name="Tesla Inc",
        sentiment_data=sentiment_data,
        technical_data=technical_data,
        risk_data=risk_data,
        news_count=8
    )
    
    signal.display()
