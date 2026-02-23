"""
Database Migration: Create Self-Tuning Engine tables
TrendSignal - Optimizer v1.0

Creates three new tables:
  - optimization_runs       : one record per full optimization run
  - optimization_generations: per-generation metrics (fitness evolution)
  - config_proposals        : proposed configs awaiting approval

Run this script once from the project root:
    python migrate_create_optimizer_tables.py

Version: 1.0
Date: 2026-02-23
"""

import sqlite3
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"


def migrate():
    print("=" * 60)
    print("TrendSignal - Optimizer Tables Migration")
    print("=" * 60)
    print(f"Database: {DATABASE_PATH}")

    if not DATABASE_PATH.exists():
        print(f"ERROR: trendsignal.db not found at {DATABASE_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DATABASE_PATH))
    cursor = conn.cursor()

    try:
        # ===================================================
        # 1. optimization_runs
        # ===================================================
        print("\n1. Creating optimization_runs table...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_runs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Run lifecycle
                status              TEXT NOT NULL DEFAULT 'RUNNING'
                                    CHECK(status IN ('RUNNING','COMPLETED','FAILED','STOPPED')),
                started_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at        TIMESTAMP,
                duration_seconds    REAL,

                -- GA parameters used
                population_size     INTEGER NOT NULL,
                max_generations     INTEGER NOT NULL,
                dimensions          INTEGER NOT NULL,
                crossover_prob      REAL NOT NULL,
                mutation_prob       REAL NOT NULL,
                tournament_size     INTEGER NOT NULL,

                -- Data split info
                train_signal_count  INTEGER,
                val_signal_count    INTEGER,
                test_signal_count   INTEGER,
                total_signal_count  INTEGER,
                train_trade_count   INTEGER,
                val_trade_count     INTEGER,
                test_trade_count    INTEGER,

                -- Best result summary
                best_train_fitness  REAL,
                best_val_fitness    REAL,
                best_test_fitness   REAL,
                generations_run     INTEGER,

                -- Baseline (current config fitness on test set)
                baseline_fitness    REAL,

                -- Outcome
                proposals_generated INTEGER DEFAULT 0,
                error_message       TEXT,

                -- Audit
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   OK: optimization_runs created")

        # ===================================================
        # 2. optimization_generations
        # ===================================================
        print("\n2. Creating optimization_generations table...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_generations (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id              INTEGER NOT NULL
                                    REFERENCES optimization_runs(id) ON DELETE CASCADE,

                generation          INTEGER NOT NULL,

                -- Population fitness stats
                best_train_fitness  REAL NOT NULL,
                avg_train_fitness   REAL NOT NULL,
                worst_train_fitness REAL NOT NULL,

                -- Validation fitness of best individual
                best_val_fitness    REAL,

                -- Overfitting indicator
                train_val_gap       REAL,

                -- Timing
                recorded_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   OK: optimization_generations created")

        # ===================================================
        # 3. config_proposals
        # ===================================================
        print("\n3. Creating config_proposals table...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_proposals (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id                  INTEGER NOT NULL
                                        REFERENCES optimization_runs(id) ON DELETE CASCADE,

                -- Rank within run (1 = best)
                rank                    INTEGER NOT NULL DEFAULT 1,

                -- Fitness scores
                train_fitness           REAL NOT NULL,
                val_fitness             REAL NOT NULL,
                test_fitness            REAL NOT NULL,
                baseline_fitness        REAL NOT NULL,
                fitness_improvement_pct REAL NOT NULL,

                -- Trade simulation results on test set
                test_trade_count        INTEGER,
                test_win_rate           REAL,
                test_profit_factor      REAL,
                baseline_profit_factor  REAL,

                -- Overfitting check
                train_val_gap           REAL,
                overfitting_ok          INTEGER,        -- 0/1 boolean

                -- Bootstrap statistical significance
                bootstrap_p_value       REAL,
                bootstrap_significant   INTEGER,        -- 0/1 boolean
                bootstrap_iterations    INTEGER DEFAULT 1000,

                -- Walk-forward validation
                wf_window_count         INTEGER,
                wf_positive_count       INTEGER,
                wf_result_json          TEXT,           -- JSON: per-window PF deltas
                wf_consistent           INTEGER,        -- 0/1 (>=4/5 positive)

                -- Market regime breakdown
                regime_trending_pf      REAL,
                regime_trending_trades  INTEGER,
                regime_sideways_pf      REAL,
                regime_sideways_trades  INTEGER,
                regime_highvol_pf       REAL,
                regime_highvol_trades   INTEGER,

                -- Acceptance gates summary
                gate_min_trades_ok      INTEGER,        -- test_trade_count >= 50
                gate_fitness_improvement_ok INTEGER,    -- improvement >= 10%
                gate_bootstrap_ok       INTEGER,        -- p_value < 0.05
                gate_overfitting_ok     INTEGER,        -- train_val_gap <= 20%
                gate_profit_factor_ok   INTEGER,        -- test_pf >= baseline_pf + 0.1
                gate_sideways_pf_ok     INTEGER,        -- sideways_pf >= 1.0 (warning only)

                -- Overall verdict
                -- PROPOSABLE / CONDITIONAL / REJECTED
                verdict                 TEXT CHECK(verdict IN (
                                            'PROPOSABLE','CONDITIONAL','REJECTED'
                                        )),
                verdict_reason          TEXT,           -- human readable summary

                -- The proposed config vector (JSON: {param_name: value})
                config_vector_json      TEXT NOT NULL,

                -- Diff vs current config (JSON: {param_name: {before, after}})
                config_diff_json        TEXT,

                -- User decision
                -- PENDING / APPROVED / REJECTED_BY_USER
                review_status           TEXT NOT NULL DEFAULT 'PENDING'
                                        CHECK(review_status IN (
                                            'PENDING','APPROVED','REJECTED_BY_USER'
                                        )),
                reviewed_at             TIMESTAMP,
                reviewed_by             TEXT DEFAULT 'user',

                -- Audit
                created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   OK: config_proposals created")

        # ===================================================
        # 4. Indexes
        # ===================================================
        print("\n4. Creating indexes...")

        indexes = [
            ("idx_opt_runs_status",      "optimization_runs",       "status"),
            ("idx_opt_runs_started",     "optimization_runs",       "started_at"),
            ("idx_opt_gens_run_id",      "optimization_generations","run_id"),
            ("idx_opt_gens_generation",  "optimization_generations","run_id, generation"),
            ("idx_opt_props_run_id",     "config_proposals",        "run_id"),
            ("idx_opt_props_verdict",    "config_proposals",        "verdict"),
            ("idx_opt_props_review",     "config_proposals",        "review_status"),
        ]

        for idx_name, table, columns in indexes:
            try:
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})"
                )
                print(f"   OK: {idx_name}")
            except sqlite3.OperationalError as e:
                print(f"   SKIP: {idx_name} ({e})")

        # ===================================================
        # 5. Verify
        # ===================================================
        print("\n5. Verifying...")

        for table in ["optimization_runs", "optimization_generations", "config_proposals"]:
            cols = cursor.execute(f"PRAGMA table_info({table})").fetchall()
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"   {table}: {len(cols)} columns, {count} rows")

        conn.commit()

        print("\n" + "=" * 60)
        print("Migration completed successfully.")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
