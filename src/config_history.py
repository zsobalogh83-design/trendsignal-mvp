"""
Config History — minden config.json íráskor snapshot a DB-be.

Az előző állapotot menti el (before-state), így bármikor visszaállítható
az előző verzióra. Külön sqlite3 kapcsolatot használ (WAL-safe), import
körök elkerülése érdekében nincs top-level DB hívás.
"""
import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "trendsignal.db"


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            changed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            source      TEXT      NOT NULL,
            config_json TEXT      NOT NULL
        )
    """)
    conn.commit()


def save_config_history(source: str, config_snapshot: dict) -> None:
    """
    Menti az aktuális (írás ELŐTTI) config állapotot.

    Args:
        source:          Azonosító, pl. "optimizer:42", "manual:component_weights",
                         "manual:decay", "auto_migration"
        config_snapshot: A teljes config dict az írás előtt (before-state).
    """
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO config_history (source, config_json) VALUES (?, ?)",
            (source, json.dumps(config_snapshot, indent=2))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] config_history: snapshot mentés sikertelen ({source}): {e}")
