"""
TrendSignal - Database Migration Script
Add new columns to existing tables for technical indicators time series

Run this ONCE before starting the updated backend:
    python migrate_add_technical_columns.py
"""

import sqlite3
import sys
import os
from pathlib import Path

# Find database file
db_path = Path(__file__).parent / "trendsignal.db"

# Alternative paths to check
alternative_paths = [
    Path(__file__).parent / "backend" / "trendsignal.db",
    Path(__file__).parent / "src" / "trendsignal.db",
    Path(__file__).parent.parent / "trendsignal.db",
]

for alt_path in alternative_paths:
    if alt_path.exists():
        db_path = alt_path
        break

if not db_path.exists():
    print("❌ Database file not found!")
    print(f"   Searched: {db_path}")
    for alt in alternative_paths:
        print(f"           {alt}")
    print("\nPlease specify the correct path to trendsignal.db")
    sys.exit(1)

print(f"📁 Database found: {db_path}")
print("=" * 70)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔍 Checking current schema...\n")

# ==========================================
# 1. CHECK SIGNALS TABLE
# ==========================================

print("📊 Signals Table:")
cursor.execute("PRAGMA table_info(signals)")
signals_columns = [row[1] for row in cursor.fetchall()]
print(f"   Current columns: {', '.join(signals_columns)}")

has_tech_id = 'technical_indicator_id' in signals_columns

if has_tech_id:
    print("   ✅ technical_indicator_id column already exists")
else:
    print("   ❌ technical_indicator_id column missing")

print()

# ==========================================
# 2. CHECK TECHNICAL_INDICATORS TABLE
# ==========================================

print("📊 Technical Indicators Table:")
cursor.execute("PRAGMA table_info(technical_indicators)")
tech_columns = [row[1] for row in cursor.fetchall()]
print(f"   Current columns: {', '.join(tech_columns)}")

has_tech_score = 'technical_score' in tech_columns
has_tech_conf = 'technical_confidence' in tech_columns
has_score_comp = 'score_components' in tech_columns

if has_tech_score and has_tech_conf and has_score_comp:
    print("   ✅ All new columns already exist")
else:
    print(f"   ❌ Missing columns:")
    if not has_tech_score:
        print("      - technical_score")
    if not has_tech_conf:
        print("      - technical_confidence")
    if not has_score_comp:
        print("      - score_components")

print("\n" + "=" * 70)
print("🔧 Applying migrations...\n")

# ==========================================
# 3. ADD COLUMNS IF MISSING
# ==========================================

migrations_applied = 0

# Add technical_indicator_id to signals table
if not has_tech_id:
    try:
        print("📝 Adding technical_indicator_id to signals table...")
        cursor.execute("""
            ALTER TABLE signals 
            ADD COLUMN technical_indicator_id INTEGER 
            REFERENCES technical_indicators(id)
        """)
        conn.commit()
        print("   ✅ Column added successfully")
        migrations_applied += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        conn.rollback()

# Add technical_score to technical_indicators table
if not has_tech_score:
    try:
        print("📝 Adding technical_score to technical_indicators table...")
        cursor.execute("""
            ALTER TABLE technical_indicators 
            ADD COLUMN technical_score FLOAT
        """)
        conn.commit()
        print("   ✅ Column added successfully")
        migrations_applied += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        conn.rollback()

# Add technical_confidence to technical_indicators table
if not has_tech_conf:
    try:
        print("📝 Adding technical_confidence to technical_indicators table...")
        cursor.execute("""
            ALTER TABLE technical_indicators 
            ADD COLUMN technical_confidence FLOAT
        """)
        conn.commit()
        print("   ✅ Column added successfully")
        migrations_applied += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        conn.rollback()

# Add score_components to technical_indicators table
if not has_score_comp:
    try:
        print("📝 Adding score_components to technical_indicators table...")
        cursor.execute("""
            ALTER TABLE technical_indicators 
            ADD COLUMN score_components TEXT
        """)
        conn.commit()
        print("   ✅ Column added successfully")
        migrations_applied += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        conn.rollback()

# ==========================================
# 4. VERIFY CHANGES
# ==========================================

print("\n" + "=" * 70)
print("🔍 Verifying changes...\n")

cursor.execute("PRAGMA table_info(signals)")
new_signals_columns = [row[1] for row in cursor.fetchall()]
print(f"📊 Signals table columns: {len(new_signals_columns)}")
if 'technical_indicator_id' in new_signals_columns:
    print("   ✅ technical_indicator_id present")

cursor.execute("PRAGMA table_info(technical_indicators)")
new_tech_columns = [row[1] for row in cursor.fetchall()]
print(f"\n📊 Technical Indicators table columns: {len(new_tech_columns)}")
if 'technical_score' in new_tech_columns:
    print("   ✅ technical_score present")
if 'technical_confidence' in new_tech_columns:
    print("   ✅ technical_confidence present")
if 'score_components' in new_tech_columns:
    print("   ✅ score_components present")

# ==========================================
# 5. SUMMARY
# ==========================================

print("\n" + "=" * 70)
if migrations_applied > 0:
    print(f"✅ Migration complete! {migrations_applied} column(s) added")
    print("\n🚀 You can now start the backend:")
    print("   cd backend")
    print("   python api.py")
else:
    print("✅ Database schema already up-to-date")
    print("   No migrations needed")

print("=" * 70)

# Close connection
conn.close()
