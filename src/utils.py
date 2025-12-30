"""
TrendSignal MVP - Utilities Module
Helper functions and utilities

Version: 1.0
Date: 2024-12-27
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional


# ==========================================
# PRICE DATA UTILITIES
# ==========================================

def fetch_price_data(
    ticker_symbol: str,
    interval: str = "5m",
    period: str = "5d"
) -> Optional[pd.DataFrame]:
    """
    Fetch price data using yfinance
    
    Args:
        ticker_symbol: Stock ticker (e.g., 'AAPL')
        interval: Data interval ('1m', '5m', '15m', '1h', '1d')
        period: Look back period ('1d', '5d', '1mo', '3mo', '1y')
    
    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(interval=interval, period=period)
        
        if df.empty:
            print(f"⚠️ No data retrieved for {ticker_symbol}")
            return None
        
        # Ensure required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            print(f"⚠️ Missing required columns for {ticker_symbol}")
            return None
        
        print(f"✅ Fetched {len(df)} candles for {ticker_symbol} ({interval})")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data for {ticker_symbol}: {e}")
        return None


def fetch_multiple_intervals(
    ticker_symbol: str
) -> Dict[str, pd.DataFrame]:
    """
    Fetch both intraday and daily data
    
    Returns:
        {'5m': DataFrame, '1d': DataFrame}
    """
    return {
        '5m': fetch_price_data(ticker_symbol, interval='5m', period='5d'),
        '1d': fetch_price_data(ticker_symbol, interval='1d', period='6mo')
    }


def fetch_dual_timeframe(ticker_symbol: str) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Fetch MULTI-timeframe data for comprehensive analysis
    
    Timeframe strategy:
    - Intraday (5m, 2d): RSI, SMA20, current price
    - Trend (1h, 30d): SMA50, ADX
    - Volatility (1h, 3d): ATR
    - S/R Levels (15m, 3d): Support/Resistance
    
    Returns:
        {
            'intraday': 5m DataFrame (~156 candles),
            'trend': 1h DataFrame (~468 candles),
            'volatility': 1h DataFrame (~45 candles),
            'support_resistance': 15m DataFrame (~180 candles)
        }
    """
    print(f"   📊 Fetching multi-timeframe data for {ticker_symbol}...")
    
    # Intraday momentum (5m, 2 days)
    df_5m = fetch_price_data(ticker_symbol, interval='5m', period='2d')
    
    # Trend context (1h, 30 days)  
    df_1h_trend = fetch_price_data(ticker_symbol, interval='1h', period='30d')
    
    # Volatility context (1h, 3 days) - focused on recent volatility
    df_1h_vol = fetch_price_data(ticker_symbol, interval='1h', period='3d')
    
    # S/R levels (15m, 3 days) - fine-grained S/R detection
    df_15m = fetch_price_data(ticker_symbol, interval='15m', period='3d')
    
    candle_summary = []
    if df_5m is not None: candle_summary.append(f"5m: {len(df_5m)}")
    if df_1h_trend is not None: candle_summary.append(f"1h: {len(df_1h_trend)}")
    if df_1h_vol is not None: candle_summary.append(f"1h-vol: {len(df_1h_vol)}")
    if df_15m is not None: candle_summary.append(f"15m: {len(df_15m)}")
    
    print(f"   ✅ Multi-timeframe: {' | '.join(candle_summary)}")
    
    return {
        'intraday': df_5m,
        'trend': df_1h_trend,
        'volatility': df_1h_vol,
        'support_resistance': df_15m
    }


# ==========================================
# VALIDATION UTILITIES
# ==========================================

def validate_ticker_symbol(ticker_symbol: str) -> bool:
    """
    Validate ticker symbol exists and has data
    
    Args:
        ticker_symbol: Stock ticker to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        if not info or 'symbol' not in info:
            return False
        
        # Try to fetch 1 day of data
        df = ticker.history(period='1d')
        return not df.empty
        
    except:
        return False


# ==========================================
# FORMATTING UTILITIES
# ==========================================

def format_currency(value: float, currency: str = "USD") -> str:
    """Format price value with currency"""
    if currency == "HUF":
        return f"{value:,.0f} HUF"
    else:
        return f"${value:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage with sign"""
    return f"{value:+.{decimals}f}%"


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime"""
    return dt.strftime(format_str)


# ==========================================
# DISPLAY UTILITIES
# ==========================================

def display_dataframe_summary(df: pd.DataFrame, name: str = "DataFrame"):
    """Display summary of DataFrame"""
    print(f"\n{'='*60}")
    print(f"{name} Summary")
    print(f"{'='*60}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"\nFirst 3 rows:")
    print(df.head(3))
    print(f"\nLast 3 rows:")
    print(df.tail(3))
    print(f"{'='*60}\n")


def create_progress_bar(current: int, total: int, width: int = 40) -> str:
    """Create ASCII progress bar"""
    filled = int(width * current / total)
    bar = '█' * filled + '░' * (width - filled)
    percentage = (current / total) * 100
    return f"[{bar}] {percentage:.0f}% ({current}/{total})"


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    print("✅ Utils Module Loaded")
    print("📊 Price data fetching: yfinance")
    print("✅ Validation utilities available")
    print("🎨 Formatting utilities available")
    
    # Test fetch
    print("\n🧪 Testing price data fetch...")
    df = fetch_price_data("AAPL", interval="1d", period="5d")
    if df is not None:
        display_dataframe_summary(df, "AAPL Daily Data")
