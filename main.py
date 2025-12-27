"""
TrendSignal MVP - Main Orchestrator
Run complete analysis for specified tickers

Version: 1.0  
Date: 2024-12-27
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from config import TrendSignalConfig, get_config
from news_collector import NewsCollector
from signal_generator import SignalGenerator, generate_signals_for_tickers
from utils import fetch_price_data, display_dataframe_summary


# ==========================================
# MAIN ANALYSIS FUNCTION
# ==========================================

def run_analysis(
    ticker_symbol: str,
    ticker_name: str,
    config: Optional[TrendSignalConfig] = None
):
    """
    Run complete TrendSignal analysis for a single ticker
    
    Args:
        ticker_symbol: Stock ticker (e.g., 'AAPL')
        ticker_name: Company name (e.g., 'Apple Inc.')
        config: Optional custom configuration
    """
    config = config or get_config()
    
    print("=" * 70)
    print(f"🚀 TrendSignal Analysis: {ticker_symbol} - {ticker_name}")
    print("=" * 70)
    print()
    
    # 1. Collect news
    print("📰 Step 1: Collecting news...")
    collector = NewsCollector(config)
    news_items = collector.collect_news(ticker_symbol, ticker_name, lookback_hours=24)
    print(f"   Collected {len(news_items)} news items")
    print()
    
    # 2. Fetch price data
    print("📊 Step 2: Fetching price data...")
    price_df = fetch_price_data(ticker_symbol, interval='5m', period='5d')
    
    if price_df is None or len(price_df) < 50:
        print("❌ Insufficient price data, cannot generate signal")
        return None
    
    print(f"   Fetched {len(price_df)} candles")
    print()
    
    # 3. Generate signal
    print("🎯 Step 3: Generating trading signal...")
    generator = SignalGenerator(config)
    signal = generator.generate_signal(ticker_symbol, ticker_name, news_items, price_df)
    print()
    
    # 4. Display result
    signal.display()
    
    return signal


# ==========================================
# BATCH ANALYSIS
# ==========================================

def run_batch_analysis(
    tickers: List[Dict[str, str]],
    config: Optional[TrendSignalConfig] = None
) -> List:
    """
    Run analysis for multiple tickers
    
    Args:
        tickers: List of {'symbol': 'AAPL', 'name': 'Apple Inc.'}
        config: Optional configuration
    
    Returns:
        List of TradingSignal objects
    """
    config = config or get_config()
    
    print("=" * 70)
    print(f"🚀 TrendSignal Batch Analysis: {len(tickers)} tickers")
    print("=" * 70)
    print()
    
    # Collect all data first
    collector = NewsCollector(config)
    
    news_data = {}
    price_data = {}
    
    print("📊 Collecting data for all tickers...")
    for ticker in tickers:
        symbol = ticker['symbol']
        name = ticker['name']
        
        print(f"\n  Processing {symbol}...")
        
        # News
        news_items = collector.collect_news(symbol, name, lookback_hours=24)
        news_data[symbol] = news_items
        
        # Price
        prices = fetch_price_data(symbol, interval='5m', period='5d')
        price_data[symbol] = prices
    
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
