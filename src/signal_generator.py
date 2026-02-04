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
# HELPER: S/R FORMAT CONVERSION
# ==========================================

def parse_support_resistance(risk_data: Dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse support/resistance from risk_data, handling both old and new formats.
    
    OLD FORMAT (from calculate_risk_score):
        risk_data = {"nearest_support": 2935.0, "nearest_resistance": 2945.0}
    
    NEW FORMAT (from detect_support_resistance):
        risk_data = {
            "support": [{"price": 2935, "distance_pct": 0.03}],
            "resistance": [{"price": 2945, "distance_pct": 0.31}]
        }
    
    Returns:
        (nearest_support, nearest_resistance) as floats or None
    """
    # Try NEW format first
    if 'support' in risk_data and isinstance(risk_data['support'], list):
        support_levels = risk_data.get('support', [])
        resistance_levels = risk_data.get('resistance', [])
        
        nearest_support = support_levels[0]['price'] if support_levels else None
        nearest_resistance = resistance_levels[0]['price'] if resistance_levels else None
        
        return nearest_support, nearest_resistance
    
    # Fall back to OLD format
    else:
        nearest_support = risk_data.get('nearest_support')
        nearest_resistance = risk_data.get('nearest_resistance')
        
        return nearest_support, nearest_resistance


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
    components: Optional[Dict] = None  # ✅ NEW: Weight and contribution breakdown
    technical_indicator_id: Optional[int] = None  # ✅ Link to TechnicalIndicator table
    
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
        # Use actual risk confidence from risk_data
        risk_confidence = risk_data.get("confidence", 0.5)
        
        overall_confidence = (
            sentiment_confidence * sentiment_weight +
            technical_confidence * technical_weight +
            risk_confidence * risk_weight
        )
        
        print(f"[{ticker_symbol}] Confidences: S={sentiment_confidence:.2f}, T={technical_confidence:.2f}, R={risk_confidence:.2f}")
        print(f"[{ticker_symbol}] OVERALL CONFIDENCE: {overall_confidence:.2%}")
        
        # ===== PRELIMINARY DECISION (for entry/exit calculation) =====
        # Need basic decision to know if BUY or SELL for stop-loss calculation
        # HOLD zone threshold (configurable)
        HOLD_ZONE_THRESHOLD = self.config.hold_zone_threshold
        
        if combined_score >= HOLD_ZONE_THRESHOLD:
            preliminary_decision = "BUY"
        elif combined_score <= -HOLD_ZONE_THRESHOLD:
            preliminary_decision = "SELL"
        else:  # -15 < score < 15
            preliminary_decision = "HOLD"
        
        logger.info(f"Preliminary decision: {preliminary_decision} (Score: {combined_score:.1f}, Threshold: ±{HOLD_ZONE_THRESHOLD})")
        
        # ===== CALCULATE ENTRY/EXIT LEVELS =====
        current_price = technical_data.get("current_price")
        entry_price, stop_loss, take_profit, rr_ratio = self._calculate_levels(
            preliminary_decision, current_price, technical_data, risk_data
        )
        
        # DEBUG: Log calculated levels
        print(f"[{ticker_symbol}] 📊 Entry/Exit Levels:")
        print(f"   Entry: ${entry_price if entry_price else 'None'}")
        print(f"   Stop-Loss: ${stop_loss if stop_loss else 'None'} ({((stop_loss/entry_price-1)*100) if (entry_price and stop_loss) else 0:+.2f}%)")
        print(f"   Take-Profit: ${take_profit if take_profit else 'None'} ({((take_profit/entry_price-1)*100) if (entry_price and take_profit) else 0:+.2f}%)")
        print(f"   R:R Ratio: {rr_ratio if rr_ratio else 'None'}")
        
        # ===== DETERMINE FINAL DECISION & STRENGTH =====
        # Now we can use entry/exit levels to assess setup quality
        decision, strength = self._determine_decision(
            combined_score, 
            overall_confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            rr_ratio=rr_ratio
        )
        
        print(f"[{ticker_symbol}] DECISION: {strength} {decision} (Conf: {overall_confidence:.0%})")
        
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
            reasoning=reasoning,
            technical_indicator_id=technical_data.get("technical_indicator_id"),  # ✅ Link to DB record
            components={  # ✅ NEW: Include actual weights and contributions
                "sentiment": {
                    "score": round(sentiment_score, 2),
                    "weight": sentiment_weight,
                    "contribution": round(sentiment_contribution, 2),
                    "confidence": round(sentiment_confidence, 2)
                },
                "technical": {
                    "score": round(technical_score, 2),
                    "weight": technical_weight,
                    "contribution": round(technical_contribution, 2),
                    "confidence": round(technical_confidence, 2),
                    # ✅ ADD: Indicator values for UI display
                    "rsi": technical_data.get("rsi"),
                    "sma_20": technical_data.get("sma_20"),
                    "sma_50": technical_data.get("sma_50"),
                    "adx": technical_data.get("adx"),
                    "atr": technical_data.get("atr"),
                    "atr_pct": technical_data.get("atr_pct")
                },
                "risk": {
                    "score": round(risk_score, 2),
                    "weight": risk_weight,
                    "contribution": round(risk_contribution, 2),
                    "confidence": round(risk_data.get("confidence", 0.5), 2),
                    # ✅ ADD: Risk component breakdown for UI
                    "components": risk_data.get("components", {})
                }
            }
        )
        
        # ===== SAVE AUDIT TRAIL (for debugging) =====
        # NOTE: This will be saved to signals table first, then audit trail
        # The audit trail includes full calculation details for debugging
        self._save_audit_trail(
            signal=signal,
            sentiment_data=sentiment_data,
            technical_data=technical_data,
            risk_data=risk_data,
            config_snapshot={
                "weights": {
                    "sentiment": sentiment_weight,
                    "technical": technical_weight,
                    "risk": risk_weight
                },
                "thresholds": {
                    "buy": getattr(self.config, 'BUY_THRESHOLD', getattr(self.config, 'moderate_buy_score', 50)),
                    "sell": getattr(self.config, 'SELL_THRESHOLD', getattr(self.config, 'moderate_sell_score', -50)),
                    "hold_zone": getattr(self.config, 'hold_zone_threshold', 15)
                },
                "technical_params": {
                    "rsi_oversold": getattr(self.config, 'rsi_oversold_threshold', 30),
                    "rsi_overbought": getattr(self.config, 'rsi_overbought_threshold', 70),
                    "adx_strong": 25,
                    "atr_multiplier_stop": getattr(self.config, 'stop_loss_atr_mult', 2.0),
                    "atr_multiplier_profit": getattr(self.config, 'take_profit_atr_mult', 3.0)
                },
                "risk_params": {
                    "volatility_weight": getattr(self.config, 'risk_volatility_weight', 0.40),
                    "proximity_weight": getattr(self.config, 'risk_proximity_weight', 0.35),
                    "trend_strength_weight": getattr(self.config, 'risk_trend_strength_weight', 0.25)
                },
                # ===== ADDITIONAL CONFIG PARAMS FOR ML =====
                "sr_support_max_distance_pct": getattr(self.config, 'sr_support_max_distance_pct', 5.0),
                "sr_resistance_max_distance_pct": getattr(self.config, 'sr_resistance_max_distance_pct', 8.0),
                "sr_buffer": getattr(self.config, 'stop_loss_sr_buffer', 0.5),
                "dbscan_eps": getattr(self.config, 'sr_dbscan_eps', 4.0),
                "dbscan_min_samples": getattr(self.config, 'sr_dbscan_min_samples', 3),
                "dbscan_order": getattr(self.config, 'sr_dbscan_order', 7),
                "dbscan_lookback": getattr(self.config, 'sr_dbscan_lookback', 180),
                "tech_sma_weight": getattr(self.config, 'tech_sma_weight', 0.30),
                "tech_rsi_weight": getattr(self.config, 'tech_rsi_weight', 0.25),
                "tech_macd_weight": getattr(self.config, 'tech_macd_weight', 0.20),
                "tech_bollinger_weight": getattr(self.config, 'tech_bollinger_weight', 0.15),
                "tech_stochastic_weight": getattr(self.config, 'tech_stochastic_weight', 0.05),
                "tech_volume_weight": getattr(self.config, 'tech_volume_weight', 0.05)
            }
        )
        
        return signal
    
    def _determine_decision(
        self, 
        combined_score: float, 
        confidence: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        rr_ratio: Optional[float] = None
    ) -> Tuple[str, str]:
        """
        Determine BUY/SELL/HOLD decision using DYNAMIC thresholds
        AND swing trading setup quality assessment
        
        Strength levels consider:
        1. Combined score (sentiment + technical + risk)
        2. Confidence level
        3. Setup quality (S/R distances, R:R ratio) ← NEW!
        
        Args:
            combined_score: -100 to +100
            confidence: 0.0 to 1.0
            entry_price, stop_loss, take_profit: Price levels (optional)
            rr_ratio: Risk/Reward ratio (optional)
        """
        strong_buy_score = self.config.STRONG_BUY_SCORE
        strong_buy_conf = self.config.STRONG_BUY_CONFIDENCE
        moderate_buy_score = self.config.MODERATE_BUY_SCORE
        moderate_buy_conf = self.config.MODERATE_BUY_CONFIDENCE
        
        strong_sell_score = self.config.STRONG_SELL_SCORE
        strong_sell_conf = self.config.STRONG_SELL_CONFIDENCE
        moderate_sell_score = self.config.MODERATE_SELL_SCORE
        moderate_sell_conf = self.config.MODERATE_SELL_CONFIDENCE
        
        # ===== SETUP QUALITY ASSESSMENT =====
        setup_quality = "unknown"
        
        if entry_price and stop_loss and take_profit and rr_ratio:
            # Calculate S/R distances
            stop_dist_pct = abs((entry_price - stop_loss) / entry_price * 100)
            target_dist_pct = abs((take_profit - entry_price) / entry_price * 100)
            
            # DEBUG: Log setup quality calculation
            logger.info(f"Setup Quality: Stop={stop_dist_pct:.2f}%, Target={target_dist_pct:.2f}%, R:R={rr_ratio:.2f}")
            
            # Assess setup quality for swing trading
            good_setup = (
                2.0 <= stop_dist_pct <= 6.0 and  # Stop in ideal swing range
                target_dist_pct >= 3.0 and        # Target far enough
                rr_ratio >= 1.5                   # Good risk/reward
            )
            
            poor_setup = (
                stop_dist_pct > 8.0 or            # Stop too far (support broken?)
                target_dist_pct < 2.0 or          # Target too close
                rr_ratio < 1.0                    # Bad risk/reward
            )
            
            if good_setup:
                setup_quality = "good"
                logger.info(f"✅ GOOD swing setup")
            elif poor_setup:
                setup_quality = "poor"
                logger.info(f"⚠️ POOR swing setup (Stop>8% OR Target<2% OR R:R<1.0)")
            else:
                setup_quality = "neutral"
                logger.info(f"⚪ NEUTRAL swing setup")
        else:
            logger.warning(f"⚠️ Cannot assess setup quality - missing levels (entry={entry_price}, stop={stop_loss}, target={take_profit}, rr={rr_ratio})")
        
        # ===== BASE DECISION (Score + Confidence) =====
        base_decision = None
        base_strength = None
        
        if combined_score >= strong_buy_score and confidence >= strong_buy_conf:
            base_decision, base_strength = "BUY", "STRONG"
        elif combined_score >= moderate_buy_score and confidence >= moderate_buy_conf:
            base_decision, base_strength = "BUY", "MODERATE"
        elif combined_score <= strong_sell_score and confidence >= strong_sell_conf:
            base_decision, base_strength = "SELL", "STRONG"
        elif combined_score <= moderate_sell_score and confidence >= moderate_sell_conf:
            base_decision, base_strength = "SELL", "MODERATE"
        else:
            # WEAK BUY/SELL or HOLD zone
            HOLD_ZONE = self.config.hold_zone_threshold
            
            if combined_score >= HOLD_ZONE and combined_score < moderate_buy_score:
                base_decision, base_strength = "BUY", "WEAK"
            elif combined_score <= -HOLD_ZONE and combined_score > moderate_sell_score:
                base_decision, base_strength = "SELL", "WEAK"
            else:  # -15 < score < 15
                base_decision, base_strength = "HOLD", "NEUTRAL"
        
        # ===== ADJUST STRENGTH BASED ON SETUP QUALITY =====
        final_strength = base_strength
        
        logger.info(f"Base strength: {base_strength} (Score: {combined_score:.1f}, Conf: {confidence:.0%})")
        
        if setup_quality == "poor":
            # Downgrade strength if setup is poor
            if base_strength == "STRONG":
                final_strength = "MODERATE"
                logger.warning(f"⬇️ Downgraded STRONG → MODERATE (poor swing setup)")
            elif base_strength == "MODERATE":
                final_strength = "WEAK"
                logger.warning(f"⬇️ Downgraded MODERATE → WEAK (poor swing setup)")
            # WEAK stays WEAK
        
        elif setup_quality == "good" and base_strength == "MODERATE":
            # Upgrade MODERATE → STRONG if setup is excellent AND score is strong enough
            if combined_score >= strong_buy_score * 0.9:  # Within 10% of STRONG threshold
                final_strength = "STRONG"
                logger.info(f"⬆️ Upgraded MODERATE → STRONG (excellent swing setup)")
        
        if final_strength != base_strength:
            logger.info(f"Final strength: {final_strength} (adjusted from {base_strength})")
        else:
            logger.info(f"Final strength: {final_strength} (no adjustment)")
        
        return base_decision, final_strength
    
    def _calculate_levels(
        self,
        decision: str,
        current_price: Optional[float],
        technical_data: Dict,
        risk_data: Dict
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Calculate entry, stop-loss, take-profit levels using DYNAMIC config parameters.
        
        S/R levels now include distance information:
        - Uses nearest S/R regardless of distance
        - Stop-loss: config.stop_loss_sr_buffer× ATR buffer below support
        - User can see if S/R is too close and decide not to trade
        
        Stop-loss buffer logic:
        - Support = psychological level where buyers step in
        - Stop BELOW support = only triggers if support truly breaks
        - Small buffer (default 0.5× ATR) prevents spike-outs while confirming breaks
        """
        if decision == "HOLD" or current_price is None:
            return None, None, None, None
        
        # ===== RELOAD CONFIG FOR DYNAMIC PARAMETERS =====
        from src.config import get_config
        config = get_config()
        if hasattr(config, 'reload'):
            config.reload()
        
        # Get data
        atr = technical_data.get("atr", current_price * 0.02)
        
        # Parse S/R (handles both old and new formats)
        nearest_support, nearest_resistance = parse_support_resistance(risk_data)
        
        entry_price = current_price
        
        if "BUY" in decision:
            # Stop-loss: Use support if available AND within reasonable distance
            if nearest_support:
                support_distance_pct = ((current_price - nearest_support) / current_price) * 100
                
                # Use config threshold (default 5%)
                if support_distance_pct <= config.sr_support_max_distance_pct:
                    # Use config S/R buffer (default 0.5× ATR)
                    stop_loss = nearest_support - (atr * config.stop_loss_sr_buffer)
                    print(f"  ✅ Support-based stop: {nearest_support:.2f} (-{support_distance_pct:.1f}%)")
                else:
                    # Support too far, use ATR fallback (config multiplier, default 2×)
                    stop_loss = current_price - (atr * config.stop_loss_atr_mult)
                    print(f"  ⚠️ Support too far ({support_distance_pct:.1f}%), ATR stop: {stop_loss:.2f} (-{((current_price-stop_loss)/current_price*100):.1f}%)")
            else:
                # Fallback: config ATR multiplier (default 2×)
                stop_loss = current_price - (atr * config.stop_loss_atr_mult)
                print(f"  ℹ️ No support found, ATR-based stop: {stop_loss:.2f} (-{((current_price-stop_loss)/current_price*100):.1f}%)")
            
            # Take-profit: Use resistance if available AND within reasonable distance
            if nearest_resistance:
                resistance_distance_pct = ((nearest_resistance - current_price) / current_price) * 100
                
                # Use config threshold (default 8%)
                if resistance_distance_pct <= config.sr_resistance_max_distance_pct:
                    take_profit = nearest_resistance
                    print(f"  ✅ Resistance-based target: {nearest_resistance:.2f} (+{resistance_distance_pct:.1f}%)")
                else:
                    # Resistance too far, use ATR fallback (config multiplier, default 3×)
                    take_profit = current_price + (atr * config.take_profit_atr_mult)
                    print(f"  ⚠️ Resistance too far ({resistance_distance_pct:.1f}%), ATR target: {take_profit:.2f} (+{((take_profit-current_price)/current_price*100):.1f}%)")
            else:
                # Fallback: config ATR multiplier (default 3×)
                take_profit = current_price + (atr * config.take_profit_atr_mult)
                print(f"  ℹ️ No resistance found, ATR-based target: {take_profit:.2f} (+{((take_profit-current_price)/current_price*100):.1f}%)")
        
        else:  # SELL
            # Stop-loss: Use resistance if available AND within reasonable distance
            if nearest_resistance:
                resistance_distance_pct = ((nearest_resistance - current_price) / current_price) * 100
                
                # Use config threshold (default 5%)
                if resistance_distance_pct <= config.sr_support_max_distance_pct:
                    # Use config S/R buffer (default 0.5× ATR)
                    stop_loss = nearest_resistance + (atr * config.stop_loss_sr_buffer)
                    print(f"  ✅ Resistance-based stop: {nearest_resistance:.2f} (+{resistance_distance_pct:.1f}%)")
                else:
                    # Resistance too far, use ATR fallback (config multiplier, default 2×)
                    stop_loss = current_price + (atr * config.stop_loss_atr_mult)
                    print(f"  ⚠️ Resistance too far ({resistance_distance_pct:.1f}%), ATR stop: {stop_loss:.2f} (+{((stop_loss-current_price)/current_price*100):.1f}%)")
            else:
                # Fallback: config ATR multiplier (default 2×)
                stop_loss = current_price + (atr * config.stop_loss_atr_mult)
                print(f"  ℹ️ No resistance found, ATR-based stop: {stop_loss:.2f} (+{((stop_loss-current_price)/current_price*100):.1f}%)")
            
            # Take-profit: Use support if available AND within reasonable distance
            if nearest_support:
                support_distance_pct = ((current_price - nearest_support) / current_price) * 100
                
                # Use config threshold (default 8%)
                if support_distance_pct <= config.sr_resistance_max_distance_pct:
                    take_profit = nearest_support
                    print(f"  ✅ Support-based target: {nearest_support:.2f} (-{support_distance_pct:.1f}%)")
                else:
                    # Support too far, use ATR fallback (config multiplier, default 3×)
                    take_profit = current_price - (atr * config.take_profit_atr_mult)
                    print(f"  ⚠️ Support too far ({support_distance_pct:.1f}%), ATR target: {take_profit:.2f} (-{((current_price-take_profit)/current_price*100):.1f}%)")
            else:
                # Fallback: config ATR multiplier (default 3×)
                take_profit = current_price - (atr * config.take_profit_atr_mult)
                print(f"  ℹ️ No support found, ATR-based target: {take_profit:.2f} (-{((current_price-take_profit)/current_price*100):.1f}%)")
        
        # Calculate Risk/Reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        return (
            round(entry_price, 2),
            round(stop_loss, 2),
            round(take_profit, 2),
            round(rr_ratio, 2)
        )
    
    def _save_audit_trail(
        self,
        signal: TradingSignal,
        sentiment_data: Dict,
        technical_data: Dict,
        risk_data: Dict,
        config_snapshot: Dict
    ):
        """
        Save detailed audit trail for debugging and analysis
        
        This creates a comprehensive record of how the signal was calculated,
        including all inputs, intermediate calculations, and configuration used.
        
        Args:
            signal: The generated TradingSignal object
            sentiment_data: Raw sentiment data with news items
            technical_data: Raw technical data with indicators
            risk_data: Raw risk data with components
            config_snapshot: Configuration at time of generation
        """
        import json
        
        try:
            # Try to import database components
            try:
                from database import SessionLocal
                from src.models import SignalCalculation
                db_available = True
            except ImportError:
                db_available = False
                logger.warning("Database not available, skipping audit trail save")
                return
            
            if not db_available:
                return
            
            db = SessionLocal()
            
            try:
                # ===== PREPARE INPUT DATA =====
                
                # News inputs
                news_items = sentiment_data.get("all_news", [])
                news_inputs = []
                for item in news_items[:20]:  # Limit to 20 most recent
                    news_inputs.append({
                        "title": item.get("title", ""),
                        "source": item.get("source", "Unknown"),
                        "sentiment_score": item.get("sentiment_score", 0),
                        "published_at": item.get("published_at", "").isoformat() if isinstance(item.get("published_at"), datetime) else str(item.get("published_at", "")),
                        "time_decay": item.get("time_decay", 1.0),
                        "weight": item.get("credibility_weight", 1.0)
                    })
                
                # Technical inputs
                technical_inputs = {
                    "current_price": technical_data.get("current_price"),
                    "atr": technical_data.get("atr"),
                    "atr_pct": technical_data.get("atr_pct"),
                    "rsi": technical_data.get("rsi"),
                    "macd": technical_data.get("macd"),
                    "macd_signal": technical_data.get("macd_signal"),
                    "sma_20": technical_data.get("sma_20"),
                    "sma_50": technical_data.get("sma_50"),
                    "sma_200": technical_data.get("sma_200"),
                    "adx": technical_data.get("adx"),
                    "bb_upper": technical_data.get("bb_upper"),
                    "bb_lower": technical_data.get("bb_lower")
                }
                
                # Risk inputs
                risk_inputs = {
                    "volatility": risk_data.get("volatility"),
                    "nearest_support": risk_data.get("nearest_support"),
                    "nearest_resistance": risk_data.get("nearest_resistance"),
                    "support_levels": risk_data.get("support", []),
                    "resistance_levels": risk_data.get("resistance", []),
                    "components": risk_data.get("components", {})
                }
                
                # ===== PREPARE INTERMEDIATE CALCULATIONS =====
                
                # Sentiment calculation
                sentiment_calculation = {
                    "raw_scores": [item.get("sentiment_score", 0) for item in news_items[:10]],
                    "time_decay_applied": [item.get("time_decay", 1.0) for item in news_items[:10]],
                    "credibility_weights": [item.get("credibility_weight", 1.0) for item in news_items[:10]],
                    "weighted_avg": sentiment_data.get("weighted_avg", 0),
                    "confidence": sentiment_data.get("confidence", 0.5),
                    "news_count": len(news_items)
                }
                
                # Technical calculation
                technical_calculation = {
                    "score": technical_data.get("score", 0),
                    "confidence": technical_data.get("confidence", 0.5),
                    "key_signals": technical_data.get("key_signals", [])
                }
                
                # Risk calculation
                risk_calculation = {
                    "score": risk_data.get("score", 0),
                    "confidence": risk_data.get("confidence", 0.5),
                    "components": risk_data.get("components", {})
                }
                
                # Final weighting
                final_weighting = {
                    "sentiment_weighted": signal.sentiment_score * config_snapshot["weights"]["sentiment"],
                    "technical_weighted": signal.technical_score * config_snapshot["weights"]["technical"],
                    "risk_weighted": signal.risk_score * config_snapshot["weights"]["risk"],
                    "combined": signal.combined_score
                }
                
                # ===== PREPARE OUTPUT DATA =====
                
                # Decision logic
                decision_logic = {
                    "combined_score": signal.combined_score,
                    "decision": signal.decision,
                    "strength": signal.strength,
                    "reasoning": signal.reasoning if signal.reasoning else {}
                }
                
                # Entry/Exit calculation
                nearest_support, nearest_resistance = parse_support_resistance(risk_data)
                
                entry_exit_calculation = {
                    "entry_price": signal.entry_price,
                    "stop_loss": {
                        "value": signal.stop_loss,
                        "method": "support/resistance" if nearest_support or nearest_resistance else "ATR-based",
                        "nearest_sr": nearest_support if signal.decision == "BUY" else nearest_resistance,
                        "atr": technical_data.get("atr")
                    },
                    "take_profit": {
                        "value": signal.take_profit,
                        "method": "support/resistance" if nearest_support or nearest_resistance else "ATR-based",
                        "nearest_sr": nearest_resistance if signal.decision == "BUY" else nearest_support,
                        "atr": technical_data.get("atr")
                    },
                    "risk_reward_ratio": signal.risk_reward_ratio
                }
                
                # ===== CREATE AUDIT RECORD (Optimized Structure) =====
                
                audit_record = SignalCalculation(
                    signal_id=None,  # Will be set after signal is saved
                    ticker_symbol=signal.ticker_symbol,
                    calculated_at=signal.timestamp,
                    
                    # ===== INPUT VALUES (columns) =====
                    current_price=technical_data.get("current_price"),
                    atr=technical_data.get("atr"),
                    atr_pct=technical_data.get("atr_pct"),
                    rsi=technical_data.get("rsi"),
                    macd=technical_data.get("macd"),
                    macd_signal=technical_data.get("macd_signal"),
                    macd_histogram=technical_data.get("macd_histogram"),
                    sma_20=technical_data.get("sma_20"),
                    sma_50=technical_data.get("sma_50"),
                    sma_200=technical_data.get("sma_200"),
                    adx=technical_data.get("adx"),
                    bb_upper=technical_data.get("bb_upper"),
                    bb_middle=technical_data.get("bb_middle"),
                    bb_lower=technical_data.get("bb_lower"),
                    stoch_k=technical_data.get("stoch_k"),
                    stoch_d=technical_data.get("stoch_d"),
                    volatility=risk_data.get("volatility"),
                    nearest_support=risk_data.get("nearest_support"),
                    nearest_resistance=risk_data.get("nearest_resistance"),
                    news_count=len(news_items),
                    
                    # ===== SCORE VALUES (columns) =====
                    sentiment_score=signal.sentiment_score,
                    sentiment_confidence=signal.sentiment_confidence,
                    technical_score=signal.technical_score,
                    technical_confidence=signal.technical_confidence,
                    risk_score=signal.risk_score,
                    risk_confidence=risk_data.get("confidence", 0.5),
                    combined_score=signal.combined_score,
                    
                    # ===== CONFIGURATION WEIGHTS (columns) =====
                    weight_sentiment=config_snapshot["weights"]["sentiment"],
                    weight_technical=config_snapshot["weights"]["technical"],
                    weight_risk=config_snapshot["weights"]["risk"],
                    threshold_buy=config_snapshot["thresholds"]["buy"],
                    threshold_sell=config_snapshot["thresholds"]["sell"],
                    threshold_hold_zone=config_snapshot["thresholds"]["hold_zone"],
                    
                    # ===== TECHNICAL PARAMETERS (columns) =====
                    config_rsi_oversold=config_snapshot["technical_params"].get("rsi_oversold", 30),
                    config_rsi_overbought=config_snapshot["technical_params"].get("rsi_overbought", 70),
                    config_adx_strong=config_snapshot["technical_params"].get("adx_strong", 25),
                    config_atr_stop_multiplier=config_snapshot["technical_params"].get("atr_multiplier_stop", 2.0),
                    config_atr_profit_multiplier=config_snapshot["technical_params"].get("atr_multiplier_profit", 3.0),
                    config_sr_support_max_distance_pct=config_snapshot.get("sr_support_max_distance_pct", 5.0),
                    config_sr_resistance_max_distance_pct=config_snapshot.get("sr_resistance_max_distance_pct", 8.0),
                    config_sr_buffer=config_snapshot.get("sr_buffer", 0.5),
                    config_dbscan_eps=config_snapshot.get("dbscan_eps", 4.0),
                    config_dbscan_min_samples=config_snapshot.get("dbscan_min_samples", 3),
                    config_dbscan_order=config_snapshot.get("dbscan_order", 7),
                    config_dbscan_lookback=config_snapshot.get("dbscan_lookback", 180),
                    
                    # ===== RISK PARAMETERS (columns) =====
                    config_risk_volatility_weight=config_snapshot["risk_params"]["volatility_weight"],
                    config_risk_proximity_weight=config_snapshot["risk_params"]["proximity_weight"],
                    config_risk_trend_strength_weight=config_snapshot["risk_params"]["trend_strength_weight"],
                    
                    # ===== TECHNICAL COMPONENT WEIGHTS (columns) =====
                    config_tech_sma_weight=config_snapshot.get("tech_sma_weight", 0.30),
                    config_tech_rsi_weight=config_snapshot.get("tech_rsi_weight", 0.25),
                    config_tech_macd_weight=config_snapshot.get("tech_macd_weight", 0.20),
                    config_tech_bollinger_weight=config_snapshot.get("tech_bollinger_weight", 0.15),
                    config_tech_stochastic_weight=config_snapshot.get("tech_stochastic_weight", 0.05),
                    config_tech_volume_weight=config_snapshot.get("tech_volume_weight", 0.05),
                    
                    # ===== OUTPUT VALUES (columns) =====
                    decision=signal.decision,
                    strength=signal.strength,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    risk_reward_ratio=signal.risk_reward_ratio,
                    
                    # ===== CONTRIBUTIONS (columns) =====
                    sentiment_contribution=signal.sentiment_score * config_snapshot["weights"]["sentiment"],
                    technical_contribution=signal.technical_score * config_snapshot["weights"]["technical"],
                    risk_contribution=signal.risk_score * config_snapshot["weights"]["risk"],
                    
                    # ===== DETAILED JSON DATA =====
                    news_inputs=json.dumps(news_inputs, default=str),
                    config_snapshot=json.dumps(config_snapshot, default=str),
                    technical_details=json.dumps(technical_calculation, default=str),
                    risk_details=json.dumps(risk_calculation, default=str),
                    reasoning=json.dumps(decision_logic, default=str),
                    entry_exit_details=json.dumps(entry_exit_calculation, default=str),
                    
                    # ===== METADATA =====
                    calculation_duration_ms=None
                )
                
                # Store temporarily in signal object for later save
                # (Will be saved after signal is inserted into DB and we have signal_id)
                if not hasattr(signal, '_audit_record'):
                    signal._audit_record = audit_record
                
                logger.info(f"✅ Audit trail prepared for {signal.ticker_symbol}")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to save audit trail: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - audit trail is optional


# ==========================================
# BATCH SIGNAL GENERATION - ROBUST VERSION
# ==========================================

def generate_signals_for_tickers(
    tickers: List[Dict],
    sentiment_data_dict: Dict,
    technical_data_dict: Dict,
    config=None,
    db=None  # Database session for saving indicators
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
            
            # Handle multi-timeframe data (dict with 'intraday', 'trend', 'volatility', 'support_resistance', 'swing_sr')
            if isinstance(technical_data_raw, dict) and 'intraday' in technical_data_raw:
                df_5m = technical_data_raw['intraday']
                df_1h = technical_data_raw.get('trend')
                df_vol = technical_data_raw.get('volatility')
                df_sr = technical_data_raw.get('support_resistance')
                df_daily = technical_data_raw.get('daily')  # NEW: For ATR calculation
                swing_sr = technical_data_raw.get('swing_sr')  # NEW: Extract swing S/R
                
                if df_5m is not None and len(df_5m) >= 50:
                    print(f"📊 [{ticker_symbol}] Calculating technical (multi-timeframe)...")
                    timeframe_info = []
                    if df_5m is not None: timeframe_info.append(f"5m: {len(df_5m)}")
                    if df_1h is not None: timeframe_info.append(f"1h: {len(df_1h)}")
                    if df_vol is not None: timeframe_info.append(f"Vol: {len(df_vol)}")
                    if df_sr is not None: timeframe_info.append(f"15m: {len(df_sr)}")
                    if swing_sr is not None: timeframe_info.append(f"Swing S/R: ✅")
                    print(f"     {' | '.join(timeframe_info)}")
                    
                    technical_data = calculate_technical_score(
                        df=df_5m, 
                        ticker_symbol=ticker_symbol, 
                        df_trend=df_1h,
                        df_volatility=df_vol,
                        df_sr=df_sr,
                        df_daily=df_daily,  # NEW: For ATR from daily data
                        db=db  # Pass database session for saving indicators
                    )
                else:
                    technical_data = {"score": 0, "confidence": 0.5, "current_price": None, "key_signals": []}
                    swing_sr = None
                    print(f"  ⚠️ Insufficient intraday data")
                    
            # Handle single DataFrame (backward compatibility)
            elif isinstance(technical_data_raw, pd.DataFrame) and len(technical_data_raw) > 50:
                print(f"📊 [{ticker_symbol}] Calculating technical from {len(technical_data_raw)} candles...")
                technical_data = calculate_technical_score(technical_data_raw, ticker_symbol, db=db)
                swing_sr = None
            elif isinstance(technical_data_raw, dict) and 'score' in technical_data_raw:
                technical_data = technical_data_raw
                swing_sr = None
            else:
                technical_data = {"score": 0, "confidence": 0.5, "current_price": None, "key_signals": []}
                swing_sr = None
                print(f"  ⚠️ No technical data")
            
            # ===== RISK CALCULATION =====
            if technical_data.get("current_price") and technical_data.get("atr_pct"):
                # DEBUG: Show what ATR is being passed to risk calculation
                print(f"  🔍 DEBUG: ATR passed to risk calc: {technical_data.get('atr_pct'):.2f}%")
                
                # NEW: Pass swing_sr to calculate_risk_score
                risk_data = calculate_risk_score(technical_data, ticker_symbol, swing_sr=swing_sr)
            else:
                risk_data = {"score": 0, "volatility": 2.0, "support": [], "resistance": []}
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
    
    # Calculate weighted average sentiment
    weighted_avg = sum(weighted_scores) / weights_sum if weights_sum > 0 else 0
    
    # ===== IMPROVED SENTIMENT CONFIDENCE =====
    # Component 1: FinBERT confidence (but capped to avoid over-confidence)
    finbert_conf = sum(confidences) / len(confidences) if confidences else 0.5
    finbert_conf_normalized = min(finbert_conf * 0.85, 0.90)  # Cap at 90%, reduce from ~93%
    
    # Component 2: News volume factor (more news = higher confidence)
    news_count = len(news_items)
    if news_count >= 10:
        volume_factor = 1.0
    elif news_count >= 5:
        volume_factor = 0.85
    elif news_count >= 3:
        volume_factor = 0.70
    elif news_count >= 2:
        volume_factor = 0.55
    else:
        volume_factor = 0.40  # Single news = low confidence
    
    # Component 3: Sentiment consistency (all aligned = higher confidence)
    positive_count = sum(1 for item in news_items if item.sentiment_score > 0.2)
    negative_count = sum(1 for item in news_items if item.sentiment_score < -0.2)
    neutral_count = news_count - positive_count - negative_count
    
    # Consistency: what % agrees with majority direction
    if positive_count > negative_count:
        consistency = positive_count / news_count if news_count > 0 else 0
    elif negative_count > positive_count:
        consistency = negative_count / news_count if news_count > 0 else 0
    else:
        consistency = 0.5  # Mixed signals
    
    # Aggregate confidence (weighted)
    final_confidence = (
        finbert_conf_normalized * 0.40 +  # FinBERT confidence (40%)
        volume_factor * 0.35 +             # News volume (35%)
        consistency * 0.25                 # Consistency (25%)
    )
    
    return {
        "weighted_avg": weighted_avg,
        "confidence": final_confidence,
        "key_news": [
            {
                "title": item.title,
                "url": item.url,
                "published_at": item.published_at.isoformat() if hasattr(item.published_at, 'isoformat') else str(item.published_at)
            }
            for item in news_items[:3]
        ],
        "news_count": len(news_items),
        "confidence_breakdown": {
            "finbert": finbert_conf_normalized,
            "volume": volume_factor,
            "consistency": consistency
        },
        # ✅ ADD: Full news list for audit trail
        "all_news": [
            {
                "title": item.title,
                "source": getattr(item, 'source', 'Unknown'),
                "sentiment_score": item.sentiment_score,
                "sentiment_confidence": item.sentiment_confidence,
                "published_at": item.published_at,
                "credibility_weight": item.credibility,
                "time_decay": (
                    decay_weights.get('0-2h', 1.0) if (now - item.published_at).total_seconds() / 3600 < 2 else
                    decay_weights.get('2-6h', 0.85) if (now - item.published_at).total_seconds() / 3600 < 6 else
                    decay_weights.get('6-12h', 0.60) if (now - item.published_at).total_seconds() / 3600 < 12 else
                    decay_weights.get('12-24h', 0.35) if (now - item.published_at).total_seconds() / 3600 < 24 else
                    0.0
                )
            }
            for item in news_items
        ]
    }


# ==========================================
# NORMALIZED TECHNICAL COMPONENT SCORING
# ==========================================

def calculate_sma_component_score(current, sma_20, sma_50, close_col, config) -> Tuple[float, Dict]:
    """Calculate SMA trend score normalized to -100 to +100"""
    sma_score = 0
    details = {}
    
    if pd.notna(sma_20) and pd.notna(sma_50):
        price = current[close_col]
        
        if price > sma_20:
            sma_score += config.tech_sma20_bullish
            details['sma20'] = 'bullish'
        else:
            sma_score -= config.tech_sma20_bearish
            details['sma20'] = 'bearish'
        
        if price > sma_50:
            sma_score += config.tech_sma50_bullish
            details['sma50'] = 'bullish'
        else:
            sma_score -= config.tech_sma50_bearish
            details['sma50'] = 'bearish'
        
        if sma_20 > sma_50:
            sma_score += config.tech_golden_cross
            details['cross'] = 'golden'
        else:
            sma_score -= config.tech_death_cross
            details['cross'] = 'death'
    
    # Normalize: max +60, min -40 → -100 to +100
    normalized = (sma_score / 60.0) * 100
    return max(-100, min(100, normalized)), details


def calculate_rsi_component_score(rsi, sma_trend_direction, config) -> Tuple[float, Dict]:
    """Calculate RSI score normalized to -100 to +100 (TREND-AWARE)"""
    rsi_score = 0
    details = {'value': float(rsi) if pd.notna(rsi) else None}
    
    if pd.notna(rsi):
        if 45 < rsi < 55:
            rsi_score = config.tech_rsi_neutral
            details['zone'] = 'neutral'
        elif 55 <= rsi < 70:
            rsi_score = config.tech_rsi_bullish
            details['zone'] = 'bullish'
        elif 30 < rsi <= 45:
            rsi_score = config.tech_rsi_weak_bullish
            details['zone'] = 'weak_bullish'
        elif rsi >= 70:
            rsi_score = -config.tech_rsi_overbought
            details['zone'] = 'overbought'
        elif rsi <= 30:
            if sma_trend_direction >= 0:
                rsi_score = config.tech_rsi_oversold
                details['zone'] = 'oversold_bullish'
            else:
                rsi_score = 0
                details['zone'] = 'oversold_ignored'
    
    # Normalize: max +30, min -20 → -100 to +100
    normalized = (rsi_score / 30.0) * 100
    return max(-100, min(100, normalized)), details


def calculate_macd_component_score(current) -> Tuple[float, Dict]:
    """Calculate MACD score normalized to -100 to +100"""
    if 'macd_histogram' in current and pd.notna(current['macd_histogram']):
        macd_hist = float(current['macd_histogram'])
        normalized = max(-100, min(100, macd_hist * 20))
        
        details = {
            'histogram': macd_hist,
            'signal': 'bullish' if macd_hist > 0 else 'bearish'
        }
        return normalized, details
    return 0, {}


def calculate_bollinger_component_score(current, close_col, sma_trend_direction) -> Tuple[float, Dict]:
    """Calculate Bollinger score normalized to -100 to +100 (TREND-AWARE)"""
    if all(pd.notna(current.get(x)) for x in ['bb_upper', 'bb_middle', 'bb_lower']):
        bb_width = current['bb_upper'] - current['bb_lower']
        
        if bb_width > 0:
            price = current[close_col]
            bb_position = (price - current['bb_lower']) / bb_width
            
            if bb_position > 0.8:
                score = -70
                zone = 'overbought'
            elif bb_position < 0.2:
                if sma_trend_direction >= 0:
                    score = +70
                    zone = 'oversold_bullish'
                else:
                    score = 0
                    zone = 'oversold_ignored'
            elif 0.4 <= bb_position <= 0.6:
                score = +30
                zone = 'neutral'
            else:
                score = 0
                zone = 'other'
            
            details = {'position': float(bb_position), 'zone': zone}
            return score, details
    return 0, {}


def calculate_stochastic_component_score(current, sma_trend_direction) -> Tuple[float, Dict]:
    """Calculate Stochastic score normalized to -100 to +100 (TREND-AWARE)"""
    if 'stoch_k' in current and pd.notna(current['stoch_k']):
        stoch_k = float(current['stoch_k'])
        
        if stoch_k < 20:
            if sma_trend_direction >= 0:
                score = +100
                zone = 'oversold_bullish'
            else:
                score = 0
                zone = 'oversold_ignored'
        elif stoch_k > 80:
            score = -100
            zone = 'overbought'
        else:
            score = 0
            zone = 'neutral'
        
        details = {'k': stoch_k, 'zone': zone}
        return score, details
    return 0, {}


def calculate_volume_component_score(df, current) -> Tuple[float, Dict]:
    """Calculate Volume score normalized to -100 to +100"""
    if 'volume' in df.columns and len(df) >= 20:
        volume_sma = df['volume'].rolling(20).mean().iloc[-1]
        current_volume = current.get('volume', 0)
        
        if pd.notna(volume_sma) and volume_sma > 0:
            volume_ratio = current_volume / volume_sma
            
            if volume_ratio > 2.0:
                score = +100
            elif volume_ratio > 1.5:
                score = +70
            elif volume_ratio > 1.2:
                score = +30
            elif volume_ratio < 0.5:
                score = -100
            elif volume_ratio < 0.8:
                score = -50
            else:
                score = 0
            
            details = {'ratio': float(volume_ratio)}
            return score, details
    return 0, {}


def calculate_technical_score(
    df: pd.DataFrame, 
    ticker_symbol: str, 
    df_trend: Optional[pd.DataFrame] = None,
    df_volatility: Optional[pd.DataFrame] = None,
    df_sr: Optional[pd.DataFrame] = None,
    df_daily: Optional[pd.DataFrame] = None,  # NEW: For ATR from daily data
    db: Optional = None  # NEW: Database session for saving indicators
) -> Dict:
    """
    Calculate technical score from MULTI-TIMEFRAME data
    
    Args:
        df: Intraday DataFrame (5m) for RSI, SMA20, current price
        ticker_symbol: Ticker symbol
        df_trend: Hourly DataFrame (1h, 30d) for SMA50, ADX
        df_volatility: Hourly DataFrame (1h, 3d) for ATR (DEPRECATED - use df_daily)
        df_sr: 15-min DataFrame (15m, 3d) for Support/Resistance
        df_daily: Daily DataFrame (1d, 6mo) for ATR calculation (PREFERRED)
    """
    try:
        # Use intraday df as primary
        print(f"  📊 [INTRADAY] Calculating from {len(df)} candles (5m)...")
        if df_trend is not None:
            print(f"  📊 [TREND] Using {len(df_trend)} hourly candles for trend context...")
        
        # Normalize column names to lowercase
        df = df.copy()
        df.columns = [str(col).lower().strip() for col in df.columns]
        
        if df_trend is not None:
            df_trend = df_trend.copy()
            df_trend.columns = [str(col).lower().strip() for col in df_trend.columns]
        
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
        
        # Calculate indicators from INTRADAY data (5m)
        df['sma_20'] = df[close_col].rolling(20).mean()
        
        # SMA 50 - use TREND data (1h) if available, otherwise intraday
        if df_trend is not None and len(df_trend) >= 50:
            # Find close column in trend df
            trend_close_col = None
            for col in df_trend.columns:
                if 'close' in col:
                    trend_close_col = col
                    break
            
            if trend_close_col:
                df_trend['sma_50'] = df_trend[trend_close_col].rolling(50).mean()
                sma_50_value = df_trend['sma_50'].iloc[-1]
                print(f"  ✅ SMA50 from TREND data (1h): {sma_50_value:.2f}")
            else:
                df['sma_50'] = df[close_col].rolling(50).mean()
                sma_50_value = df['sma_50'].iloc[-1]
        else:
            df['sma_50'] = df[close_col].rolling(50).mean()
            sma_50_value = df['sma_50'].iloc[-1] if 'sma_50' in df.columns else None
        
        # RSI from INTRADAY data
        delta = df[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA 12 and 26 for MACD
        df['ema_12'] = df[close_col].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df[close_col].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Stochastic Oscillator
        if high_col and low_col:
            low_14 = df[low_col].rolling(window=14).min()
            high_14 = df[high_col].rolling(window=14).max()
            df['stoch_k'] = 100 * ((df[close_col] - low_14) / (high_14 - low_14))
            df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df[close_col].rolling(window=20).mean()
        bb_std = df[close_col].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # CCI (Commodity Channel Index)
        if high_col and low_col:
            tp = (df[high_col] + df[low_col] + df[close_col]) / 3  # Typical Price
            sma_tp = tp.rolling(window=20).mean()
            mad = tp.rolling(window=20).apply(lambda x: abs(x - x.mean()).mean())
            df['cci'] = (tp - sma_tp) / (0.015 * mad)
        
        # OBV (On-Balance Volume)
        if 'volume' in df.columns:
            obv = [0]
            for i in range(1, len(df)):
                if df[close_col].iloc[i] > df[close_col].iloc[i-1]:
                    obv.append(obv[-1] + df['volume'].iloc[i])
                elif df[close_col].iloc[i] < df[close_col].iloc[i-1]:
                    obv.append(obv[-1] - df['volume'].iloc[i])
                else:
                    obv.append(obv[-1])
            df['obv'] = obv
        
        # Latest values from INTRADAY
        current = df.iloc[-1]
        
        # DEBUG: Check what's actually in current
        print(f"  🔍 DEBUG: current.index = {list(current.index)}")
        print(f"  🔍 DEBUG: 'macd' in current: {'macd' in current.index}")
        print(f"  🔍 DEBUG: 'stoch_k' in current: {'stoch_k' in current.index}")
        print(f"  🔍 DEBUG: 'ema_12' in current: {'ema_12' in current.index}")
        if 'macd' in current.index:
            print(f"  🔍 DEBUG: MACD value: {current['macd']}")
        
        # ===== LOAD CONFIG FOR TECHNICAL WEIGHTS =====
        from src.config import get_config
        config = get_config()
        if hasattr(config, 'reload'):
            config.reload()
        
        # ===== DETECT TREND DIRECTION =====
        sma_50_for_comparison = sma_50_value if pd.notna(sma_50_value) else current.get('sma_50')
        sma_trend_direction = 0
        
        if pd.notna(current.get('sma_20')) and pd.notna(sma_50_for_comparison):
            if current['sma_20'] > sma_50_for_comparison:
                sma_trend_direction = 1  # Golden Cross (bullish)
            else:
                sma_trend_direction = -1  # Death Cross (bearish)
        
        # ===== CALCULATE COMPONENT SCORES (each normalized to -100/+100) =====
        
        # 1. SMA Score
        sma_score, sma_details = calculate_sma_component_score(
            current, current.get('sma_20'), sma_50_for_comparison, close_col, config
        )
        
        # 2. RSI Score (trend-aware)
        rsi_score, rsi_details = calculate_rsi_component_score(
            current.get('rsi'), sma_trend_direction, config
        )
        
        # 3. MACD Score
        macd_score, macd_details = calculate_macd_component_score(current)
        
        # 4. Bollinger Score (trend-aware)
        bb_score, bb_details = calculate_bollinger_component_score(
            current, close_col, sma_trend_direction
        )
        
        # 5. Stochastic Score (trend-aware)
        stoch_score, stoch_details = calculate_stochastic_component_score(
            current, sma_trend_direction
        )
        
        # 6. Volume Score
        volume_score, volume_details = calculate_volume_component_score(df, current)
        
        # ===== WEIGHTED TECHNICAL SCORE =====
        tech_score = (
            sma_score * config.tech_sma_weight +
            rsi_score * config.tech_rsi_weight +
            macd_score * config.tech_macd_weight +
            bb_score * config.tech_bollinger_weight +
            stoch_score * config.tech_stochastic_weight +
            volume_score * config.tech_volume_weight
        )
        
        # Clamp to -100/+100
        tech_score = max(-100, min(100, tech_score))
        
        # ===== BUILD KEY SIGNALS =====
        key_signals = []
        if sma_details.get('cross') == 'golden':
            key_signals.append("Golden Cross")
        elif sma_details.get('cross') == 'death':
            key_signals.append("Death Cross")
        
        if sma_details.get('sma20') == 'bullish':
            key_signals.append("Price > SMA20")
        if sma_details.get('sma50') == 'bullish':
            key_signals.append("Price > SMA50")
        
        if rsi_details.get('zone') == 'oversold_bullish':
            key_signals.append(f"RSI oversold ({rsi_details.get('value', 0):.1f})")
        elif rsi_details.get('zone') == 'overbought':
            key_signals.append(f"RSI overbought ({rsi_details.get('value', 0):.1f})")
        
        if macd_details.get('signal') == 'bullish':
            key_signals.append("MACD bullish")
        elif macd_details.get('signal') == 'bearish':
            key_signals.append("MACD bearish")
        
        if bb_details.get('zone') == 'oversold_bullish':
            key_signals.append("BB dip buy")
        
        if stoch_details.get('zone') == 'oversold_bullish':
            key_signals.append("Stoch oversold")
        
        if volume_details.get('ratio', 1.0) > 1.5:
            key_signals.append("High volume")
        
        # ===== SCORE COMPONENTS TRACKING =====
        score_components = {
            'sma': {'score': round(sma_score, 2), 'weight': config.tech_sma_weight, 'contribution': round(sma_score * config.tech_sma_weight, 2), 'details': sma_details},
            'rsi': {'score': round(rsi_score, 2), 'weight': config.tech_rsi_weight, 'contribution': round(rsi_score * config.tech_rsi_weight, 2), 'details': rsi_details},
            'macd': {'score': round(macd_score, 2), 'weight': config.tech_macd_weight, 'contribution': round(macd_score * config.tech_macd_weight, 2), 'details': macd_details},
            'bollinger': {'score': round(bb_score, 2), 'weight': config.tech_bollinger_weight, 'contribution': round(bb_score * config.tech_bollinger_weight, 2), 'details': bb_details},
            'stochastic': {'score': round(stoch_score, 2), 'weight': config.tech_stochastic_weight, 'contribution': round(stoch_score * config.tech_stochastic_weight, 2), 'details': stoch_details},
            'volume': {'score': round(volume_score, 2), 'weight': config.tech_volume_weight, 'contribution': round(volume_score * config.tech_volume_weight, 2), 'details': volume_details},
            'total_score': round(tech_score, 2)
        }

        
        # ADX - Trend Strength Indicator from TREND timeframe (1h)
        adx = None
        if df_trend is not None and len(df_trend) >= 28:
            try:
                # Find columns in trend df
                trend_high = None
                trend_low = None
                trend_close = None
                
                for col in df_trend.columns:
                    if 'high' in col:
                        trend_high = col
                    elif 'low' in col:
                        trend_low = col
                    elif 'close' in col:
                        trend_close = col
                
                if trend_high and trend_low and trend_close:
                    # Calculate True Range on TREND timeframe
                    df_trend['tr1'] = df_trend[trend_high] - df_trend[trend_low]
                    df_trend['tr2'] = abs(df_trend[trend_high] - df_trend[trend_close].shift())
                    df_trend['tr3'] = abs(df_trend[trend_low] - df_trend[trend_close].shift())
                    df_trend['tr'] = df_trend[['tr1', 'tr2', 'tr3']].max(axis=1)
                    
                    # Calculate Directional Movement
                    df_trend['up_move'] = df_trend[trend_high] - df_trend[trend_high].shift()
                    df_trend['down_move'] = df_trend[trend_low].shift() - df_trend[trend_low]
                    
                    df_trend['plus_dm'] = df_trend['up_move'].where((df_trend['up_move'] > df_trend['down_move']) & (df_trend['up_move'] > 0), 0)
                    df_trend['minus_dm'] = df_trend['down_move'].where((df_trend['down_move'] > df_trend['up_move']) & (df_trend['down_move'] > 0), 0)
                    
                    # Smooth with 14-period
                    atr_14 = df_trend['tr'].rolling(14).mean()
                    plus_di = 100 * (df_trend['plus_dm'].rolling(14).mean() / atr_14)
                    minus_di = 100 * (df_trend['minus_dm'].rolling(14).mean() / atr_14)
                    
                    # Calculate ADX
                    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                    df_trend['adx'] = dx.rolling(14).mean()
                    
                    trend_current = df_trend.iloc[-1]
                    adx = trend_current['adx'] if pd.notna(trend_current.get('adx')) else None
                    
                    if adx is not None:
                        key_signals.append(f"ADX: {adx:.1f} (1h trend)")
                        print(f"  ✅ ADX calculated from TREND data: {adx:.1f}")
                    
            except Exception as e:
                print(f"  ⚠️ Could not calculate ADX from trend data: {e}")
                adx = None
        elif high_col and low_col:
            # Fallback: try from intraday if no trend data
            try:
                # Calculate True Range
                df['tr1'] = df[high_col] - df[low_col]
                df['tr2'] = abs(df[high_col] - df[close_col].shift())
                df['tr3'] = abs(df[low_col] - df[close_col].shift())
                df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
                
                # Calculate Directional Movement
                df['up_move'] = df[high_col] - df[high_col].shift()
                df['down_move'] = df[low_col].shift() - df[low_col]
                
                df['plus_dm'] = df['up_move'].where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), 0)
                df['minus_dm'] = df['down_move'].where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), 0)
                
                # Smooth with 14-period
                atr_14 = df['tr'].rolling(14).mean()
                plus_di = 100 * (df['plus_dm'].rolling(14).mean() / atr_14)
                minus_di = 100 * (df['minus_dm'].rolling(14).mean() / atr_14)
                
                # Calculate ADX
                dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                df['adx'] = dx.rolling(14).mean()
                
                adx = current['adx'] if pd.notna(current.get('adx')) else None
                
                if adx is not None:
                    key_signals.append(f"ADX: {adx:.1f}")
                    
            except Exception as e:
                print(f"  ⚠️ Could not calculate ADX: {e}")
                adx = None
        
        # ATR - CRITICAL: Use DAILY data for accurate daily volatility measurement
        # Daily ATR = average daily price range over last 14 days
        atr = None
        atr_pct = None
        
        if df_daily is not None and len(df_daily) >= 14:
            try:
                # Normalize daily df columns
                df_daily_copy = df_daily.copy()
                df_daily_copy.columns = [str(col).lower().strip() for col in df_daily_copy.columns]
                
                # Find columns
                daily_high = None
                daily_low = None
                daily_close = None
                
                for col in df_daily_copy.columns:
                    if 'high' in col:
                        daily_high = col
                    elif 'low' in col:
                        daily_low = col
                    elif 'close' in col:
                        daily_close = col
                
                if daily_high and daily_low and daily_close:
                    # Calculate True Range (daily)
                    high_low = df_daily_copy[daily_high] - df_daily_copy[daily_low]
                    atr = high_low.rolling(14).mean().iloc[-1]
                    atr_pct = (atr / df_daily_copy[daily_close].iloc[-1]) * 100
                    print(f"  ✅ ATR from DAILY data (1d, 14-period): {atr_pct:.2f}%")
                else:
                    print(f"  ⚠️ Could not find High/Low/Close in daily data")
            except Exception as e:
                print(f"  ⚠️ Could not calculate ATR from daily data: {e}")
        
        # Fallback if no daily data or calculation failed: use hourly (DEPRECATED)
        if atr is None and df_volatility is not None and len(df_volatility) >= 14:
            try:
                # Find columns in volatility df
                vol_high = None
                vol_low = None
                vol_close = None
                
                for col in df_volatility.columns:
                    if 'high' in col:
                        vol_high = col
                    elif 'low' in col:
                        vol_low = col
                    elif 'close' in col:
                        vol_close = col
                
                if vol_high and vol_low and vol_close:
                    high_low = df_volatility[vol_high] - df_volatility[vol_low]
                    atr = high_low.rolling(14).mean().iloc[-1]
                    atr_pct = (atr / df_volatility[vol_close].iloc[-1]) * 100
                    print(f"  ✅ ATR from VOLATILITY data (1h, 3d): {atr_pct:.2f}%")
                else:
                    # Fallback to intraday
                    if high_col and low_col:
                        high_low = df[high_col] - df[low_col]
                        atr = high_low.rolling(14).mean().iloc[-1]
                        atr_pct = (atr / current[close_col]) * 100
                    else:
                        atr = current[close_col] * 0.02
                        atr_pct = 2.0
            except Exception as e:
                print(f"  ⚠️ Could not calculate ATR from volatility data: {e}")
                atr = current[close_col] * 0.02
                atr_pct = 2.0
        # Final fallback: use intraday ONLY if no ATR calculated yet
        if atr is None:
            if high_col and low_col:
                # Fallback: use intraday (5m data)
                high_low = df[high_col] - df[low_col]
                atr = high_low.rolling(14).mean().iloc[-1]
                atr_pct = (atr / current[close_col]) * 100
                print(f"  ⚠️ Using INTRADAY ATR fallback (5m): {atr_pct:.2f}%")
            else:
                atr = current[close_col] * 0.02
                atr_pct = 2.0
                print(f"  ⚠️ Using DEFAULT ATR: 2.0%")
        
        # Support/Resistance - from S/R timeframe (15m, 3d)
        # NOTE: This is INTRADAY S/R (simple min/max from last 100 15m candles)
        # Different from TechnicalAnalyzer.detect_support_resistance() which uses
        # 180-day daily pivots with order=7 for swing trading S/R levels
        if df_sr is not None and len(df_sr) >= 50:
            try:
                # Find columns in S/R df
                sr_high = None
                sr_low = None
                
                for col in df_sr.columns:
                    if 'high' in col:
                        sr_high = col
                    elif 'low' in col:
                        sr_low = col
                
                if sr_high and sr_low:
                    recent_lows = df_sr[sr_low].tail(100)  # Last 100 candles = 25 hours
                    recent_highs = df_sr[sr_high].tail(100)
                    nearest_support = float(recent_lows.min())
                    nearest_resistance = float(recent_highs.max())
                    print(f"  ✅ S/R from 15m data: Support ${nearest_support:.2f}, Resistance ${nearest_resistance:.2f}")
                else:
                    # Fallback to intraday
                    if high_col and low_col:
                        recent_lows = df[low_col].tail(20)
                        recent_highs = df[high_col].tail(20)
                        nearest_support = float(recent_lows.min())
                        nearest_resistance = float(recent_highs.max())
                    else:
                        nearest_support = current[close_col] * 0.97
                        nearest_resistance = current[close_col] * 1.03
            except Exception as e:
                print(f"  ⚠️ Could not calculate S/R from 15m data: {e}")
                nearest_support = current[close_col] * 0.97
                nearest_resistance = current[close_col] * 1.03
        elif high_col and low_col:
            # Fallback: use intraday
            recent_lows = df[low_col].tail(20)
            recent_highs = df[high_col].tail(20)
            nearest_support = float(recent_lows.min())
            nearest_resistance = float(recent_highs.max())
        else:
            nearest_support = current[close_col] * 0.97
            nearest_resistance = current[close_col] * 1.03
        
        # ===== TECHNICAL CONFIDENCE =====
        # Based on how many indicators agree
        indicators_checked = 0
        indicators_bullish = 0
        indicators_bearish = 0
        
        # SMA trend indicators
        if pd.notna(current.get('sma_20')) and pd.notna(current.get('sma_50')):
            indicators_checked += 3
            if current[close_col] > current['sma_20']:
                indicators_bullish += 1
            else:
                indicators_bearish += 1
                
            if current[close_col] > current['sma_50']:
                indicators_bullish += 1
            else:
                indicators_bearish += 1
                
            if current['sma_20'] > current['sma_50']:
                indicators_bullish += 1
            else:
                indicators_bearish += 1
        
        # RSI
        if pd.notna(current.get('rsi')):
            indicators_checked += 1
            if current['rsi'] > 55:
                indicators_bullish += 1
            elif current['rsi'] < 45:
                indicators_bearish += 1
        
        # ADX (strong trend = higher confidence)
        adx_boost = 0
        if adx is not None:
            if adx > 25:
                adx_boost = 0.15  # Strong trend increases confidence
            elif adx > 20:
                adx_boost = 0.10
        
        # Calculate alignment (what % of indicators agree)
        alignment = max(indicators_bullish, indicators_bearish) / indicators_checked if indicators_checked > 0 else 0.5
        
        # Base confidence from alignment
        base_confidence = 0.50 + (alignment * 0.30)  # 50% to 80% range
        
        # Add ADX boost
        technical_confidence = min(base_confidence + adx_boost, 0.90)  # Cap at 90%
        
        result = {
            "score": max(-100, min(100, tech_score)),
            "confidence": technical_confidence,  # Now dynamic!
            "current_price": float(current[close_col]),
            "key_signals": key_signals,
            "atr": float(atr),
            "atr_pct": float(atr_pct),
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "rsi": float(current['rsi']) if pd.notna(current['rsi']) else None,
            "sma_20": float(current['sma_20']) if pd.notna(current['sma_20']) else None,
            "sma_50": float(sma_50_for_comparison) if pd.notna(sma_50_for_comparison) else None,  # From trend df!
            "sma_200": None,  # TODO: Implement from daily data
            "adx": float(adx) if adx is not None else None,
            # ✅ ADD: MACD values
            "macd": float(current['macd']) if pd.notna(current.get('macd')) else None,
            "macd_signal": float(current['macd_signal']) if pd.notna(current.get('macd_signal')) else None,
            "macd_histogram": float(current['macd_histogram']) if pd.notna(current.get('macd_histogram')) else None,
            # ✅ ADD: Bollinger Bands
            "bb_upper": float(current['bb_upper']) if pd.notna(current.get('bb_upper')) else None,
            "bb_middle": float(current['bb_middle']) if pd.notna(current.get('bb_middle')) else None,
            "bb_lower": float(current['bb_lower']) if pd.notna(current.get('bb_lower')) else None,
            # ✅ ADD: Stochastic
            "stoch_k": float(current['stoch_k']) if pd.notna(current.get('stoch_k')) else None,
            "stoch_d": float(current['stoch_d']) if pd.notna(current.get('stoch_d')) else None,
            "technical_indicator_id": None  # Will be set if DB save succeeds
        }
        
        # Save technical indicators to database WITH SCORE AND COMPONENTS
        if db is not None:
            try:
                from db_helpers import save_technical_indicators_to_db
                
                indicators_to_save = {
                    'sma_20': float(current['sma_20']) if pd.notna(current.get('sma_20')) else None,
                    'sma_50': float(sma_50_for_comparison) if pd.notna(sma_50_for_comparison) else None,
                    'rsi': float(current['rsi']) if pd.notna(current.get('rsi')) else None,
                    'adx': float(adx) if adx is not None else None,
                    'atr': float(atr) if atr is not None else None,
                    'stoch_k': float(current['stoch_k']) if 'stoch_k' in current and pd.notna(current['stoch_k']) else None,
                    'stoch_d': float(current['stoch_d']) if 'stoch_d' in current and pd.notna(current['stoch_d']) else None,
                    'macd': float(current['macd']) if 'macd' in current and pd.notna(current['macd']) else None,
                    'macd_signal': float(current['macd_signal']) if 'macd_signal' in current and pd.notna(current['macd_signal']) else None,
                    'macd_histogram': float(current['macd_histogram']) if 'macd_histogram' in current and pd.notna(current['macd_histogram']) else None,
                    'bb_upper': float(current['bb_upper']) if 'bb_upper' in current and pd.notna(current['bb_upper']) else None,
                    'bb_middle': float(current['bb_middle']) if 'bb_middle' in current and pd.notna(current['bb_middle']) else None,
                    'bb_lower': float(current['bb_lower']) if 'bb_lower' in current and pd.notna(current['bb_lower']) else None,
                    'close_price': float(current[close_col])
                }
                
                # Use the last timestamp from the dataframe
                timestamp = df.index[-1]
                if not hasattr(timestamp, 'tzinfo') or timestamp.tzinfo is None:
                    from datetime import timezone as tz
                    timestamp = timestamp.replace(tzinfo=tz.utc)
                
                # Save with score and components
                tech_record = save_technical_indicators_to_db(
                    ticker_symbol=ticker_symbol,
                    interval='5m',  # Primary timeframe
                    timestamp=timestamp,
                    indicators=indicators_to_save,
                    technical_score=float(tech_score),
                    technical_confidence=float(technical_confidence),
                    score_components=score_components,
                    db=db
                )
                
                if tech_record and tech_record.id:
                    result['technical_indicator_id'] = tech_record.id
                    print(f"  💾 Technical indicators saved to DB (ID: {tech_record.id})")
                
            except Exception as e:
                print(f"  ⚠️ Could not save technical indicators to DB: {e}")
        
        adx_str = f" | ADX: {adx:.1f}" if adx is not None else ""
        print(f"  ✅ Technical: {tech_score:.1f} (Conf: {technical_confidence:.0%}) | RSI: {current['rsi']:.1f}{adx_str} | Price: ${current[close_col]:.2f}")
        
        return result
        
    except Exception as e:
        print(f"  ❌ Technical calculation error: {e}")
        import traceback
        traceback.print_exc()
        return {"score": 0, "confidence": 0.5, "current_price": None, "key_signals": []}


def calculate_risk_score(
    technical_data: Dict, 
    ticker_symbol: str,
    swing_sr: Optional[Dict] = None
) -> Dict:
    """
    Calculate multi-component risk score with CONTINUOUS SCALING
    
    Components (with continuous linear interpolation):
    1. Volatility (ATR) - 40% weight
       - Range: 1.5% (very low, +0.8) → 7.0% (very high, -0.8)
       - Categories: Very Low → Low → Moderate → High → Very High
    
    2. S/R Proximity - 35% weight
       - Range: <1% (very close, -0.8) → >10% (excellent, +0.8)
       - Categories: Very Close → Close → Neutral → Good → Safe
    
    3. Trend Strength (ADX) - 25% weight
       - Range: <15 (very weak, -0.8) → >40 (very strong, +0.8)
       - Categories: Very Weak → Weak → Moderate → Strong → Very Strong
    
    Args:
        technical_data: Technical indicators
        ticker_symbol: Ticker symbol
        swing_sr: Optional swing S/R from detect_support_resistance()
                  Format: {'support': [{'price': X, 'distance_pct': Y}], 'resistance': [...]}
                  If provided, prioritized over intraday S/R
    
    Returns:
        Dict with risk score (clamped -100 to +100), confidence, and components
    """
    try:
        atr_pct = technical_data.get("atr_pct", 2.0)
        current_price = technical_data["current_price"]
        adx = technical_data.get("adx", None)  # Trend strength
        
        # ===== SUPPORT/RESISTANCE SELECTION =====
        # PRIORITY: swing_sr (daily 180d, order=7) > intraday S/R (15m min/max)
        
        if swing_sr and (swing_sr.get('support') or swing_sr.get('resistance')):
            # Use swing S/R from detect_support_resistance()
            support_levels = swing_sr.get('support', [])
            resistance_levels = swing_sr.get('resistance', [])
            
            nearest_support = support_levels[0]['price'] if support_levels else None
            nearest_resistance = resistance_levels[0]['price'] if resistance_levels else None
            
            sr_source = "Swing S/R (180d)"
            
            # Log the swing S/R usage
            if nearest_support:
                support_dist = support_levels[0]['distance_pct']
                print(f"  📊 {sr_source}: Support ${nearest_support:.2f} ({support_dist:.2f}% below)")
            if nearest_resistance:
                resistance_dist = resistance_levels[0]['distance_pct']
                print(f"  📊 {sr_source}: Resistance ${nearest_resistance:.2f} ({resistance_dist:.2f}% above)")
        else:
            # Fallback to intraday S/R from technical_data
            nearest_support = technical_data.get("nearest_support", current_price * 0.97)
            nearest_resistance = technical_data.get("nearest_resistance", current_price * 1.03)
            sr_source = "Intraday S/R (15m)"
            print(f"  ⚠️ Using {sr_source} (no swing S/R available)")
        
        # Handle None values (fallback to percentage-based)
        if nearest_support is None:
            nearest_support = current_price * 0.97
        if nearest_resistance is None:
            nearest_resistance = current_price * 1.03
        
        # ===== 1. VOLATILITY RISK (ATR-based) - 40% =====
        # 🆕 Continuous scaling: 1.5% (very low) → 7.0% (very high)
        if atr_pct < 1.5:
            volatility_risk = +0.8  # Very low volatility = very low risk
            vol_status = f"🟢 Very Low Vol"
            vol_confidence = 0.95
        elif atr_pct < 2.5:
            # Linear interpolation: 1.5% → +0.8, 2.5% → +0.4
            volatility_risk = 0.8 - ((atr_pct - 1.5) / 1.0) * 0.4
            vol_status = f"🟢 Low Vol"
            vol_confidence = 0.90
        elif atr_pct < 3.5:
            # Linear interpolation: 2.5% → +0.4, 3.5% → 0.0
            volatility_risk = 0.4 - ((atr_pct - 2.5) / 1.0) * 0.4
            vol_status = f"⚪ Moderate Vol"
            vol_confidence = 0.75
        elif atr_pct < 5.0:
            # Linear interpolation: 3.5% → 0.0, 5.0% → -0.4
            volatility_risk = 0.0 - ((atr_pct - 3.5) / 1.5) * 0.4
            vol_status = f"🟡 High Vol"
            vol_confidence = 0.65
        else:
            # Linear scaling beyond 5%: 5% → -0.4, 7% → -0.8
            volatility_risk = max(-0.8, -0.4 - ((atr_pct - 5.0) / 2.0) * 0.4)
            vol_status = f"🔴 Very High Vol"
            vol_confidence = 0.50
        
        # ===== 2. S/R PROXIMITY RISK - 35% =====
        support_dist_pct = ((current_price - nearest_support) / current_price) * 100
        resistance_dist_pct = ((nearest_resistance - current_price) / current_price) * 100
        min_distance = min(abs(support_dist_pct), abs(resistance_dist_pct))
        
        # 🆕 Continuous scaling based on minimum distance to S/R
        if min_distance < 1.0:
            # Very close to S/R (< 1%)
            proximity_risk = -0.8
            proximity_status = f"🔴 Very Close"
            proximity_confidence = 0.35
        elif min_distance < 2.0:
            # Linear interpolation: 1% → -0.8, 2% → -0.4
            proximity_risk = -0.8 + ((min_distance - 1.0) / 1.0) * 0.4
            proximity_status = f"🟡 Close"
            proximity_confidence = 0.45
        elif min_distance < 4.0:
            # Linear interpolation: 2% → -0.4, 4% → 0.0
            proximity_risk = -0.4 + ((min_distance - 2.0) / 2.0) * 0.4
            proximity_status = f"⚪ Neutral"
            proximity_confidence = 0.65
        elif min_distance < 6.0:
            # Linear interpolation: 4% → 0.0, 6% → +0.4
            proximity_risk = 0.0 + ((min_distance - 4.0) / 2.0) * 0.4
            proximity_status = f"🟢 Good Zone"
            proximity_confidence = 0.80
        else:
            # Excellent zone (> 6% from S/R)
            # Linear interpolation: 6% → +0.4, 10% → +0.8
            proximity_risk = min(0.8, 0.4 + ((min_distance - 6.0) / 4.0) * 0.4)
            proximity_status = f"🟢 Safe Zone"
            proximity_confidence = 0.85
        
        # ===== 3. TREND STRENGTH (ADX) - 25% =====
        if adx is not None:
            # 🆕 Continuous scaling based on ADX
            if adx > 40:
                # Very strong trend (ADX > 40)
                trend_risk = +0.8
                trend_status = f"🟢 Very Strong Trend (ADX: {adx:.1f})"
                trend_confidence = 0.95
            elif adx > 30:
                # Linear interpolation: 30 → +0.5, 40 → +0.8
                trend_risk = 0.5 + ((adx - 30) / 10) * 0.3
                trend_status = f"🟢 Strong Trend (ADX: {adx:.1f})"
                trend_confidence = 0.85
            elif adx > 25:
                # Linear interpolation: 25 → +0.3, 30 → +0.5
                trend_risk = 0.3 + ((adx - 25) / 5) * 0.2
                trend_status = f"🟢 Strong Trend (ADX: {adx:.1f})"
                trend_confidence = 0.80
            elif adx > 20:
                # Linear interpolation: 20 → 0.0, 25 → +0.3
                trend_risk = 0.0 + ((adx - 20) / 5) * 0.3
                trend_status = f"⚪ Moderate Trend (ADX: {adx:.1f})"
                trend_confidence = 0.70
            elif adx > 15:
                # Linear interpolation: 15 → -0.3, 20 → 0.0
                trend_risk = -0.3 + ((adx - 15) / 5) * 0.3
                trend_status = f"🟡 Weak Trend (ADX: {adx:.1f})"
                trend_confidence = 0.60
            else:
                # Very weak trend (ADX < 15)
                trend_risk = max(-0.8, -0.3 - ((15 - adx) / 10) * 0.5)
                trend_status = f"🔴 Very Weak Trend (ADX: {adx:.1f})"
                trend_confidence = 0.50
        else:
            # No ADX data - neutral
            trend_risk = 0.0
            trend_status = "⚪ No ADX data"
            trend_confidence = 0.60
        
        # ===== AGGREGATE RISK SCORE =====
        # Load dynamic weights from config
        from src.config import get_config
        config = get_config()
        if hasattr(config, 'reload'):
            config.reload()
        
        risk_score = (
            volatility_risk * config.risk_volatility_weight +
            proximity_risk * config.risk_proximity_weight +
            trend_risk * config.risk_trend_strength_weight
        ) * 200  # Scale to -100 to +100 range
        
        # ===== RISK CONFIDENCE =====
        risk_confidence = (
            vol_confidence * config.risk_volatility_weight +
            proximity_confidence * config.risk_proximity_weight +
            trend_confidence * config.risk_trend_strength_weight
        )
        
        print(f"  ✅ Risk: {risk_score:+.1f} | ATR: {atr_pct:.2f}% | {vol_status} | {proximity_status} | {trend_status}")
        print(f"     Components: Vol={volatility_risk:+.1f} ({config.risk_volatility_weight:.0%}), Prox={proximity_risk:+.1f} ({config.risk_proximity_weight:.0%}), Trend={trend_risk:+.1f} ({config.risk_trend_strength_weight:.0%})")
        print(f"     Confidence: {risk_confidence:.0%}")
        
        return {
            "score": max(-100, min(100, risk_score)),  # Clamp to -100...+100
            "confidence": risk_confidence,
            "volatility": atr_pct,
            # NEW FORMAT: For parse_support_resistance() helper
            "support": swing_sr.get('support', []) if swing_sr else [],
            "resistance": swing_sr.get('resistance', []) if swing_sr else [],
            # OLD FORMAT: Keep for backward compatibility
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "components": {
                "volatility": {"risk": volatility_risk, "status": vol_status, "confidence": vol_confidence},
                "proximity": {"risk": proximity_risk, "status": proximity_status, "confidence": proximity_confidence},
                "trend_strength": {"risk": trend_risk, "status": trend_status, "confidence": trend_confidence}
            }
        }
        
    except Exception as e:
        print(f"  ❌ Risk calculation error: {e}")
        return {
            "score": 0,
            "confidence": 0.50,
            "volatility": 2.0,
            "nearest_support": None,
            "nearest_resistance": None
        }


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
