from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4


MIGRATION_0001 = "0001_initial_schema"
MIGRATION_0002 = "0002_session_lifecycle"

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

MIGRATION_0002_SQL = """
ALTER TABLE debrief_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'created';
ALTER TABLE debrief_sessions ADD COLUMN started_at TEXT;
ALTER TABLE debrief_sessions ADD COLUMN ended_at TEXT;
"""


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


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

        if not _has_column(conn, "debrief_sessions", "status"):
            conn.executescript(MIGRATION_0002_SQL)
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (migration_name)
            VALUES (?)
            """,
            (MIGRATION_0002,),
        )
        conn.commit()

    return db_path


def create_session(sqlite_db_path: str | Path, session_id: str | None = None) -> str:
    sid = session_id or f"debrief-{uuid4().hex[:12]}"
    with sqlite3.connect(sqlite_db_path) as conn:
        conn.execute(
            """
            INSERT INTO debrief_sessions (session_id, status)
            VALUES (?, 'created')
            """,
            (sid,),
        )
        conn.commit()
    return sid


def set_session_started(sqlite_db_path: str | Path, session_id: str) -> None:
    with sqlite3.connect(sqlite_db_path) as conn:
        cur = conn.execute(
            """
            UPDATE debrief_sessions
            SET status='started', started_at=COALESCE(started_at, datetime('now')), updated_at=datetime('now')
            WHERE session_id=?
            """,
            (session_id,),
        )
        if cur.rowcount == 0:
            raise ValueError("session not found")
        conn.commit()


def set_session_ended(sqlite_db_path: str | Path, session_id: str) -> None:
    with sqlite3.connect(sqlite_db_path) as conn:
        cur = conn.execute(
            """
            UPDATE debrief_sessions
            SET status='ended', ended_at=datetime('now'), updated_at=datetime('now')
            WHERE session_id=?
            """,
            (session_id,),
        )
        if cur.rowcount == 0:
            raise ValueError("session not found")
        conn.commit()


def get_session(sqlite_db_path: str | Path, session_id: str) -> dict[str, str | None]:
    with sqlite3.connect(sqlite_db_path) as conn:
        row = conn.execute(
            """
            SELECT session_id, status, started_at, ended_at
            FROM debrief_sessions
            WHERE session_id=?
            """,
            (session_id,),
        ).fetchone()
    if row is None:
        raise ValueError("session not found")
    return {"session_id": row[0], "status": row[1], "started_at": row[2], "ended_at": row[3]}
