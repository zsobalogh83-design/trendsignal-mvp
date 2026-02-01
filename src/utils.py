"""
TrendSignal MVP - Utilities Module with Database Integration - DEBUG VERSION
Helper functions and utilities with DB persistence for price data

Version: 1.1 - Database Support + DEBUG
Date: 2025-02-01
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from sqlalchemy.orm import Session


# ==========================================
# PRICE DATA UTILITIES WITH DB SUPPORT
# ==========================================

def fetch_price_data(
    ticker_symbol: str,
    interval: str = "5m",
    period: str = "5d",
    db: Optional[Session] = None,
    use_cache: bool = True
) -> Optional[pd.DataFrame]:
    """
    Fetch price data using yfinance with optional database caching
    """
    print(f"🔍 DEBUG: fetch_price_data called for {ticker_symbol} ({interval}, {period})")
    
    # Try database first if caching enabled
    if use_cache and db:
        try:
            from src.db_helpers import get_price_data_from_db
            
            # Convert period to days
            period_days = _period_to_days(period)
            print(f"🔍 DEBUG: Trying DB cache ({period_days} days)...")
            df = get_price_data_from_db(ticker_symbol, interval, period_days, db)
            
            if df is not None and len(df) > 0:
                print(f"✅ Loaded {len(df)} candles from DB cache for {ticker_symbol} ({interval})")
                return df
            else:
                print(f"🔍 DEBUG: DB cache returned None or empty")
        except Exception as e:
            print(f"⚠️ DB cache miss, fetching from yfinance: {e}")
    else:
        print(f"🔍 DEBUG: Skipping DB cache (use_cache={use_cache}, db={db is not None})")
    
    # Fetch from yfinance
    try:
        print(f"🔍 DEBUG: Calling yfinance for {ticker_symbol}...")
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(interval=interval, period=period)
        
        print(f"🔍 DEBUG: yfinance returned DataFrame with {len(df)} rows")
        
        if df.empty:
            print(f"⚠️ No data retrieved for {ticker_symbol}")
            return None
        
        # Ensure required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        print(f"🔍 DEBUG: DataFrame columns: {list(df.columns)}")
        
        if not all(col in df.columns for col in required_cols):
            print(f"⚠️ Missing required columns for {ticker_symbol}")
            print(f"   Required: {required_cols}")
            print(f"   Available: {list(df.columns)}")
            return None
        
        print(f"✅ Fetched {len(df)} candles for {ticker_symbol} ({interval})")
        
        # Save to database if session provided
        if db:
            try:
                from src.db_helpers import save_price_data_to_db
                print(f"🔍 DEBUG: Saving to DB...")
                save_price_data_to_db(df, ticker_symbol, interval, db)
            except Exception as e:
                print(f"⚠️ Could not save to DB: {e}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data for {ticker_symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _period_to_days(period: str) -> int:
    """Convert period string to days"""
    period_map = {
        '1d': 1,
        '2d': 2,
        '5d': 5,
        '1mo': 30,
        '3mo': 90,
        '6mo': 180,
        '1y': 365,
        '2y': 730,
        '5y': 1825
    }
    return period_map.get(period, 5)


def fetch_dual_timeframe(
    ticker_symbol: str,
    db: Optional[Session] = None
) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Fetch MULTI-timeframe data for comprehensive analysis with DB caching
    """
    print(f"\n🔍 DEBUG: ===== fetch_dual_timeframe START for {ticker_symbol} =====")
    print(f"   📊 Fetching multi-timeframe data for {ticker_symbol}...")
    
    # Intraday momentum (5m, 2 days)
    print(f"\n🔍 DEBUG: Fetching 5m data...")
    df_5m = fetch_price_data(ticker_symbol, interval='5m', period='2d', db=db)
    print(f"🔍 DEBUG: df_5m result: {type(df_5m)}, length: {len(df_5m) if df_5m is not None else 'None'}")
    
    # Trend context (1h, 30 days)
    print(f"\n🔍 DEBUG: Fetching 1h trend data...")
    df_1h_trend = fetch_price_data(ticker_symbol, interval='1h', period='30d', db=db)
    print(f"🔍 DEBUG: df_1h_trend result: length: {len(df_1h_trend) if df_1h_trend is not None else 'None'}")
    
    # Volatility context (1h, 3 days)
    print(f"\n🔍 DEBUG: Fetching 1h volatility data...")
    df_1h_vol = fetch_price_data(ticker_symbol, interval='1h', period='3d', db=db)
    print(f"🔍 DEBUG: df_1h_vol result: length: {len(df_1h_vol) if df_1h_vol is not None else 'None'}")
    
    # S/R levels (15m, 3 days)
    print(f"\n🔍 DEBUG: Fetching 15m S/R data...")
    df_15m = fetch_price_data(ticker_symbol, interval='15m', period='3d', db=db)
    print(f"🔍 DEBUG: df_15m result: length: {len(df_15m) if df_15m is not None else 'None'}")
    
    # NEW: Daily data for swing S/R calculation (1d, 6 months)
    print(f"\n🔍 DEBUG: Fetching 1d daily data...")
    df_daily = fetch_price_data(ticker_symbol, interval='1d', period='6mo', db=db)
    print(f"🔍 DEBUG: df_daily result: length: {len(df_daily) if df_daily is not None else 'None'}")
    
    # NEW: Calculate swing S/R levels from daily data
    swing_sr = None
    if df_daily is not None and len(df_daily) >= 30:
        try:
            print(f"\n🔍 DEBUG: Calculating swing S/R...")
            from src.technical_analyzer import detect_support_resistance
            from src.config import get_config
            
            # Load config for DBSCAN parameters
            config = get_config()
            if hasattr(config, 'reload'):
                config.reload()
            
            print(f"🔍 DEBUG: Config loaded, DBSCAN params:")
            print(f"   - lookback: {getattr(config, 'sr_dbscan_lookback', 180)}")
            print(f"   - eps: {getattr(config, 'sr_dbscan_eps', 4.0)}%")
            print(f"   - order: {getattr(config, 'sr_dbscan_order', 7)}")
            print(f"   - min_samples: {getattr(config, 'sr_dbscan_min_samples', 3)}")
            
            # Call with config parameters
            swing_sr = detect_support_resistance(
                df_daily,
                lookback_days=getattr(config, 'sr_dbscan_lookback', 180),
                proximity_pct=getattr(config, 'sr_dbscan_eps', 4.0) / 100,
                order=getattr(config, 'sr_dbscan_order', 7),
                min_samples=getattr(config, 'sr_dbscan_min_samples', 3)
            )
            
            print(f"🔍 DEBUG: swing_sr calculated: {swing_sr}")
            
            # Log the results
            support_count = len(swing_sr.get('support', [])) if swing_sr else 0
            resistance_count = len(swing_sr.get('resistance', [])) if swing_sr else 0
            
            print(f"🔍 DEBUG: Swing S/R counts - support: {support_count}, resistance: {resistance_count}")
            
            if support_count > 0 or resistance_count > 0:
                print(f"   🎯 Swing S/R (180d): {support_count} support, {resistance_count} resistance")
                
                if support_count > 0:
                    nearest_support = swing_sr['support'][0]
                    print(f"      📉 Support: ${nearest_support['price']:.2f} ({nearest_support['distance_pct']:.2f}% below)")
                
                if resistance_count > 0:
                    nearest_resistance = swing_sr['resistance'][0]
                    print(f"      📈 Resistance: ${nearest_resistance['price']:.2f} ({nearest_resistance['distance_pct']:.2f}% above)")
            else:
                print(f"   ⚠️ Swing S/R: No significant levels found (tight consolidation)")
                
        except Exception as e:
            print(f"   ❌ Could not calculate swing S/R: {e}")
            import traceback
            traceback.print_exc()
            swing_sr = None
    else:
        print(f"🔍 DEBUG: Skipping swing S/R calculation (df_daily={df_daily is not None}, len={len(df_daily) if df_daily is not None else 0})")
    
    candle_summary = []
    if df_5m is not None: candle_summary.append(f"5m: {len(df_5m)}")
    if df_1h_trend is not None: candle_summary.append(f"1h: {len(df_1h_trend)}")
    if df_1h_vol is not None: candle_summary.append(f"1h-vol: {len(df_1h_vol)}")
    if df_15m is not None: candle_summary.append(f"15m: {len(df_15m)}")
    if df_daily is not None: candle_summary.append(f"1d: {len(df_daily)}")
    
    print(f"   ✅ Multi-timeframe: {' | '.join(candle_summary)}")
    
    result = {
        'intraday': df_5m,
        'trend': df_1h_trend,
        'volatility': df_1h_vol,
        'support_resistance': df_15m,
        'daily': df_daily,
        'swing_sr': swing_sr
    }
    
    print(f"🔍 DEBUG: ===== fetch_dual_timeframe END =====")
    print(f"   Returning dict with keys: {list(result.keys())}")
    print(f"   intraday is None: {result['intraday'] is None}")
    if result['intraday'] is not None:
        print(f"   intraday length: {len(result['intraday'])}")
    
    return result


# ==========================================
# VALIDATION UTILITIES
# ==========================================

def validate_ticker_symbol(ticker_symbol: str) -> bool:
    """Validate ticker symbol exists and has data"""
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
    print("✅ Utils Module Loaded with Database Support - DEBUG VERSION")
    print("📊 Price data fetching: yfinance")
    print("💾 Database caching enabled")
    print("✅ Validation utilities available")
    print("🎨 Formatting utilities available")
    
    # Test fetch
    print("\n🧪 Testing price data fetch...")
    df = fetch_price_data("AAPL", interval="1d", period="5d")
    if df is not None:
        display_dataframe_summary(df, "AAPL Daily Data")
