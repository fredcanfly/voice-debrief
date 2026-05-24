from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4


MIGRATION_0001 = "0001_initial_schema"
MIGRATION_0002 = "0002_session_lifecycle"
MIGRATION_0003 = "0003_transcripts"
MIGRATION_0004 = "0004_memory_facts"
MIGRATION_0005 = "0005_skill_hints"

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

MIGRATION_0003_SQL = """
CREATE TABLE IF NOT EXISTS debrief_transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    transcript_text TEXT NOT NULL,
    stt_model TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES debrief_sessions(session_id)
);
"""

MIGRATION_0004_SQL = """
CREATE TABLE IF NOT EXISTS debrief_memory_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    fact_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES debrief_sessions(session_id)
);
"""

MIGRATION_0005_SQL = """
CREATE TABLE IF NOT EXISTS debrief_skill_hints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    hint_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES debrief_sessions(session_id)
);
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

        conn.executescript(MIGRATION_0003_SQL)
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (migration_name)
            VALUES (?)
            """,
            (MIGRATION_0003,),
        )

        conn.executescript(MIGRATION_0004_SQL)
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (migration_name)
            VALUES (?)
            """,
            (MIGRATION_0004,),
        )

        conn.executescript(MIGRATION_0005_SQL)
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (migration_name)
            VALUES (?)
            """,
            (MIGRATION_0005,),
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


def save_transcript(sqlite_db_path: str | Path, session_id: str, transcript_text: str, stt_model: str | None) -> None:
    with sqlite3.connect(sqlite_db_path) as conn:
        conn.execute(
            """
            INSERT INTO debrief_transcripts (session_id, transcript_text, stt_model)
            VALUES (?, ?, ?)
            """,
            (session_id, transcript_text, stt_model),
        )
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


def get_latest_transcript(sqlite_db_path: str | Path, session_id: str) -> dict[str, str | None] | None:
    with sqlite3.connect(sqlite_db_path) as conn:
        row = conn.execute(
            """
            SELECT transcript_text, stt_model, created_at
            FROM debrief_transcripts
            WHERE session_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "transcript_text": row[0],
        "stt_model": row[1],
        "created_at": row[2],
    }


def get_session_transcripts(sqlite_db_path: str | Path, session_id: str) -> list[dict[str, str | None]]:
    with sqlite3.connect(sqlite_db_path) as conn:
        rows = conn.execute(
            """
            SELECT transcript_text, stt_model, created_at
            FROM debrief_transcripts
            WHERE session_id=?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()

    return [
        {"transcript_text": r[0], "stt_model": r[1], "created_at": r[2]}
        for r in rows
    ]


def save_memory_facts(sqlite_db_path: str | Path, session_id: str, facts: list[str]) -> None:
    clean_facts = [f.strip() for f in facts if str(f).strip()]
    if not clean_facts:
        return

    with sqlite3.connect(sqlite_db_path) as conn:
        conn.executemany(
            """
            INSERT INTO debrief_memory_facts (session_id, fact_text)
            VALUES (?, ?)
            """,
            [(session_id, fact) for fact in clean_facts],
        )
        conn.commit()


def get_session_memory_facts(sqlite_db_path: str | Path, session_id: str, limit: int = 20) -> list[str]:
    with sqlite3.connect(sqlite_db_path) as conn:
        rows = conn.execute(
            """
            SELECT fact_text
            FROM debrief_memory_facts
            WHERE session_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

    return [r[0] for r in reversed(rows)]


def save_skill_hints(sqlite_db_path: str | Path, session_id: str, hints: list[str]) -> None:
    clean_hints = [h.strip() for h in hints if str(h).strip()]
    if not clean_hints:
        return

    with sqlite3.connect(sqlite_db_path) as conn:
        conn.executemany(
            """
            INSERT INTO debrief_skill_hints (session_id, hint_text)
            VALUES (?, ?)
            """,
            [(session_id, hint) for hint in clean_hints],
        )
        conn.commit()


def get_session_skill_hints(sqlite_db_path: str | Path, session_id: str, limit: int = 20) -> list[str]:
    with sqlite3.connect(sqlite_db_path) as conn:
        rows = conn.execute(
            """
            SELECT hint_text
            FROM debrief_skill_hints
            WHERE session_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

    return [r[0] for r in reversed(rows)]
