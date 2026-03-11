"""
Test yfinance 5-minute data limit
Checks how far back yfinance can provide 5m candles

Usage:
    python test_yfinance_limit.py
"""
import yfinance as yf
from datetime import datetime, timedelta

print("=" * 70)
print("  yfinance 5-Minute Data Limit Test")
print("=" * 70)

ticker = yf.Ticker("AAPL")
now = datetime.now()

print(f"\nMai dátum: {now.date()}")
print(f"Most: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# Test 1: period="max"
print("\n" + "-" * 70)
print("[Test 1] period='max' with interval='5m'")
print("-" * 70)
try:
    df = ticker.history(period="max", interval="5m")
    if not df.empty:
        oldest = df.index[0]
        newest = df.index[-1]
        days = (newest - oldest).days
        print(f"✅ Kapott: {len(df):,} gyertya")
        print(f"   Legrégebbi: {oldest}")
        print(f"   Legújabb: {newest}")
        print(f"   Időtartam: {days} nap")
        print(f"   Naponta átlag: {len(df) / max(days, 1):.0f} gyertya")
    else:
        print("❌ Nincs adat")
except Exception as e:
    print(f"❌ Hiba: {e}")

# Test 2: period="60d"
print("\n" + "-" * 70)
print("[Test 2] period='60d' with interval='5m'")
print("-" * 70)
try:
    df = ticker.history(period="60d", interval="5m")
    if not df.empty:
        oldest = df.index[0]
        newest = df.index[-1]
        days = (newest - oldest).days
        print(f"✅ Kapott: {len(df):,} gyertya")
        print(f"   Legrégebbi: {oldest}")
        print(f"   Legújabb: {newest}")
        print(f"   Időtartam: {days} nap")
    else:
        print("❌ Nincs adat")
except Exception as e:
    print(f"❌ Hiba: {e}")

# Test 3: Different lookback periods
print("\n" + "-" * 70)
print("[Test 3] Testing Different Lookback Periods")
print("-" * 70)
print(f"{'Days Back':>12} | {'Candles':>8} | {'Actual Days':>12} | Status")
print("-" * 70)

for days_back in [7, 14, 21, 30, 45, 60, 75, 90]:
    start = now - timedelta(days=days_back)
    try:
        df = ticker.history(start=start, end=now, interval="5m")
        if not df.empty:
            actual_days = (df.index[-1] - df.index[0]).days
            print(f"{days_back:12d} | {len(df):8,} | {actual_days:12d} | ✅")
        else:
            print(f"{days_back:12d} | {'0':>8} | {'0':>12} | ❌ No data")
    except Exception as e:
        print(f"{days_back:12d} | {'ERROR':>8} | {'-':>12} | ❌ {str(e)[:20]}")

print("\n" + "=" * 70)
print("ÖSSZEFOGLALÓ")
print("=" * 70)
print("\nA legkorábbi elérhető 5 perces adat (fenti tesztek alapján):")
print("→ Nézd meg a 'Legrégebbi' dátumokat fent")
print("\n⚠️  yfinance 5m limit jellemzően: 30-60 nap (változó)")
print("⚠️  Ennél régebbi signalok NEM szimulálhatók!")
print()
