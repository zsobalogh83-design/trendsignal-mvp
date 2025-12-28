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
    Fetch dual timeframe data for multi-timeframe analysis
    
    Intraday (5m): For RSI, SMA20, current price
    Hourly (1h): For SMA50, ADX, trend context
    
    Returns:
        {
            'intraday': 5m DataFrame (2 days, ~156 candles),
            'trend': 1h DataFrame (30 days, ~468 candles)
        }
    """
    print(f"   📊 Fetching dual timeframe data for {ticker_symbol}...")
    
    # Intraday data (5m interval, 2 days)
    df_5m = fetch_price_data(ticker_symbol, interval='5m', period='2d')
    
    # Trend data (1h interval, 30 days)  
    df_1h = fetch_price_data(ticker_symbol, interval='1h', period='30d')
    
    if df_5m is not None and df_1h is not None:
        print(f"   ✅ Dual timeframe: {len(df_5m)} intraday + {len(df_1h)} hourly candles")
    
    return {
        'intraday': df_5m,
        'trend': df_1h
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
