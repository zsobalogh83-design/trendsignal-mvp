"""
TrendSignal - Timezone Diagnostic
Check how timestamps are stored in the database
"""
import sqlite3
from datetime import datetime
import pytz

DB_PATH = "trendsignal.db"

print("=" * 70)
print("  Timezone Diagnostic")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Current system time
now_system = datetime.now()
now_utc = datetime.now(pytz.UTC)
now_cet = datetime.now(pytz.timezone('Europe/Budapest'))
now_et = datetime.now(pytz.timezone('US/Eastern'))

print(f"\nJelenlegi idők:")
print(f"  System: {now_system}")
print(f"  UTC:    {now_utc}")
print(f"  CET:    {now_cet}")
print(f"  ET:     {now_et}")

# Check Signal timestamps
print("\n" + "=" * 70)
print("📊 Signal Timestamps (sample)")
print("=" * 70)

cursor.execute("""
    SELECT 
        id,
        ticker_symbol,
        created_at,
        CASE 
            WHEN ticker_symbol LIKE '%.BD' THEN 'BÉT (CET)'
            ELSE 'US (ET)'
        END as market
    FROM signals
    WHERE ABS(combined_score) >= 25
    ORDER BY created_at
    LIMIT 5
""")

print(f"{'ID':>5} | {'Symbol':8} | {'Created At':20} | Market")
print("-" * 70)
for row in cursor.fetchall():
    print(f"{row[0]:5d} | {row[1]:8s} | {row[2]:20s} | {row[3]}")

# Check PriceData timestamps  
print("\n" + "=" * 70)
print("📊 Price Data Timestamps (sample)")
print("=" * 70)

cursor.execute("""
    SELECT 
        ticker_symbol,
        timestamp,
        close
    FROM price_data
    WHERE interval = '5m'
    ORDER BY timestamp
    LIMIT 10
""")

print(f"{'Symbol':8} | {'Timestamp':20} | {'Close':>8}")
print("-" * 70)
for row in cursor.fetchall():
    print(f"{row[0]:8s} | {row[1]:20s} | {row[2]:8.2f}")

# Check if timestamps have timezone info
print("\n" + "=" * 70)
print("🔍 Timezone Analysis")
print("=" * 70)

# Sample signal
cursor.execute("SELECT created_at FROM signals LIMIT 1")
signal_ts = cursor.fetchone()[0]

# Sample price
cursor.execute("SELECT timestamp FROM price_data WHERE interval = '5m' LIMIT 1")
price_ts = cursor.fetchone()[0] if cursor.fetchone() else None

print(f"\nSignal timestamp string: '{signal_ts}'")
print(f"  - Contains timezone info? {'+' in signal_ts or 'Z' in signal_ts}")
print(f"  - Format detected: {'ISO with TZ' if 'T' in signal_ts and ('+' in signal_ts or 'Z' in signal_ts) else 'Naive'}")

if price_ts:
    print(f"\nPrice timestamp string: '{price_ts}'")
    print(f"  - Contains timezone info? {'+' in price_ts or 'Z' in price_ts}")
    print(f"  - Format detected: {'ISO with TZ' if 'T' in price_ts and ('+' in price_ts or 'Z' in price_ts) else 'Naive'}")

# Compare a matching timestamp pair
print("\n" + "=" * 70)
print("🔍 Example: Signal vs Nearest Price Data")
print("=" * 70)

cursor.execute("""
    SELECT 
        s.id,
        s.ticker_symbol,
        s.created_at as signal_time,
        p.timestamp as price_time,
        ROUND((JULIANDAY(p.timestamp) - JULIANDAY(s.created_at)) * 24 * 60, 1) as diff_minutes
    FROM signals s
    LEFT JOIN price_data p ON 
        p.ticker_symbol = s.ticker_symbol 
        AND p.interval = '5m'
    WHERE ABS(s.combined_score) >= 25
    AND p.timestamp IS NOT NULL
    LIMIT 5
""")

print(f"{'ID':>5} | {'Symbol':8} | {'Signal Time':20} | {'Price Time':20} | {'Diff (min)':>12}")
print("-" * 90)
for row in cursor.fetchall():
    print(f"{row[0]:5d} | {row[1]:8s} | {row[2]:20s} | {row[3]:20s} | {row[4]:12.1f}")

conn.close()

print("\n" + "=" * 70)
print("💡 Következtetések:")
print("=" * 70)
print("\n1. Ha Signal timestamp tartalmaz +XX:XX vagy Z → UTC")
print("2. Ha Price timestamp NEM tartalmaz timezone → Market local time")
print("3. Konverzió szükséges Signal (UTC) → Market time → Price query")
print()
