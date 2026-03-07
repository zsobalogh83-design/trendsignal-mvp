"""
Migration: Add BCD optimizer tables and columns

Changes:
  1. ALTER TABLE optimization_runs  ADD COLUMN run_type TEXT DEFAULT 'GA'
  2. ALTER TABLE optimization_runs  ADD COLUMN bcd_block_impact TEXT
  3. CREATE TABLE bcd_rounds        (per-round BCD tracking)

Safe to run multiple times (checks before adding).

Usage:
    python migrate_add_bcd_tables.py
    python migrate_add_bcd_tables.py --db-path path/to/trendsignal.db
"""

import argparse
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"


def get_existing_columns(conn: sqlite3.Connection, table: str):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def run_migration(db_path: Path):
    print(f"[Migration] DB: {db_path}")

    conn = sqlite3.connect(str(db_path))

    try:
        # ------------------------------------------------------------------
        # 1. Add run_type column to optimization_runs
        # ------------------------------------------------------------------
        existing = get_existing_columns(conn, "optimization_runs")

        if "run_type" not in existing:
            conn.execute(
                "ALTER TABLE optimization_runs ADD COLUMN run_type TEXT NOT NULL DEFAULT 'GA'"
            )
            print("[Migration] OK  Added optimization_runs.run_type")
        else:
            print("[Migration] --  optimization_runs.run_type already exists")

        # ------------------------------------------------------------------
        # 2. Add bcd_block_impact column to optimization_runs
        # ------------------------------------------------------------------
        if "bcd_block_impact" not in existing:
            conn.execute(
                "ALTER TABLE optimization_runs ADD COLUMN bcd_block_impact TEXT"
            )
            print("[Migration] OK  Added optimization_runs.bcd_block_impact")
        else:
            print("[Migration] --  optimization_runs.bcd_block_impact already exists")

        # ------------------------------------------------------------------
        # 3. Create bcd_rounds table
        # ------------------------------------------------------------------
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bcd_rounds'"
        )
        if cur.fetchone() is None:
            conn.execute("""
                CREATE TABLE bcd_rounds (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id           INTEGER NOT NULL
                                     REFERENCES optimization_runs(id) ON DELETE CASCADE,
                    round_number     INTEGER NOT NULL,
                    unit_ids         TEXT    NOT NULL,
                    active_dims      TEXT    NOT NULL,
                    n_active_dims    INTEGER NOT NULL,
                    fitness_before   REAL    NOT NULL,
                    fitness_after    REAL    NOT NULL,
                    improvement_pct  REAL    NOT NULL,
                    accepted         INTEGER NOT NULL DEFAULT 0,
                    elapsed_seconds  REAL,
                    recorded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE INDEX idx_bcd_rounds_run_id ON bcd_rounds(run_id)"
            )
            conn.execute(
                "CREATE INDEX idx_bcd_rounds_round  ON bcd_rounds(run_id, round_number)"
            )
            print("[Migration] OK  Created bcd_rounds table + indexes")
        else:
            print("[Migration] --  bcd_rounds table already exists")

        conn.commit()
        print("[Migration] OK  Migration complete.")

    except Exception as e:
        conn.rollback()
        print(f"[Migration] ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add BCD tables to TrendSignal DB")
    parser.add_argument("--db-path", type=str, default=str(DATABASE_PATH))
    args = parser.parse_args()

    run_migration(Path(args.db_path))
