"""
TrendSignal MVP - Main Orchestrator with Database Integration
Run complete analysis for specified tickers with DB persistence

Version: 1.1 - Database Support
Date: 2024-12-30
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from config import TrendSignalConfig, get_config
from news_collector import NewsCollector
from signal_generator import SignalGenerator, generate_signals_for_tickers
from utils import fetch_price_data, fetch_dual_timeframe, display_dataframe_summary

# Database imports (optional)
try:
    from src.database import SessionLocal
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    print("⚠️ Database not available, running without persistence")


# ==========================================
# MAIN ANALYSIS FUNCTION
# ==========================================

def run_analysis(
    ticker_symbol: str,
    ticker_name: str,
    config: Optional[TrendSignalConfig] = None,
    use_db: bool = True
):
    """
    Run complete TrendSignal analysis for a single ticker
    
    Args:
        ticker_symbol: Stock ticker (e.g., 'AAPL')
        ticker_name: Company name (e.g., 'Apple Inc.')
        config: Optional custom configuration
        use_db: If True, use database for caching/persistence
    """
    config = config or get_config()
    
    # Database session
    db = None
    if use_db and HAS_DATABASE:
        db = SessionLocal()
    
    try:
        print("=" * 70)
        print(f"🚀 TrendSignal Analysis: {ticker_symbol} - {ticker_name}")
        print("=" * 70)
        print()
        
        # 1. Collect news (with DB persistence)
        print("📰 Step 1: Collecting news...")
        collector = NewsCollector(config, db=db)
        news_items = collector.collect_news(
            ticker_symbol, 
            ticker_name, 
            lookback_hours=24,
            save_to_db=(db is not None)
        )
        print(f"   Collected {len(news_items)} news items")
        print()
        
        # 2. Fetch price data (MULTI-TIMEFRAME with DB caching)
        print("📊 Step 2: Fetching price data (multi-timeframe)...")
        price_data_multi = fetch_dual_timeframe(ticker_symbol, db=db)
        
        price_df_5m = price_data_multi['intraday']
        price_df_1h = price_data_multi['trend']
        price_df_vol = price_data_multi['volatility']
        price_df_sr = price_data_multi['support_resistance']
        
        if price_df_5m is None or len(price_df_5m) < 50:
            print("❌ Insufficient intraday price data, cannot generate signal")
            return None
        
        print()
        
        # 3. Generate signal
        print("🎯 Step 3: Generating trading signal...")
        
        # Import helper functions from signal_generator
        from signal_generator import (
            aggregate_sentiment_from_news, 
            calculate_technical_score, 
            calculate_risk_score
        )
        
        # Aggregate sentiment from news
        sentiment_data = aggregate_sentiment_from_news(news_items)
        
        # Calculate technical score from MULTI timeframe
        technical_data = calculate_technical_score(
            df=price_df_5m, 
            ticker_symbol=ticker_symbol, 
            df_trend=price_df_1h,
            df_volatility=price_df_vol,
            df_sr=price_df_sr
        )
        
        # Calculate risk score
        if technical_data.get("current_price") and technical_data.get("atr_pct"):
            risk_data = calculate_risk_score(technical_data, ticker_symbol)
        else:
            risk_data = {
                "score": 0,
                "confidence": 0.5,
                "volatility": 2.0,
                "nearest_support": None,
                "nearest_resistance": None
            }
        
        # Generate signal with new interface
        generator = SignalGenerator(config)
        signal = generator.generate_signal(
            ticker_symbol=ticker_symbol,
            ticker_name=ticker_name,
            sentiment_data=sentiment_data,
            technical_data=technical_data,
            risk_data=risk_data,
            news_count=len(news_items)
        )
        print()
        
        # 4. Display result
        signal.display()
        
        return signal
        
    finally:
        if db:
            db.close()


# ==========================================
# BATCH ANALYSIS
# ==========================================

def run_batch_analysis(
    tickers: List[Dict[str, str]],
    config: Optional[TrendSignalConfig] = None,
    use_db: bool = True
) -> List:
    """
    Run analysis for multiple tickers with DB support
    
    Args:
        tickers: List of {'symbol': 'AAPL', 'name': 'Apple Inc.'}
        config: Optional configuration
        use_db: If True, use database for caching/persistence
    
    Returns:
        List of TradingSignal objects
    """
    config = config or get_config()
    
    # Database session
    db = None
    if use_db and HAS_DATABASE:
        db = SessionLocal()
    
    try:
        print("=" * 70)
        print(f"🚀 TrendSignal Batch Analysis: {len(tickers)} tickers")
        if db:
            print("💾 Database persistence: ENABLED")
        print("=" * 70)
        print()
        
        # Collect all data first
        collector = NewsCollector(config, db=db)
        
        news_data = {}
        price_data = {}
        
        print("📊 Collecting data for all tickers...")
        for ticker in tickers:
            symbol = ticker['symbol']
            name = ticker['name']
            
            print(f"\n  Processing {symbol}...")
            
            # News (with DB persistence)
            news_items = collector.collect_news(
                symbol, 
                name, 
                lookback_hours=24,
                save_to_db=(db is not None)
            )
            news_data[symbol] = news_items
            
            # Price - DUAL TIMEFRAME (with DB caching)
            dual_data = fetch_dual_timeframe(symbol, db=db)
            price_data[symbol] = dual_data
        
        print("\n" + "=" * 70)
        print("🎯 Generating signals...")
        print("=" * 70)
        
        # Generate signals
        signals = generate_signals_for_tickers(tickers, news_data, price_data, config)
        
        print("\n" + "=" * 70)
        print(f"✅ Generated {len(signals)} signals")
        print("=" * 70)
        
        # Display summary
        print("\n📊 SIGNAL SUMMARY:\n")
        for signal in signals:
            emoji = "🟢" if "BUY" in signal.decision else "🔴" if "SELL" in signal.decision else "⚪"
            print(f"{emoji} {signal.ticker_symbol:8s} | {signal.strength:8s} {signal.decision:4s} | "
                  f"Score: {signal.combined_score:+6.1f} | Conf: {signal.overall_confidence:.0%}")
        
        return signals
        
    finally:
        if db:
            db.close()


# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    # Display configuration
    config = get_config()
    config.display()
    
    print("\n")
    
    # Example: Single ticker analysis
    print("📌 Example 1: Single Ticker Analysis")
    print("-" * 70)
    
    signal = run_analysis(
        ticker_symbol="AAPL",
        ticker_name="Apple Inc."
    )
    
    print("\n\n")
    
    # Example: Batch analysis
    print("📌 Example 2: Batch Analysis")
    print("-" * 70)
    
    tickers = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
    ]
    
    signals = run_batch_analysis(tickers)
    
    print("\n✅ Analysis complete!")
