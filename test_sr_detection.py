"""
Test script for improved Support/Resistance detection

Tests the new detect_support_resistance() function with:
- 180-day lookback
- order=7 pivot detection
- 4% clustering
- Distance information in results
"""

import sys
sys.path.append('./src')  # Add src directory to path

from technical_analyzer import detect_support_resistance
import yfinance as yf
import pandas as pd

def test_sr_detection(symbol: str):
    """Test S/R detection for a ticker"""
    print(f"\n{'='*60}")
    print(f"Testing S/R Detection: {symbol}")
    print(f"{'='*60}\n")
    
    # Download 6 months of daily data
    print(f"Downloading 6 months of daily data for {symbol}...")
    df = yf.download(symbol, period='6mo', interval='1d', progress=False)
    
    if df.empty:
        print(f"❌ No data for {symbol}")
        return
    
    print(f"✅ Downloaded {len(df)} daily candles")
    current_price = float(df['Close'].iloc[-1])  # Convert to float
    print(f"📊 Current Price: ${current_price:.2f}")
    
    # Run new S/R detection
    print(f"\n🔍 Running detect_support_resistance() with new parameters...")
    print(f"   - Lookback: 180 days")
    print(f"   - Pivot order: 7")
    print(f"   - Clustering: 4%")
    
    sr_levels = detect_support_resistance(df)
    
    # Display results
    print(f"\n📊 RESULTS:\n")
    
    if sr_levels['support']:
        print(f"🟢 SUPPORT LEVELS ({len(sr_levels['support'])}):")
        for i, level in enumerate(sr_levels['support'], 1):
            price = level['price']
            dist = level['distance_pct']
            
            # Color code by distance
            if dist < 1:
                status = "⚠️ VERY CLOSE"
            elif dist < 2.5:
                status = "⚠️ CLOSE"
            else:
                status = "✅ GOOD"
            
            print(f"   {i}. ${price:.2f} ({dist:.2f}% below) {status}")
    else:
        print(f"🟢 SUPPORT LEVELS: None found")
    
    print()
    
    if sr_levels['resistance']:
        print(f"🔴 RESISTANCE LEVELS ({len(sr_levels['resistance'])}):")
        for i, level in enumerate(sr_levels['resistance'], 1):
            price = level['price']
            dist = level['distance_pct']
            
            # Color code by distance
            if dist < 1:
                status = "⚠️ VERY CLOSE"
            elif dist < 2.5:
                status = "⚠️ CLOSE"
            else:
                status = "✅ GOOD"
            
            print(f"   {i}. ${price:.2f} ({dist:.2f}% above) {status}")
    else:
        print(f"🔴 RESISTANCE LEVELS: None found")
    
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    # Test on various tickers
    test_tickers = [
        'OTP.BD',   # Hungarian bank
        'MOL.BD',   # Hungarian oil
        'AAPL',     # US tech
        'MSFT',     # US tech
        'TSLA'      # US auto
    ]
    
    for ticker in test_tickers:
        try:
            test_sr_detection(ticker)
        except Exception as e:
            print(f"❌ Error testing {ticker}: {e}\n")
    
    print("✅ Testing complete!")
