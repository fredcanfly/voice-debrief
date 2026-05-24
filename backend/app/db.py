from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATION_0001 = "0001_initial_schema"

MIGRATION_0001_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS debrief_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_sqlite(sqlite_db_path: str | Path) -> Path:
    db_path = Path(sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(MIGRATION_0001_SQL)
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (migration_name)
            VALUES (?)
            """,
            (MIGRATION_0001,),
        )
        conn.commit()

    return db_path
