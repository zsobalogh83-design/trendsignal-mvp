"""
Debug: What does yfinance return for 2026-01-31 to 2026-02-17?
"""
import yfinance as yf
from datetime import datetime
import pandas as pd

print("=" * 70)
print("Testing yfinance for 2026-01-31 to 2026-02-17")
print("=" * 70)

ticker = yf.Ticker("AAPL")

start = datetime(2026, 1, 31)
end = datetime(2026, 2, 17)

print(f"\nKérés: {start} → {end}")

df = ticker.history(start=start, end=end, interval="5m")

if df.empty:
    print("❌ NINCS ADAT!")
else:
    print(f"✅ Kapott: {len(df)} gyertya\n")
    
    # Show date range
    print(f"Időszak:")
    print(f"  Legrégebbi: {df.index[0]}")
    print(f"  Legújabb: {df.index[-1]}")
    
    # Convert to timezone-naive
    df.index = df.index.tz_localize(None)
    
    # Group by date
    df['date'] = pd.to_datetime(df.index).date
    date_counts = df.groupby('date').size()
    
    print(f"\nNapok szerinti bontás:")
    for date, count in date_counts.items():
        print(f"  {date}: {count:3d} gyertya")
    
    print(f"\nÖsszesen {len(date_counts)} nap, {len(df)} gyertya")
    
    # Check January 31
    jan31_data = df[df['date'] == datetime(2026, 1, 31).date()]
    
    print(f"\n📅 JANUÁR 31 részletek:")
    if len(jan31_data) > 0:
        print(f"   ✅ VAN január 31-i adat: {len(jan31_data)} gyertya")
        print(f"   Időszak: {jan31_data.index[0]} → {jan31_data.index[-1]}")
    else:
        print(f"   ❌ NINCS január 31-i adat!")
        print(f"   Első adat: {df.index[0]}")

print("\n" + "=" * 70)
