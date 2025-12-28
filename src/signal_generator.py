"""
TrendSignal MVP - Signal Generator Module  
Generates BUY/SELL/HOLD trading signals with dynamic configuration

Version: 1.2 - Robust DataFrame Handling
Date: 2024-12-28
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
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
        result = asdict(self)
        # Convert datetime to string
        if isinstance(result['timestamp'], datetime):
            result['timestamp'] = result['timestamp'].isoformat()
        return result
    
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
            print(f"   Entry:       ${self.entry_price:.2f}")
            if self.stop_loss:
                print(f"   Stop-Loss:   ${self.stop_loss:.2f} ({((self.stop_loss/self.entry_price-1)*100):+.2f}%)")
            if self.take_profit:
                print(f"   Take-Profit: ${self.take_profit:.2f} ({((self.take_profit/self.entry_price-1)*100):+.2f}%)")
            if self.risk_reward_ratio:
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
        """Initialize signal generator"""
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
            ticker_symbol: Ticker symbol
            ticker_name: Company name
            sentiment_data: Dict with weighted_avg, confidence, key_news
            technical_data: Dict with score, confidence, current_price, indicators
            risk_data: Dict with score, volatility, support/resistance
            news_count: Number of news items
        
        Returns:
            TradingSignal object
        """
        # ===== CRITICAL: RELOAD CONFIG =====
        from src.config import get_config
        self.config = get_config()
        if hasattr(self.config, 'reload'):
            self.config.reload()
        
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
        
        # ===== CALCULATE CONTRIBUTIONS =====
        sentiment_contribution = sentiment_score * sentiment_weight
        technical_contribution = technical_score * technical_weight
        risk_contribution = risk_score * risk_weight
        
        # ===== COMBINED SCORE =====
        combined_score = sentiment_contribution + technical_contribution + risk_contribution
        
        # Logging
        print(f"[{ticker_symbol}] Using weights: S={sentiment_weight:.2f}, T={technical_weight:.2f}, R={risk_weight:.2f}")
        print(f"[{ticker_symbol}] Scores: S={sentiment_score:.1f}, T={technical_score:.1f}, R={risk_score:.1f}")
        print(f"[{ticker_symbol}] Contributions: S={sentiment_contribution:.1f}, T={technical_contribution:.1f}, R={risk_contribution:.1f}")
        print(f"[{ticker_symbol}] COMBINED SCORE: {combined_score:.2f}")
        
        # ===== OVERALL CONFIDENCE =====
        overall_confidence = (
            sentiment_confidence * sentiment_weight +
            technical_confidence * technical_weight +
            0.5 * risk_weight
        )
        
        # ===== DETERMINE DECISION =====
        decision, strength = self._determine_decision(combined_score, overall_confidence)
        
        print(f"[{ticker_symbol}] DECISION: {strength} {decision} (Conf: {overall_confidence:.0%})")
        
        # ===== CALCULATE ENTRY/EXIT LEVELS =====
        current_price = technical_data.get("current_price")
        entry_price, stop_loss, take_profit, rr_ratio = self._calculate_levels(
            decision, current_price, technical_data, risk_data
        )
        
        # ===== BUILD REASONING =====
        reasoning = {
            "sentiment": {
                "score": sentiment_score,
                "contribution": sentiment_contribution,
                "confidence": sentiment_confidence,
                "key_news": sentiment_data.get("key_news", [])[:3]
            },
            "technical": {
                "score": technical_score,
                "contribution": technical_contribution,
                "confidence": technical_confidence,
                "key_signals": technical_data.get("key_signals", [])
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
        """Determine BUY/SELL/HOLD decision using DYNAMIC thresholds"""
        strong_buy_score = self.config.STRONG_BUY_SCORE
        strong_buy_conf = self.config.STRONG_BUY_CONFIDENCE
        moderate_buy_score = self.config.MODERATE_BUY_SCORE
        moderate_buy_conf = self.config.MODERATE_BUY_CONFIDENCE
        
        strong_sell_score = self.config.STRONG_SELL_SCORE
        strong_sell_conf = self.config.STRONG_SELL_CONFIDENCE
        moderate_sell_score = self.config.MODERATE_SELL_SCORE
        moderate_sell_conf = self.config.MODERATE_SELL_CONFIDENCE
        
        if combined_score >= strong_buy_score and confidence >= strong_buy_conf:
            return "BUY", "STRONG"
        elif combined_score >= moderate_buy_score and confidence >= moderate_buy_conf:
            return "BUY", "MODERATE"
        elif combined_score <= strong_sell_score and confidence >= strong_sell_conf:
            return "SELL", "STRONG"
        elif combined_score <= moderate_sell_score and confidence >= moderate_sell_conf:
            return "SELL", "MODERATE"
        else:
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
        technical_data: Dict,
        risk_data: Dict
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Calculate entry, stop-loss, take-profit levels"""
        if decision == "HOLD" or current_price is None:
            return None, None, None, None
        
        # Get data
        atr = technical_data.get("atr", current_price * 0.02)
        nearest_support = risk_data.get("nearest_support", current_price * 0.97)
        nearest_resistance = risk_data.get("nearest_resistance", current_price * 1.03)
        
        entry_price = current_price
        
        if "BUY" in decision:
            stop_loss = nearest_support - (atr * 1.5)
            stop_loss = max(stop_loss, current_price * 0.974)
            take_profit = nearest_resistance
        else:  # SELL
            stop_loss = nearest_resistance + (atr * 1.5)
            stop_loss = min(stop_loss, current_price * 1.026)
            take_profit = nearest_support
        
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
# BATCH SIGNAL GENERATION - ROBUST VERSION
# ==========================================

def generate_signals_for_tickers(
    tickers: List[Dict],
    sentiment_data_dict: Dict,
    technical_data_dict: Dict,
    config=None
) -> List[TradingSignal]:
    """
    Generate signals for multiple tickers with ROBUST error handling
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
            
            # ===== SENTIMENT AGGREGATION =====
            sentiment_data_raw = sentiment_data_dict.get(ticker_symbol, [])
            
            if isinstance(sentiment_data_raw, list) and len(sentiment_data_raw) > 0:
                print(f"📰 [{ticker_symbol}] Aggregating {len(sentiment_data_raw)} news items...")
                sentiment_data = aggregate_sentiment_from_news(sentiment_data_raw)
                print(f"  ✅ Sentiment: {sentiment_data['weighted_avg']:+.2f} (from {len(sentiment_data_raw)} news)")
            elif isinstance(sentiment_data_raw, dict):
                sentiment_data = sentiment_data_raw
            else:
                sentiment_data = {"weighted_avg": 0, "confidence": 0.5, "key_news": [], "news_count": 0}
            
            # ===== TECHNICAL CALCULATION =====
            technical_data_raw = technical_data_dict.get(ticker_symbol, {})
            
            if isinstance(technical_data_raw, pd.DataFrame) and len(technical_data_raw) > 50:
                print(f"📊 [{ticker_symbol}] Calculating technical from {len(technical_data_raw)} candles...")
                technical_data = calculate_technical_score(technical_data_raw, ticker_symbol)
            elif isinstance(technical_data_raw, dict) and 'score' in technical_data_raw:
                technical_data = technical_data_raw
            else:
                technical_data = {"score": 0, "confidence": 0.5, "current_price": None, "key_signals": []}
                print(f"  ⚠️ No technical data")
            
            # ===== RISK CALCULATION =====
            if technical_data.get("current_price") and technical_data.get("atr_pct"):
                risk_data = calculate_risk_score(technical_data, ticker_symbol)
            else:
                risk_data = {"score": 0, "volatility": 2.0, "nearest_support": None, "nearest_resistance": None}
                print(f"  ⚠️ No risk data")
            
            # ===== GENERATE SIGNAL =====
            signal = generator.generate_signal(
                ticker_symbol=ticker_symbol,
                ticker_name=ticker_name,
                sentiment_data=sentiment_data,
                technical_data=technical_data,
                risk_data=risk_data,
                news_count=sentiment_data.get("news_count", 0)
            )
            
            signals.append(signal)
            print(f"✅ Signal: {signal.strength} {signal.decision}")
            
        except Exception as e:
            logger.error(f"Error generating signal for {ticker_symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    return signals


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def aggregate_sentiment_from_news(news_items: List) -> Dict:
    """Aggregate sentiment from NewsItem list with decay model"""
    from src.config import get_config
    
    config = get_config()
    decay_weights = config.decay_weights
    
    weighted_scores = []
    weights_sum = 0
    confidences = []
    
    now = datetime.now(timezone.utc)
    
    for news_item in news_items:
        # Calculate age
        news_age_hours = (now - news_item.published_at).total_seconds() / 3600
        
        # Get decay weight
        if news_age_hours < 2:
            decay = decay_weights.get('0-2h', 1.0)
        elif news_age_hours < 6:
            decay = decay_weights.get('2-6h', 0.85)
        elif news_age_hours < 12:
            decay = decay_weights.get('6-12h', 0.60)
        elif news_age_hours < 24:
            decay = decay_weights.get('12-24h', 0.35)
        else:
            decay = 0.0
        
        if decay > 0:
            final_weight = decay * news_item.credibility
            weighted_scores.append(news_item.sentiment_score * final_weight)
            weights_sum += final_weight
            confidences.append(news_item.sentiment_confidence)
    
    # Calculate weighted average
    weighted_avg = sum(weighted_scores) / weights_sum if weights_sum > 0 else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    
    return {
        "weighted_avg": weighted_avg,
        "confidence": avg_confidence,
        "key_news": [item.title for item in news_items[:3]],
        "news_count": len(news_items)
    }


def calculate_technical_score(df: pd.DataFrame, ticker_symbol: str) -> Dict:
    """Calculate technical score from price DataFrame - ROBUST version"""
    try:
        # Normalize column names to lowercase
        df = df.copy()
        df.columns = [str(col).lower().strip() for col in df.columns]
        
        print(f"  📋 DataFrame columns: {list(df.columns)[:5]}... ({len(df.columns)} total)")
        
        # Check for required columns (flexible naming)
        close_col = None
        high_col = None
        low_col = None
        
        for col in df.columns:
            if 'close' in col or col == '4. close':
                close_col = col
            elif 'high' in col or col == '2. high':
                high_col = col
            elif 'low' in col or col == '3. low':
                low_col = col
        
        if not close_col:
            print(f"  ❌ No 'close' column found in: {list(df.columns)}")
            return {"score": 0, "confidence": 0.5, "current_price": None, "key_signals": ["No close price"]}
        
        print(f"  ✅ Using columns: close={close_col}, high={high_col}, low={low_col}")
        
        # Calculate indicators
        df['sma_20'] = df[close_col].rolling(20).mean()
        df['sma_50'] = df[close_col].rolling(50).mean()
        
        # RSI
        delta = df[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Latest values
        current = df.iloc[-1]
        
        # Technical score
        tech_score = 0
        key_signals = []
        
        # SMA trend
        if pd.notna(current['sma_20']) and pd.notna(current['sma_50']):
            if current[close_col] > current['sma_20']:
                tech_score += 25
                key_signals.append("Price > SMA20")
            else:
                tech_score -= 15
            
            if current[close_col] > current['sma_50']:
                tech_score += 20
                key_signals.append("Price > SMA50")
            else:
                tech_score -= 10
            
            if current['sma_20'] > current['sma_50']:
                tech_score += 15
                key_signals.append("Golden Cross")
            else:
                tech_score -= 15
                key_signals.append("Death Cross")
        
        # RSI
        if pd.notna(current['rsi']):
            rsi = current['rsi']
            if 45 < rsi < 55:
                tech_score += 20
                key_signals.append(f"RSI neutral ({rsi:.1f})")
            elif 55 <= rsi < 70:
                tech_score += 30
                key_signals.append(f"RSI bullish ({rsi:.1f})")
            elif 30 < rsi <= 45:
                tech_score += 10
            elif rsi >= 70:
                tech_score -= 20
                key_signals.append(f"RSI overbought ({rsi:.1f})")
            elif rsi <= 30:
                tech_score -= 20
                key_signals.append(f"RSI oversold ({rsi:.1f})")
        
        # ATR
        if high_col and low_col:
            high_low = df[high_col] - df[low_col]
            atr = high_low.rolling(14).mean().iloc[-1]
            atr_pct = (atr / current[close_col]) * 100
            
            # Support/Resistance
            recent_lows = df[low_col].tail(20)
            recent_highs = df[high_col].tail(20)
            nearest_support = float(recent_lows.min())
            nearest_resistance = float(recent_highs.max())
        else:
            atr = current[close_col] * 0.02
            atr_pct = 2.0
            nearest_support = current[close_col] * 0.97
            nearest_resistance = current[close_col] * 1.03
        
        result = {
            "score": max(-100, min(100, tech_score)),
            "confidence": 0.70,
            "current_price": float(current[close_col]),
            "key_signals": key_signals,
            "atr": float(atr),
            "atr_pct": float(atr_pct),
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "rsi": float(current['rsi']) if pd.notna(current['rsi']) else None,
            "sma_20": float(current['sma_20']) if pd.notna(current['sma_20']) else None,
            "sma_50": float(current['sma_50']) if pd.notna(current['sma_50']) else None
        }
        
        print(f"  ✅ Technical: {tech_score:.1f} | RSI: {current['rsi']:.1f} | Price: ${current[close_col]:.2f}")
        
        return result
        
    except Exception as e:
        print(f"  ❌ Technical calculation error: {e}")
        import traceback
        traceback.print_exc()
        return {"score": 0, "confidence": 0.5, "current_price": None, "key_signals": []}


def calculate_risk_score(technical_data: Dict, ticker_symbol: str) -> Dict:
    """Calculate risk score from technical data"""
    try:
        atr_pct = technical_data.get("atr_pct", 2.0)
        current_price = technical_data["current_price"]
        nearest_support = technical_data.get("nearest_support", current_price * 0.97)
        nearest_resistance = technical_data.get("nearest_resistance", current_price * 1.03)
        
        # Risk score
        risk_score = 50
        
        # Volatility
        if atr_pct < 2.0:
            risk_score += 30
        elif atr_pct < 3.0:
            risk_score += 15
        elif atr_pct > 5.0:
            risk_score -= 30
        
        # Distance from support
        support_dist_pct = ((current_price - nearest_support) / current_price) * 100
        if support_dist_pct < 3:
            risk_score += 20
        
        print(f"  ✅ Risk: {risk_score:.1f} | ATR: {atr_pct:.2f}% | Supp dist: {support_dist_pct:.2f}%")
        
        return {
            "score": max(-100, min(100, risk_score)),
            "volatility": atr_pct,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance
        }
        
    except Exception as e:
        print(f"  ❌ Risk calculation error: {e}")
        return {"score": 0, "volatility": 2.0, "nearest_support": None, "nearest_resistance": None}


# ==========================================
# MOCK FUNCTIONS FOR TESTING
# ==========================================

def create_mock_signal(ticker_symbol: str = "TEST") -> TradingSignal:
    """Create mock signal for testing"""
    return TradingSignal(
        ticker_symbol=ticker_symbol,
        ticker_name="Test Stock",
        timestamp=datetime.now(),
        decision="BUY",
        strength="STRONG",
        combined_score=72.5,
        sentiment_score=68.0,
        technical_score=58.5,
        risk_score=65.0,
        overall_confidence=0.81,
        sentiment_confidence=0.82,
        technical_confidence=0.70,
        entry_price=100.0,
        stop_loss=97.4,
        take_profit=105.0,
        risk_reward_ratio=2.5,
        news_count=8
    )
