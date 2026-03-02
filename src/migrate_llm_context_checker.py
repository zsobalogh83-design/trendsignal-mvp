"""
TrendSignal - Database Migration Script
Add LLM Context Checker columns to news_items table

Run this ONCE before starting the updated backend:
    python src/migrate_llm_context_checker.py

Idempotens: tobbszor futtatható hiba nelkul.
CRITICAL: sentiment_score NEM torlodik (backward compat).

Version: 1.0 | 2026-03-02
"""

import sqlite3
import sys
import os
from pathlib import Path

# Find database file
db_path = Path(__file__).parent.parent / "trendsignal.db"

alternative_paths = [
    Path(__file__).parent / "trendsignal.db",
    Path(__file__).parent / "backend" / "trendsignal.db",
    Path(__file__).parent.parent / "backend" / "trendsignal.db",
]

for alt_path in alternative_paths:
    if alt_path.exists():
        db_path = alt_path
        break

if not db_path.exists():
    print("[ERROR] Database file not found!")
    print(f"   Searched: {db_path}")
    for alt in alternative_paths:
        print(f"           {alt}")
    print("\nPlease ensure the database exists before running migrations.")
    sys.exit(1)

print(f"[DB] Database found: {db_path}")
print("=" * 70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("[INFO] Checking current schema of news_items table...\n")

cursor.execute("PRAGMA table_info(news_items)")
existing_columns = {row[1] for row in cursor.fetchall()}
print(f"   Current columns ({len(existing_columns)}): {', '.join(sorted(existing_columns))}")
print()

# ==========================================
# NEW COLUMNS TO ADD
# ==========================================

NEW_COLUMNS = [
    ("finbert_score",       "FLOAT",        "FinBERT score (copy of sentiment_score)"),
    ("llm_score",           "FLOAT",        "LLM price impact score [-1.0, +1.0]"),
    ("llm_price_impact",    "VARCHAR(20)",  "strong_up|up|neutral|down|strong_down"),
    ("llm_impact_level",    "INTEGER",      "1-5 (1=minimal, 5=extreme)"),
    ("llm_impact_duration", "VARCHAR(20)",  "hours|days|weeks|permanent"),
    ("llm_catalyst_type",   "VARCHAR(30)",  "earnings|macro|regulatory|corporate_action|analyst|sector|other"),
    ("llm_priced_in",       "BOOLEAN",      "true if already priced in by market"),
    ("llm_confidence",      "VARCHAR(10)",  "low|medium|high"),
    ("llm_reason",          "VARCHAR(100)", "max 10 word reason"),
    ("llm_latency_ms",      "INTEGER",      "API response time in ms"),
    ("active_score",        "FLOAT",        "ScoreResolver output: llm_score or finbert_score"),
    ("active_score_source", "VARCHAR(10)",  "llm | finbert"),
]

print("=" * 70)
print("[MIGRATE] Applying migrations...\n")

migrations_applied = 0
migrations_skipped = 0

for col_name, col_type, col_desc in NEW_COLUMNS:
    if col_name in existing_columns:
        print(f"   [OK] {col_name} -- already exists (skip)")
        migrations_skipped += 1
    else:
        try:
            cursor.execute(f"ALTER TABLE news_items ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"   [ADD] {col_name} ({col_type}) -- ADDED  [{col_desc}]")
            migrations_applied += 1
        except Exception as e:
            print(f"   [ERR] {col_name} -- ERROR: {e}")
            conn.rollback()

# ==========================================
# VERIFY
# ==========================================

print("\n" + "=" * 70)
print("[VERIFY] Verifying changes...\n")

cursor.execute("PRAGMA table_info(news_items)")
new_columns = {row[1] for row in cursor.fetchall()}

expected_new = {col[0] for col in NEW_COLUMNS}
missing = expected_new - new_columns
if missing:
    print(f"[WARN] Still missing columns: {missing}")
else:
    print(f"[OK] All {len(NEW_COLUMNS)} LLM columns present in news_items table")

# Verify sentiment_score still exists (CRITICAL)
if "sentiment_score" in new_columns:
    print("[OK] sentiment_score column intact (backward compat OK)")
else:
    print("[CRITICAL] sentiment_score column MISSING!")

# ==========================================
# SUMMARY
# ==========================================

print("\n" + "=" * 70)
if migrations_applied > 0:
    print(f"[OK] Migration complete! {migrations_applied} column(s) added, {migrations_skipped} already existed")
else:
    print("[OK] Database schema already up-to-date. No migrations needed.")

print("\n[NEXT] Start the updated backend")
print("=" * 70)

conn.close()
