"""
Egyszeri migrációs script: api_quotas tábla létrehozása a meglévő DB-ben.

Futtatás (projekt gyökeréből):
    python migrate_create_api_quotas.py

Ha az api_quotas tábla már létezik, a script ezt jelzi és kilép.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "trendsignal.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_quotas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      VARCHAR(50)  NOT NULL,
    date        DATE         NOT NULL,
    daily_count INTEGER      NOT NULL DEFAULT 0,
    last_reset_at DATETIME   DEFAULT (CURRENT_TIMESTAMP),
    updated_at  DATETIME     DEFAULT (CURRENT_TIMESTAMP)
);
"""

CREATE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS ix_api_quotas_id     ON api_quotas(id);",
    "CREATE INDEX IF NOT EXISTS ix_api_quotas_source ON api_quotas(source);",
    "CREATE INDEX IF NOT EXISTS ix_api_quotas_date   ON api_quotas(date);",
]


def main():
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    print(f"[DB] {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()

        # Check if table already exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_quotas'")
        if cur.fetchone():
            print("[OK] api_quotas table already exists - nothing to do.")
            return

        # Create table + indexes
        cur.execute(CREATE_TABLE_SQL)
        for idx_sql in CREATE_INDEX_SQL:
            cur.execute(idx_sql)
        conn.commit()
        print("[OK] api_quotas table created successfully.")

        # Verify
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_quotas'")
        print(f"   Verify: {cur.fetchone()}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
