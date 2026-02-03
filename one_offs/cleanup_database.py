"""
TrendSignal Database Cleanup Script
Analyze and remove unnecessary historical price data based on 2× buffer rule

VERSION: 1.0
DATE: 2026-02-03

STRATEGY:
- Keep only data needed for technical indicators with 2× buffer
- 5m: Keep 2 days (2× MACD_26 buffer)
- 15m: Keep 7 days (2× intraday S/R buffer)
- 1h: Keep 90 days (2× SMA_200 buffer)
- 1d: Keep 1 year (2× swing S/R buffer)
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

# Retention policy (based on 2× buffer rule + 1 day safety margin)
# Safety margin ensures no re-download of edge data from yfinance
RETENTION_POLICY = {
    '5m': 3,      # 2 days + 1 safety = 3 days
    '15m': 8,     # 7 days + 1 safety = 8 days
    '1h': 91,     # 90 days + 1 safety = 91 days
    '1d': 366     # 365 days + 1 safety = 366 days
}

# Database path - should be in same directory as script
DB_PATH = Path(__file__).resolve().parent / "trendsignal.db"

# If not found, try alternative locations
if not DB_PATH.exists():
    # Try src/trendsignal.db
    alt_path = Path(__file__).resolve().parent / "src" / "trendsignal.db"
    if alt_path.exists():
        DB_PATH = alt_path
    else:
        print(f"❌ ERROR: Could not find trendsignal.db!")
        print(f"   Tried: {DB_PATH}")
        print(f"   Tried: {alt_path}")
        print(f"\n💡 Please ensure trendsignal.db is in the same directory as this script.")
        exit(1)

print("=" * 100)
print("🗑️  TRENDSIGNAL DATABASE CLEANUP")
print("=" * 100)
print(f"\n📁 Database: {DB_PATH}")
print(f"📅 Retention policy (2× buffer rule):")
for interval, days in RETENTION_POLICY.items():
    print(f"   - {interval:5s}: {days:3d} days")
print()

# ==========================================
# STEP 1: ANALYZE CURRENT DATA
# ==========================================

print("=" * 100)
print("📊 STEP 1: ANALYZING CURRENT DATA")
print("=" * 100)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Query current data statistics
analysis_query = """
SELECT 
    ticker_symbol,
    interval,
    COUNT(*) as total_candles,
    MIN(timestamp) as oldest,
    MAX(timestamp) as newest,
    ROUND(JULIANDAY(MAX(timestamp)) - JULIANDAY(MIN(timestamp))) as days_span,
    MIN(fetched_at) as first_fetch
FROM price_data
GROUP BY ticker_symbol, interval
ORDER BY ticker_symbol, 
    CASE interval
        WHEN '5m' THEN 1
        WHEN '15m' THEN 2
        WHEN '1h' THEN 3
        WHEN '1d' THEN 4
        ELSE 5
    END;
"""

print("\n📋 CURRENT DATA INVENTORY:\n")
print(f"{'Ticker':<10} {'Interval':<8} {'Candles':<10} {'Days Span':<12} {'Oldest':<20} {'Newest':<20}")
print("-" * 100)

results = cursor.execute(analysis_query).fetchall()
total_candles = 0

for row in results:
    ticker, interval, candles, oldest, newest, days_span, first_fetch = row
    print(f"{ticker:<10} {interval:<8} {candles:<10} {days_span:<12.0f} {oldest:<20} {newest:<20}")
    total_candles += candles

print("-" * 100)
print(f"{'TOTAL':<10} {'ALL':<8} {total_candles:<10}")
print()

# ==========================================
# STEP 2: CALCULATE DELETIONS
# ==========================================

print("=" * 100)
print("🔍 STEP 2: CALCULATING RECORDS TO DELETE")
print("=" * 100)

deletion_plan = []

for ticker, interval, candles, oldest, newest, days_span, _ in results:
    retention_days = RETENTION_POLICY.get(interval)
    
    if retention_days is None:
        print(f"⚠️  {ticker} {interval}: Unknown interval, skipping")
        continue
    
    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    
    # Count records to delete
    count_query = """
    SELECT COUNT(*) 
    FROM price_data 
    WHERE ticker_symbol = ? 
      AND interval = ? 
      AND timestamp < ?
    """
    
    to_delete = cursor.execute(count_query, (ticker, interval, cutoff_date.isoformat())).fetchone()[0]
    to_keep = candles - to_delete
    
    if to_delete > 0:
        deletion_plan.append({
            'ticker': ticker,
            'interval': interval,
            'total': candles,
            'to_delete': to_delete,
            'to_keep': to_keep,
            'cutoff': cutoff_date,
            'retention_days': retention_days
        })
        
        status = "🗑️  DELETE" if to_delete > 0 else "✅ KEEP ALL"
        print(f"{status} {ticker:<10} {interval:<8}: {to_delete:>6} / {candles:<6} ({to_delete/candles*100:.1f}%) - Keep {retention_days}d")
    else:
        print(f"✅ KEEP ALL {ticker:<10} {interval:<8}: All {candles} candles within {retention_days}d retention")

print()

# Summary
total_to_delete = sum(item['to_delete'] for item in deletion_plan)
total_to_keep = total_candles - total_to_delete

print(f"📊 SUMMARY:")
print(f"   Total candles: {total_candles:,}")
print(f"   To delete: {total_to_delete:,} ({total_to_delete/total_candles*100:.1f}%)")
print(f"   To keep: {total_to_keep:,} ({total_to_keep/total_candles*100:.1f}%)")
print()

# ==========================================
# STEP 3: CONFIRM DELETION
# ==========================================

if total_to_delete == 0:
    print("✅ No records to delete! Database is already optimized.")
    conn.close()
    exit(0)

print("=" * 100)
print("⚠️  STEP 3: DELETION CONFIRMATION")
print("=" * 100)
print()
print(f"⚠️  WARNING: About to delete {total_to_delete:,} records ({total_to_delete/total_candles*100:.1f}% of database)")
print()
print("Deletion plan:")
for item in deletion_plan:
    print(f"   - {item['ticker']:<10} {item['interval']:<8}: Delete {item['to_delete']:>6} candles (before {item['cutoff'].date()})")
print()

response = input("❓ Proceed with deletion? (yes/no): ").strip().lower()

if response != 'yes':
    print("\n❌ Deletion cancelled. No changes made.")
    conn.close()
    exit(0)

# ==========================================
# STEP 4: EXECUTE DELETION
# ==========================================

print("\n" + "=" * 100)
print("🗑️  STEP 4: EXECUTING DELETION")
print("=" * 100)
print()

deleted_total = 0

for item in deletion_plan:
    delete_query = """
    DELETE FROM price_data 
    WHERE ticker_symbol = ? 
      AND interval = ? 
      AND timestamp < ?
    """
    
    cursor.execute(delete_query, (item['ticker'], item['interval'], item['cutoff'].isoformat()))
    deleted_count = cursor.rowcount
    deleted_total += deleted_count
    
    print(f"   ✅ {item['ticker']:<10} {item['interval']:<8}: Deleted {deleted_count:>6} records")

# Commit changes
conn.commit()

print()
print(f"💾 Committed {deleted_total:,} deletions to database")

# ==========================================
# STEP 5: VACUUM DATABASE
# ==========================================

print("\n" + "=" * 100)
print("🔧 STEP 5: OPTIMIZING DATABASE (VACUUM)")
print("=" * 100)
print()

print("Running VACUUM to reclaim disk space...")
cursor.execute("VACUUM")
print("✅ Database optimized!")

# ==========================================
# STEP 6: VERIFY RESULTS
# ==========================================

print("\n" + "=" * 100)
print("✅ STEP 6: VERIFICATION")
print("=" * 100)
print()

# Re-run analysis query
print("📋 FINAL DATA INVENTORY:\n")
print(f"{'Ticker':<10} {'Interval':<8} {'Candles':<10} {'Days Span':<12} {'Oldest':<20}")
print("-" * 100)

results_after = cursor.execute(analysis_query).fetchall()
total_after = 0

for row in results_after:
    ticker, interval, candles, oldest, newest, days_span, _ = row
    print(f"{ticker:<10} {interval:<8} {candles:<10} {days_span:<12.0f} {oldest:<20}")
    total_after += candles

print("-" * 100)
print(f"{'TOTAL':<10} {'ALL':<8} {total_after:<10}")
print()

print("=" * 100)
print("🎉 CLEANUP COMPLETE!")
print("=" * 100)
print(f"📊 Statistics:")
print(f"   Before: {total_candles:,} candles")
print(f"   After:  {total_after:,} candles")
print(f"   Deleted: {deleted_total:,} candles ({deleted_total/total_candles*100:.1f}%)")
print(f"   Space saved: Estimated {(total_candles - total_after) * 0.5 / 1024:.1f} MB")
print()
print("✅ Database is now optimized for efficient signal generation!")

conn.close()
