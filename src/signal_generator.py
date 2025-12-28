"""
TrendSignal MVP - Signal Generator Module
Combines sentiment and technical analysis to generate trading signals

Version: 1.0
Date: 2024-12-27
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict

from config import TrendSignalConfig, get_config
from sentiment_analyzer import SentimentAggregator, AggregatedSentiment, NewsItem
from technical_analyzer import TechnicalAnalyzer, TechnicalAnalysisResult


# ==========================================
# TRADING SIGNAL DATACLASS
# ==========================================

@dataclass
class TradingSignal:
    """Complete trading signal for a ticker"""
    
    # Ticker info
    ticker_symbol: str
    ticker_name: str
    timestamp: datetime
    
    # Decision
    decision: str  # 'BUY', 'SELL', 'HOLD'
    strength: str  # 'STRONG', 'MODERATE', 'WEAK'
    
    # Scores
    combined_score: float  # -100 to +100
    sentiment_score: float  # -100 to +100
    technical_score: float  # -100 to +100
    risk_score: float  # -100 to +100
    
    # Confidence
    overall_confidence: float  # 0.0 to 1.0
    sentiment_confidence: float
    technical_confidence: float
    
    # Entry/Exit levels
    current_price: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    
    # Metadata
    news_count: int
    sentiment_data: Optional[AggregatedSentiment]
    technical_data: Optional[TechnicalAnalysisResult]
    
    # Reasoning
    reasoning: Dict[str, any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def display(self):
        """Display signal in human-readable format"""
        print("=" * 70)
        print(f"📊 {self.ticker_symbol} - {self.ticker_name}")
        print("=" * 70)
        print()
        
        # Decision
        emoji = "🟢" if "BUY" in self.decision else "🔴" if "SELL" in self.decision else "⚪"
        print(f"{emoji} {self.strength} {self.decision}")
        print()
        
        # Scores
        print(f"Combined Score: {self.combined_score:+.1f}  |  Confidence: {self.overall_confidence:.0%}")
        print(f"{'█' * int(abs(self.combined_score)/5)}{'░' * (20-int(abs(self.combined_score)/5))}")
        print()
        
        # Breakdown
        print("📊 Score Breakdown:")
        print(f"  Sentiment: {self.sentiment_score:+6.1f}  (weight: 70%)")
        print(f"  Technical: {self.technical_score:+6.1f}  (weight: 20%)")
        print(f"  Risk:      {self.risk_score:+6.1f}  (weight: 10%)")
        print()
        
        # Entry/Exit
        print("💰 Entry & Exit Levels:")
        print(f"  Current:     {self.current_price:.2f}")
        print(f"  Entry:       {self.entry_price:.2f}")
        print(f"  Stop-Loss:   {self.stop_loss:.2f}  ({((self.stop_loss-self.entry_price)/self.entry_price*100):+.1f}%)")
        print(f"  Take-Profit: {self.take_profit:.2f}  ({((self.take_profit-self.entry_price)/self.entry_price*100):+.1f}%)")
        print(f"  R:R Ratio:   1:{self.risk_reward_ratio:.1f}")
        print()
        
        # News summary
        print(f"📰 News: {self.news_count} items (last 24h)")
        if self.sentiment_data and self.sentiment_data.time_distribution:
            for bucket, data in self.sentiment_data.time_distribution.items():
                print(f"  {bucket:8s}: avg {data['avg']:+.2f}  (count: {data['count']})")
        print()
        
        # Technical summary
        if self.technical_data and self.technical_data.signals:
            print("📈 Technical Signals:")
            for key, signal in self.technical_data.signals.items():
                print(f"  • {signal}")
        
        print()
        print("=" * 70)


# ==========================================
# SIGNAL GENERATOR
# ==========================================

class SignalGenerator:
    """Generate trading signals from sentiment and technical analysis"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
        self.sentiment_aggregator = SentimentAggregator(config)
        self.technical_analyzer = TechnicalAnalyzer(config)
    
    def generate_signal(
        self,
        ticker_symbol: str,
        ticker_name: str,
        news_items: List[NewsItem],
        price_df: pd.DataFrame
    ) -> TradingSignal:
        """
        Generate complete trading signal
        
        Args:
            ticker_symbol: Stock ticker
            ticker_name: Company name
            news_items: List of news items
            price_df: DataFrame with OHLC data
        
        Returns:
            TradingSignal object
        """
        # 1. Aggregate sentiment
        sentiment_result = self.sentiment_aggregator.aggregate_sentiment(news_items)
        
        # 2. Perform technical analysis
        technical_result = self.technical_analyzer.analyze(price_df)
        
        # 3. Calculate risk score
        risk_score = self._calculate_risk_score(price_df, technical_result)
        
        # 4. Calculate combined score
        sentiment_score_scaled = sentiment_result.weighted_avg * 100  # -100 to +100
        technical_score_scaled = technical_result.score  # Already -100 to +100
        
        combined_score = (
            sentiment_score_scaled * self.config.sentiment_weight +
            technical_score_scaled * self.config.technical_weight +
            risk_score * self.config.risk_weight
        )
        
        # 5. Calculate overall confidence
        overall_confidence = (
            sentiment_result.confidence * self.config.sentiment_weight +
            technical_result.confidence * self.config.technical_weight +
            0.70 * self.config.risk_weight  # Risk has fixed confidence for now
        )
        
        # 6. Determine decision
        decision, strength = self._determine_decision(combined_score, overall_confidence)
        
        # 7. Calculate entry/exit levels
        current_price = price_df['Close'].iloc[-1]
        entry_price = current_price
        stop_loss, take_profit, rr_ratio = self._calculate_levels(
            decision, entry_price, technical_result
        )
        
        # 8. Generate reasoning
        reasoning = self._generate_reasoning(
            sentiment_result, technical_result, risk_score, decision
        )
        
        # 9. Create signal
        signal = TradingSignal(
            ticker_symbol=ticker_symbol,
            ticker_name=ticker_name,
            timestamp=datetime.now(timezone.utc),
            decision=decision,
            strength=strength,
            combined_score=combined_score,
            sentiment_score=sentiment_score_scaled,
            technical_score=technical_score_scaled,
            risk_score=risk_score,
            overall_confidence=overall_confidence,
            sentiment_confidence=sentiment_result.confidence,
            technical_confidence=technical_result.confidence,
            current_price=current_price,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            news_count=sentiment_result.news_count,
            sentiment_data=sentiment_result,
            technical_data=technical_result,
            reasoning=reasoning
        )
        
        return signal
    
    def _calculate_risk_score(
        self,
        price_df: pd.DataFrame,
        technical_result: TechnicalAnalysisResult
    ) -> float:
        """
        Calculate risk component score
        
        Factors:
        - Volatility (ATR)
        - Proximity to support/resistance
        - Volume
        """
        score = 0
        
        # ATR-based volatility (lower = better)
        if technical_result.indicators.get('atr'):
            atr_pct = (technical_result.indicators['atr'] / technical_result.indicators['close']) * 100
            if atr_pct < 2.0:
                score += 50  # Low volatility
            elif atr_pct > 5.0:
                score -= 50  # High volatility (risky)
        
        # Support/Resistance proximity
        current_price = technical_result.indicators['close']
        sr_levels = technical_result.support_resistance
        
        if sr_levels.get('support'):
            nearest_support = max([s for s in sr_levels['support'] if s < current_price], default=None)
            if nearest_support:
                dist_pct = ((current_price - nearest_support) / current_price) * 100
                if dist_pct > 2.0:
                    score += 50  # Safe distance from support
                elif dist_pct < 1.0:
                    score -= 30  # Too close to support (risky)
        
        return np.clip(score, -100, 100)
    
    def _determine_decision(
        self,
        combined_score: float,
        confidence: float
    ) -> Tuple[str, str]:
        """
        Determine BUY/SELL/HOLD decision and strength
        
        Returns: (decision, strength)
        """
        # STRONG BUY
        if (combined_score >= self.config.strong_buy_score and 
            confidence >= self.config.strong_buy_confidence):
            return 'BUY', 'STRONG'
        
        # MODERATE BUY
        elif (combined_score >= self.config.moderate_buy_score and 
              confidence >= self.config.moderate_buy_confidence):
            return 'BUY', 'MODERATE'
        
        # STRONG SELL
        elif (combined_score <= self.config.strong_sell_score and 
              confidence >= self.config.strong_sell_confidence):
            return 'SELL', 'STRONG'
        
        # MODERATE SELL
        elif (combined_score <= self.config.moderate_sell_score and 
              confidence >= self.config.moderate_sell_confidence):
            return 'SELL', 'MODERATE'
        
        # WEAK BUY/SELL (low confidence)
        elif combined_score > 0:
            return 'BUY', 'WEAK'
        elif combined_score < 0:
            return 'SELL', 'WEAK'
        
        # HOLD
        else:
            return 'HOLD', 'NEUTRAL'
    
    def _calculate_levels(
        self,
        decision: str,
        entry_price: float,
        technical_result: TechnicalAnalysisResult
    ) -> Tuple[float, float, float]:
        """
        Calculate stop-loss and take-profit levels
        
        Returns: (stop_loss, take_profit, risk_reward_ratio)
        """
        atr = technical_result.indicators.get('atr', entry_price * 0.02)
        sr_levels = technical_result.support_resistance
        
        if decision == 'BUY':
            # Stop-loss: Below nearest support or ATR-based
            if sr_levels.get('support'):
                nearest_support = max([s for s in sr_levels['support'] if s < entry_price], default=None)
                if nearest_support:
                    stop_loss = nearest_support - atr
                else:
                    stop_loss = entry_price - (atr * self.config.stop_loss_atr_mult)
            else:
                stop_loss = entry_price - (atr * self.config.stop_loss_atr_mult)
            
            # Ensure minimum/maximum stop-loss distance
            min_stop = entry_price * (1 - 0.05)  # Max 5% loss
            max_stop = entry_price * (1 - 0.02)  # Min 2% loss
            stop_loss = np.clip(stop_loss, min_stop, max_stop)
            
            # Take-profit: R:R ratio based
            risk_amount = entry_price - stop_loss
            take_profit = entry_price + (risk_amount * self.config.risk_reward_ratio)
            
            # Or use nearest resistance if better
            if sr_levels.get('resistance'):
                nearest_resistance = min([r for r in sr_levels['resistance'] if r > entry_price], default=None)
                if nearest_resistance and nearest_resistance > take_profit:
                    take_profit = nearest_resistance
        
        elif decision == 'SELL':
            # Stop-loss: Above nearest resistance or ATR-based
            if sr_levels.get('resistance'):
                nearest_resistance = min([r for r in sr_levels['resistance'] if r > entry_price], default=None)
                if nearest_resistance:
                    stop_loss = nearest_resistance + atr
                else:
                    stop_loss = entry_price + (atr * self.config.stop_loss_atr_mult)
            else:
                stop_loss = entry_price + (atr * self.config.stop_loss_atr_mult)
            
            # Ensure minimum/maximum stop-loss distance
            max_stop = entry_price * (1 + 0.05)  # Max 5% loss
            min_stop = entry_price * (1 + 0.02)  # Min 2% loss
            stop_loss = np.clip(stop_loss, min_stop, max_stop)
            
            # Take-profit: R:R ratio based
            risk_amount = stop_loss - entry_price
            take_profit = entry_price - (risk_amount * self.config.risk_reward_ratio)
            
            # Or use nearest support if better
            if sr_levels.get('support'):
                nearest_support = max([s for s in sr_levels['support'] if s < entry_price], default=None)
                if nearest_support and nearest_support < take_profit:
                    take_profit = nearest_support
        
        else:  # HOLD
            stop_loss = entry_price * 0.95  # 5% default
            take_profit = entry_price * 1.05
        
        # Calculate actual R:R ratio
        if decision == 'BUY':
            rr_ratio = (take_profit - entry_price) / (entry_price - stop_loss)
        elif decision == 'SELL':
            rr_ratio = (entry_price - take_profit) / (stop_loss - entry_price)
        else:
            rr_ratio = 1.0
        
        return stop_loss, take_profit, rr_ratio
    
    def _generate_reasoning(
        self,
        sentiment_result: AggregatedSentiment,
        technical_result: TechnicalAnalysisResult,
        risk_score: float,
        decision: str
    ) -> Dict:
        """Generate structured reasoning for the signal"""
        
        # Sentiment reasoning
        sentiment_summary = f"Sentiment: {sentiment_result.weighted_avg:+.2f} based on {sentiment_result.news_count} news items"
        
        key_news = []
        if sentiment_result.news_items:
            # Get top 3 most impactful news
            sorted_news = sorted(
                sentiment_result.news_items,
                key=lambda x: abs(x.sentiment_score) * x.credibility,
                reverse=True
            )[:3]
            
            for news in sorted_news:
                age_hours = news.get_age_hours()
                key_news.append({
                    'title': news.title,
                    'sentiment': news.sentiment_score,
                    'age_hours': age_hours,
                    'source': news.source
                })
        
        # Technical reasoning
        technical_summary = f"Technical score: {technical_result.score:+.1f}"
        key_signals = list(technical_result.signals.values())[:3]
        
        # Risk reasoning
        risk_summary = f"Risk score: {risk_score:+.1f}"
        risk_factors = []
        
        if technical_result.indicators.get('atr'):
            atr_pct = (technical_result.indicators['atr'] / technical_result.indicators['close']) * 100
            risk_factors.append(f"ATR: {atr_pct:.1f}% ({'low' if atr_pct < 2 else 'high'} volatility)")
        
        # Overall reasoning
        reasoning = {
            'sentiment': {
                'summary': sentiment_summary,
                'key_news': key_news,
                'confidence': sentiment_result.confidence
            },
            'technical': {
                'summary': technical_summary,
                'key_signals': key_signals,
                'confidence': technical_result.confidence
            },
            'risk': {
                'summary': risk_summary,
                'factors': risk_factors
            },
            'decision_rationale': self._get_decision_rationale(decision, sentiment_result, technical_result)
        }
        
        return reasoning
    
    def _get_decision_rationale(
        self,
        decision: str,
        sentiment_result: AggregatedSentiment,
        technical_result: TechnicalAnalysisResult
    ) -> str:
        """Generate human-readable decision rationale"""
        if decision == 'BUY':
            return (f"Strong positive sentiment ({sentiment_result.weighted_avg:+.2f}) "
                   f"confirmed by bullish technical indicators (score: {technical_result.score:+.1f})")
        elif decision == 'SELL':
            return (f"Strong negative sentiment ({sentiment_result.weighted_avg:+.2f}) "
                   f"confirmed by bearish technical indicators (score: {technical_result.score:+.1f})")
        else:
            return "Insufficient signal strength or conflicting indicators suggest waiting"


# ==========================================
# BATCH SIGNAL GENERATION
# ==========================================

def generate_signals_for_tickers(
    tickers: List[Dict[str, str]],
    news_data: Dict[str, List[NewsItem]],
    price_data: Dict[str, pd.DataFrame],
    config: Optional[TrendSignalConfig] = None
) -> List[TradingSignal]:
    """
    Generate signals for multiple tickers
    
    Args:
        tickers: List of {'symbol': ..., 'name': ...}
        news_data: Dict mapping ticker -> news items
        price_data: Dict mapping ticker -> price DataFrame
        config: Optional configuration
    
    Returns:
        List of TradingSignal objects
    """
    generator = SignalGenerator(config)
    signals = []
    
    for ticker in tickers:
        symbol = ticker['symbol']
        name = ticker['name']
        
        # Get data
        news = news_data.get(symbol, [])
        prices = price_data.get(symbol)
        
        if prices is None or len(prices) < 50:
            print(f"⚠️ Insufficient price data for {symbol}, skipping...")
            continue
        
        # Generate signal
        try:
            signal = generator.generate_signal(symbol, name, news, prices)
            signals.append(signal)
            print(f"✅ Generated signal for {symbol}: {signal.strength} {signal.decision}")
        except Exception as e:
            print(f"❌ Error generating signal for {symbol}: {e}")
    
    return signals


# ==========================================
# USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    print("✅ Signal Generator Module Loaded")
    print("⚖️ Formula: (Sentiment × 70%) + (Technical × 20%) + (Risk × 10%)")
    print("🎯 Decisions: STRONG BUY/SELL, MODERATE BUY/SELL, HOLD")
    print("💰 Auto-calculates: Entry, Stop-Loss, Take-Profit")

