"""
TrendSignal MVP - Technical Analysis Module
Manual implementation of technical indicators (no pandas-ta dependency)

Version: 1.0
Date: 2024-12-27
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass

from config import TrendSignalConfig, get_config


# ==========================================
# TECHNICAL INDICATORS (MANUAL IMPLEMENTATION)
# ==========================================

def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)
    
    Returns: Series with RSI values (0-100)
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Avoid division by zero
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    data: pd.Series, 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    data: pd.Series, 
    period: int = 20, 
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands
    
    Returns: (upper_band, middle_band, lower_band)
    """
    middle = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper, middle, lower


def calculate_atr(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    period: int = 14
) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Returns: Series with ATR values
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator
    
    Returns: (K_line, D_line)
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    # Avoid division by zero
    denominator = (highest_high - lowest_low).replace(0, np.nan)
    k_line = 100 * (close - lowest_low) / denominator
    d_line = k_line.rolling(window=d_period).mean()
    
    return k_line, d_line


# ==========================================
# SUPPORT/RESISTANCE DETECTION
# ==========================================

def detect_support_resistance(
    df: pd.DataFrame,
    lookback_days: int = 180,  # 6 months for swing trading
    proximity_pct: float = 0.04,  # 4% clustering tolerance
    order: int = 7,  # NEW: Configurable pivot order
    min_samples: int = 3  # NEW: Configurable min cluster size
) -> Dict[str, list]:
    """
    Detect support and resistance levels using blue chip swing trading best practices.
    
    Strategy:
    - Stricter pivot detection (configurable order, default=7)
    - 6-month lookback for swing trading (configurable)
    - DBSCAN-style clustering with configurable tolerance
    - Minimum cluster size validation (configurable min_samples)
    - Returns ALL detected S/R levels with distance information
    - User/system decides which levels are significant enough to use
    
    Args:
        df: DataFrame with OHLC data
        lookback_days: Days to look back (default 180 = 6 months)
        proximity_pct: Cluster proximity threshold (default 4% = 0.04)
        order: Pivot detection window (default 7 bars each side)
        min_samples: Minimum pivots per cluster (default 3)
    
    Returns:
        {
            'support': [{'price': X, 'distance_pct': Y}, ...],
            'resistance': [{'price': X, 'distance_pct': Y}, ...]
        }
        Returns levels sorted by proximity to current price
    """
    # Get recent data
    recent_df = df.tail(lookback_days) if len(df) > lookback_days else df
    
    if len(recent_df) < 30:
        logger.warning(f"Insufficient data for S/R: {len(recent_df)} bars")
        return {'support': [], 'resistance': []}
    
    # Extract current price as scalar (handle MultiIndex)
    try:
        current_price = float(recent_df['Close'].iloc[-1])
    except (TypeError, ValueError):
        # Handle MultiIndex case
        if isinstance(recent_df['Close'].iloc[-1], pd.Series):
            current_price = float(recent_df['Close'].iloc[-1].iloc[0])
        else:
            current_price = float(recent_df['Close'].iloc[-1])
    
    # STRICTER PIVOT DETECTION: configurable order (default 7 bars each side)
    # order parameter passed from function arguments
    supports = []
    resistances = []

    def _scalar(val):
        """Extract scalar float from potentially MultiIndex Series value."""
        if isinstance(val, pd.Series):
            return float(val.iloc[0])
        return float(val)

    # Find local minima (support) with order bars each side
    # A true swing low must be STRICTLY lower than ALL surrounding bars
    for i in range(order, len(recent_df) - order):
        left_window  = recent_df['Low'].iloc[i-order:i]
        right_window = recent_df['Low'].iloc[i+1:i+order+1]
        current_value = recent_df['Low'].iloc[i]

        try:
            current_float = _scalar(current_value)
            left_min      = _scalar(left_window.min())
            right_min     = _scalar(right_window.min())
        except Exception:
            continue

        # Strictly less than all neighbours on both sides
        if current_float < left_min and current_float < right_min:
            supports.append(current_float)

    # Find local maxima (resistance) with order bars each side
    # A true swing high must be STRICTLY higher than ALL surrounding bars
    for i in range(order, len(recent_df) - order):
        left_window  = recent_df['High'].iloc[i-order:i]
        right_window = recent_df['High'].iloc[i+1:i+order+1]
        current_value = recent_df['High'].iloc[i]

        try:
            current_float = _scalar(current_value)
            left_max      = _scalar(left_window.max())
            right_max     = _scalar(right_window.max())
        except Exception:
            continue

        # Strictly greater than all neighbours on both sides
        if current_float > left_max and current_float > right_max:
            resistances.append(current_float)
    
    # CLUSTER nearby levels with proximity_pct tolerance and min_samples validation
    supports = cluster_levels(supports, proximity_pct, min_samples)
    resistances = cluster_levels(resistances, proximity_pct, min_samples)
    
    # BUILD RESULTS with distance information
    # Minimum distance filter: S/R levels too close to current price are discarded.
    from src.config import get_config
    _cfg = get_config()
    min_distance_pct = _cfg.sr_min_distance_pct
    top_n = _cfg.sr_top_n_levels

    support_levels = []
    for s in supports:
        if s < current_price:
            distance_pct = (current_price - s) / current_price * 100
            if distance_pct >= min_distance_pct:
                support_levels.append({
                    'price': round(s, 2),
                    'distance_pct': round(distance_pct, 2)
                })

    resistance_levels = []
    for r in resistances:
        if r > current_price:
            distance_pct = (r - current_price) / current_price * 100
            if distance_pct >= min_distance_pct:
                resistance_levels.append({
                    'price': round(r, 2),
                    'distance_pct': round(distance_pct, 2)
                })

    # Sort by proximity (nearest first)
    support_levels.sort(key=lambda x: x['distance_pct'])
    resistance_levels.sort(key=lambda x: x['distance_pct'])

    return {
        'support': support_levels[:top_n],
        'resistance': resistance_levels[:top_n]
    }


def cluster_levels(levels: list, proximity_pct: float = 0.02, min_samples: int = 3) -> list:
    """
    Cluster nearby price levels with minimum cluster size validation.

    Uses the cluster's ANCHOR (first element) as the reference for proximity,
    so a long chain of gradually shifting prices cannot drift into one giant cluster.

    Args:
        levels: List of price levels
        proximity_pct: Proximity threshold as fraction (e.g. 0.04 = 4%)
        min_samples: Minimum number of pivots required for a valid cluster (default 3)

    Returns:
        List of clustered representative levels (median of each valid cluster),
        sorted ascending.
    """
    if not levels:
        return []

    levels = sorted(levels)
    clusters = []
    current_cluster = [levels[0]]
    anchor = levels[0]  # Fixed reference point for the current cluster

    for level in levels[1:]:
        # Proximity is measured against the ANCHOR (first element), not the drifting mean
        if abs(level - anchor) / anchor <= proximity_pct:
            current_cluster.append(level)
        else:
            # Save current cluster ONLY if it has enough samples
            if len(current_cluster) >= min_samples:
                clusters.append(float(np.median(current_cluster)))
            # Start new cluster
            current_cluster = [level]
            anchor = level

    # Don't forget last cluster
    if len(current_cluster) >= min_samples:
        clusters.append(float(np.median(current_cluster)))

    return sorted(clusters)


# ==========================================
# TECHNICAL SCORE CALCULATION
# ==========================================

@dataclass
class TechnicalAnalysisResult:
    """Result of technical analysis"""
    score: float  # -100 to +100
    confidence: float  # 0.0 to 1.0
    components: Dict[str, float]
    indicators: Dict[str, Any]
    support_resistance: Dict[str, list]
    signals: Dict[str, str]


class TechnicalAnalyzer:
    """Technical analysis engine"""
    
    def __init__(self, config: Optional[TrendSignalConfig] = None):
        self.config = config or get_config()
    
    def analyze(self, df: pd.DataFrame) -> TechnicalAnalysisResult:
        """
        Perform complete technical analysis
        
        Args:
            df: DataFrame with OHLC data (columns: Open, High, Low, Close, Volume)
        
        Returns:
            TechnicalAnalysisResult with score, signals, and details
        """
        # Calculate all indicators
        indicators = self._calculate_all_indicators(df)
        
        # Detect support/resistance with blue chip swing trading parameters
        sr_config = self.config.support_resistance if hasattr(self.config, 'support_resistance') else {}
        
        # Load DBSCAN parameters from config (with fallbacks to defaults)
        sr_lookback = getattr(self.config, 'sr_dbscan_lookback', sr_config.get('lookback_days', 180))
        # sr_dbscan_eps is stored as a percentage (e.g. 4.0 = 4%), convert to fraction
        sr_proximity_raw = getattr(self.config, 'sr_dbscan_eps', None)
        if sr_proximity_raw is not None:
            sr_proximity = sr_proximity_raw / 100.0  # 4.0 → 0.04
        else:
            sr_proximity = sr_config.get('proximity_pct', 0.04)
        sr_order = getattr(self.config, 'sr_dbscan_order', 7)
        sr_min_samples = getattr(self.config, 'sr_dbscan_min_samples', 3)
        
        sr_levels = detect_support_resistance(
            df,
            lookback_days=sr_lookback,
            proximity_pct=sr_proximity,
            order=sr_order,
            min_samples=sr_min_samples
        )
        
        # Calculate component scores
        trend_score = self._calculate_trend_score(indicators, df)
        momentum_score = self._calculate_momentum_score(indicators)
        volatility_score = self._calculate_volatility_score(indicators, df)
        volume_score = self._calculate_volume_score(indicators, df)
        
        # Aggregate technical score
        technical_score = (
            trend_score * 0.40 +
            momentum_score * 0.30 +
            volatility_score * 0.20 +
            volume_score * 0.10
        )
        
        # Calculate confidence (based on signal alignment)
        confidence = self._calculate_confidence(
            trend_score, momentum_score, volatility_score, volume_score, indicators
        )
        
        # Generate signal descriptions
        signals = self._generate_signals(indicators, sr_levels, df)
        
        return TechnicalAnalysisResult(
            score=technical_score,
            confidence=confidence,
            components={
                'trend': trend_score,
                'momentum': momentum_score,
                'volatility': volatility_score,
                'volume': volume_score
            },
            indicators=indicators,
            support_resistance=sr_levels,
            signals=signals
        )
    
    def _calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators"""
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        # SMAs
        sma_20 = calculate_sma(close, self.config.sma_periods['short'])
        sma_50 = calculate_sma(close, self.config.sma_periods['medium'])
        sma_200 = calculate_sma(close, self.config.sma_periods['long'])
        
        # EMAs
        ema_12 = calculate_ema(close, self.config.macd_params['fast'])
        ema_26 = calculate_ema(close, self.config.macd_params['slow'])
        
        # MACD
        macd, macd_signal, macd_hist = calculate_macd(
            close,
            self.config.macd_params['fast'],
            self.config.macd_params['slow'],
            self.config.macd_params['signal']
        )
        
        # RSI
        rsi = calculate_rsi(close, self.config.rsi_period)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close)
        
        # ATR
        atr = calculate_atr(high, low, close, self.config.atr_period)
        
        # Stochastic
        stoch_k, stoch_d = calculate_stochastic(high, low, close)
        
        # Volume SMA
        volume_sma = calculate_sma(volume, 20)
        
        return {
            'sma_20': sma_20.iloc[-1] if len(sma_20) > 0 else None,
            'sma_50': sma_50.iloc[-1] if len(sma_50) > 0 else None,
            'sma_200': sma_200.iloc[-1] if len(sma_200) > 0 else None,
            'ema_12': ema_12.iloc[-1] if len(ema_12) > 0 else None,
            'ema_26': ema_26.iloc[-1] if len(ema_26) > 0 else None,
            'macd': macd.iloc[-1] if len(macd) > 0 else None,
            'macd_signal': macd_signal.iloc[-1] if len(macd_signal) > 0 else None,
            'macd_hist': macd_hist.iloc[-1] if len(macd_hist) > 0 else None,
            'rsi': rsi.iloc[-1] if len(rsi) > 0 else None,
            'bb_upper': bb_upper.iloc[-1] if len(bb_upper) > 0 else None,
            'bb_middle': bb_middle.iloc[-1] if len(bb_middle) > 0 else None,
            'bb_lower': bb_lower.iloc[-1] if len(bb_lower) > 0 else None,
            'atr': atr.iloc[-1] if len(atr) > 0 else None,
            'stoch_k': stoch_k.iloc[-1] if len(stoch_k) > 0 else None,
            'stoch_d': stoch_d.iloc[-1] if len(stoch_d) > 0 else None,
            'close': close.iloc[-1],
            'volume': volume.iloc[-1],
            'volume_sma': volume_sma.iloc[-1] if len(volume_sma) > 0 else None,
        }
    
    def _calculate_trend_score(
        self, 
        indicators: Dict, 
        df: pd.DataFrame
    ) -> float:
        """Calculate trend component score (-100 to +100)"""
        score = 0
        signals = 0
        
        # SMA alignment (Golden Cross / Death Cross)
        if all([indicators['sma_20'], indicators['sma_50'], indicators['sma_200']]):
            if (indicators['sma_20'] > indicators['sma_50'] > indicators['sma_200']):
                score += 100  # Golden Cross
                signals += 1
            elif (indicators['sma_20'] < indicators['sma_50'] < indicators['sma_200']):
                score -= 100  # Death Cross
                signals += 1
            else:
                # Partial alignment
                if indicators['sma_20'] > indicators['sma_50']:
                    score += 50
                else:
                    score -= 50
                signals += 1
        
        # MACD
        if indicators['macd'] is not None and indicators['macd_signal'] is not None:
            if indicators['macd'] > indicators['macd_signal']:
                score += 100  # Bullish
            else:
                score -= 100  # Bearish
            signals += 1
        
        # Price vs SMA20
        if indicators['sma_20'] is not None:
            if indicators['close'] > indicators['sma_20']:
                score += 50
            else:
                score -= 50
            signals += 1
        
        return score / signals if signals > 0 else 0
    
    def _calculate_momentum_score(self, indicators: Dict) -> float:
        """Calculate momentum component score (-100 to +100)"""
        score = 0
        signals = 0
        
        # RSI
        if indicators['rsi'] is not None:
            rsi = indicators['rsi']
            if rsi < 30:
                score += 100  # Oversold (buy signal)
            elif rsi > 70:
                score -= 100  # Overbought (sell signal)
            elif rsi > 50:
                score += 50   # Bullish momentum
            else:
                score -= 50   # Bearish momentum
            signals += 1
        
        # Stochastic
        if indicators['stoch_k'] is not None and indicators['stoch_d'] is not None:
            if indicators['stoch_k'] > indicators['stoch_d']:
                score += 100  # Bullish crossover
            else:
                score -= 100  # Bearish crossover
            signals += 1
        
        return score / signals if signals > 0 else 0
    
    def _calculate_volatility_score(
        self, 
        indicators: Dict, 
        df: pd.DataFrame
    ) -> float:
        """Calculate volatility component score (-100 to +100)"""
        score = 0
        signals = 0
        
        # Bollinger Bands position
        if all([indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower']]):
            close = indicators['close']
            bb_position = (close - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
            
            if bb_position > 0.8:
                score -= 50  # Near upper band (overbought)
            elif bb_position < 0.2:
                score += 50  # Near lower band (oversold)
            else:
                score += 20  # Middle zone (neutral-positive)
            signals += 1
        
        # ATR (lower volatility = better for entry)
        if indicators['atr'] is not None:
            atr_pct = (indicators['atr'] / indicators['close']) * 100
            if atr_pct < 2.0:
                score += 50  # Low volatility
            elif atr_pct > 5.0:
                score -= 50  # High volatility
            signals += 1
        
        return score / signals if signals > 0 else 0
    
    def _calculate_volume_score(
        self, 
        indicators: Dict, 
        df: pd.DataFrame
    ) -> float:
        """Calculate volume component score (-100 to +100)"""
        score = 0
        
        # Volume vs average
        if indicators['volume_sma'] is not None:
            volume_ratio = indicators['volume'] / indicators['volume_sma']
            
            if volume_ratio > 1.5:
                score += 100  # High volume (strong signal)
            elif volume_ratio > 1.2:
                score += 50   # Above average
            elif volume_ratio < 0.8:
                score -= 50   # Low volume (weak signal)
        
        return score
    
    def _calculate_confidence(
        self,
        trend: float,
        momentum: float,
        volatility: float,
        volume: float,
        indicators: Dict
    ) -> float:
        """
        Calculate confidence based on signal alignment
        
        Higher confidence when all components agree
        """
        # Normalize scores to -1 to +1
        scores = [trend/100, momentum/100, volatility/100, volume/100]
        
        # Check alignment (all positive or all negative)
        positive_count = sum(1 for s in scores if s > 0)
        negative_count = sum(1 for s in scores if s < 0)
        
        alignment_ratio = max(positive_count, negative_count) / len(scores)
        
        # Base confidence from alignment
        base_confidence = alignment_ratio
        
        # Boost if strong trend (ADX would be here in Phase 2)
        # For now, use SMA alignment as proxy
        if indicators.get('sma_20') and indicators.get('sma_50'):
            sma_diff_pct = abs(indicators['sma_20'] - indicators['sma_50']) / indicators['sma_50']
            if sma_diff_pct > 0.05:  # 5% difference = strong trend
                base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _generate_signals(
        self,
        indicators: Dict,
        sr_levels: Dict,
        df: pd.DataFrame
    ) -> Dict[str, str]:
        """Generate human-readable signal descriptions"""
        signals = {}
        
        # Trend signals
        if all([indicators['sma_20'], indicators['sma_50'], indicators['sma_200']]):
            if (indicators['sma_20'] > indicators['sma_50'] > indicators['sma_200']):
                signals['trend'] = "Golden Cross (SMA 20 > 50 > 200)"
            elif (indicators['sma_20'] < indicators['sma_50'] < indicators['sma_200']):
                signals['trend'] = "Death Cross (SMA 20 < 50 < 200)"
            else:
                signals['trend'] = "Mixed SMA alignment"
        
        # MACD
        if indicators['macd_hist'] is not None:
            if indicators['macd_hist'] > 0:
                signals['macd'] = "Bullish MACD crossover"
            else:
                signals['macd'] = "Bearish MACD crossover"
        
        # RSI
        if indicators['rsi'] is not None:
            rsi = indicators['rsi']
            if rsi < 30:
                signals['rsi'] = f"RSI {rsi:.1f} (Oversold)"
            elif rsi > 70:
                signals['rsi'] = f"RSI {rsi:.1f} (Overbought)"
            else:
                signals['rsi'] = f"RSI {rsi:.1f} (Neutral)"
        
        # Support/Resistance proximity
        current_price = indicators['close']
        if sr_levels['support']:
            nearest_support = max([s for s in sr_levels['support'] if s < current_price], default=None)
            if nearest_support:
                dist_pct = ((current_price - nearest_support) / current_price) * 100
                signals['support'] = f"{dist_pct:.1f}% above support ({nearest_support:.2f})"
        
        if sr_levels['resistance']:
            nearest_resistance = min([r for r in sr_levels['resistance'] if r > current_price], default=None)
            if nearest_resistance:
                dist_pct = ((nearest_resistance - current_price) / current_price) * 100
                signals['resistance'] = f"{dist_pct:.1f}% below resistance ({nearest_resistance:.2f})"
        
        return signals


# ==========================================
# USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    # This would be imported and used by signal_generator.py
    print("✅ Technical Analyzer Module Loaded")
    print("📊 Available indicators: SMA, EMA, RSI, MACD, Bollinger, ATR, Stochastic")
    print("🎯 Support/Resistance detection: DBSCAN clustering")
    print("⚖️ Component weights: Trend 40%, Momentum 30%, Volatility 20%, Volume 10%")
