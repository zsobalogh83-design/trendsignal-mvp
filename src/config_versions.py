"""
Config Versions — felhasználó által névvel ellátott, visszaállítható config snapshots.

Elkülönül a config_history audit log-tól:
- config_history: nyers before-state napló, debug célra
- config_versions: elnevezett, verzióval ellátott snapshots, UI-ból kezelhető
"""
import json
import sqlite3
from pathlib import Path
from typing import Optional

_DB_PATH = Path(__file__).resolve().parent.parent / "trendsignal.db"


def _db(path: Path = _DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config_versions (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            version     INTEGER  NOT NULL DEFAULT 0,
            name        TEXT     NOT NULL,
            source      TEXT     NOT NULL DEFAULT 'manual',
            config_json TEXT     NOT NULL,
            saved_at    TEXT     NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M', 'now')),
            is_active   INTEGER  NOT NULL DEFAULT 0
        )
    """)
    # Trigger: auto-set sequential version number on insert
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS config_versions_set_version
        AFTER INSERT ON config_versions
        BEGIN
            UPDATE config_versions
            SET version = (
                SELECT COALESCE(MAX(version), 0) + 1
                FROM config_versions
                WHERE id != NEW.id
            )
            WHERE id = NEW.id;
        END
    """)
    conn.commit()


def save_version(name: str, source: str, config_snapshot: dict,
                 db_path: Path = _DB_PATH) -> int:
    """
    Elmenti az aktuális config állapotot névvel és forrással.
    Visszaadja az új sor id-ját.
    Az új verzió automatikusan aktívvá válik.
    """
    conn = _db(db_path)
    _ensure_table(conn)
    # Deactivate all previous
    conn.execute("UPDATE config_versions SET is_active = 0")
    cur = conn.execute(
        "INSERT INTO config_versions (name, source, config_json, is_active) VALUES (?, ?, ?, 1)",
        (name, source, json.dumps(config_snapshot, indent=2))
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def set_active(version_id: int, db_path: Path = _DB_PATH) -> None:
    """Beállítja az aktív verziót (a többit deaktiválja)."""
    conn = _db(db_path)
    _ensure_table(conn)
    conn.execute("UPDATE config_versions SET is_active = 0")
    conn.execute("UPDATE config_versions SET is_active = 1 WHERE id = ?", (version_id,))
    conn.commit()
    conn.close()


def get_active(db_path: Path = _DB_PATH) -> Optional[dict]:
    """Visszaadja az aktív verziót, vagy None-t ha nincs."""
    conn = _db(db_path)
    _ensure_table(conn)
    row = conn.execute(
        "SELECT * FROM config_versions WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_versions(limit: int = 50, db_path: Path = _DB_PATH) -> list:
    """Visszaadja az összes verziót csökkenő sorrendben (config_json nélkül)."""
    conn = _db(db_path)
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT id, version, name, source, saved_at, is_active FROM config_versions ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_version(version_id: int, db_path: Path = _DB_PATH) -> Optional[dict]:
    """Visszaad egy konkrét verziót (config_json-nal együtt)."""
    conn = _db(db_path)
    _ensure_table(conn)
    row = conn.execute(
        "SELECT * FROM config_versions WHERE id = ?", (version_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
