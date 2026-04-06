"""
Migration: Add 12-component score columns to signal_calculations table.

These columns store the individual component scores from the new 12-component
scoring architecture (replaces the old 3-bucket sentiment/technical/risk model).

Usage:
    python one_offs/migrate_component_scores.py
    python one_offs/migrate_component_scores.py --dry-run
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import engine
from sqlalchemy import text

NEW_COLUMNS = [
    ("sma_trend_score",         "FLOAT"),
    ("rsi_momentum_score",      "FLOAT"),
    ("macd_signal_score",       "FLOAT"),
    ("bb_position_score",       "FLOAT"),
    ("stoch_cross_score",       "FLOAT"),
    ("volume_confirm_score",    "FLOAT"),
    ("sentiment_recency_score", "FLOAT"),
    ("volatility_risk_score",   "FLOAT"),
    ("sr_proximity_score",      "FLOAT"),
    ("trend_strength_score",    "FLOAT"),
    ("rr_quality_score",        "FLOAT"),
]

TABLE = "signal_calculations"


def column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result.fetchall())


def migrate(dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"  Migrating {TABLE}: adding 12-component score columns")
    if dry_run:
        print("  [DRY RUN] -- no changes will be written")
    print(f"{'='*60}\n")

    with engine.connect() as conn:
        added = 0
        skipped = 0
        for col_name, col_type in NEW_COLUMNS:
            if column_exists(conn, TABLE, col_name):
                print(f"  SKIP  {col_name} already exists")
                skipped += 1
            else:
                sql = f"ALTER TABLE {TABLE} ADD COLUMN {col_name} {col_type}"
                print(f"  ADD   {col_name} {col_type}")
                if not dry_run:
                    conn.execute(text(sql))
                added += 1

        if not dry_run and added > 0:
            conn.commit()

    print(f"\n  Summary: {added} column(s) added, {skipped} already existed.")
    if dry_run and added > 0:
        print("  Re-run without --dry-run to apply changes.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Add 12-component score columns to signal_calculations"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing to DB")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
