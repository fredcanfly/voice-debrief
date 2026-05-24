import sqlite3

from backend.app.db import MIGRATION_0001, init_sqlite


def test_sqlite_init_creates_db_and_baseline_migration(tmp_path):
    db_path = tmp_path / "data" / "voice_debrief.sqlite3"

    created_path = init_sqlite(db_path)

    assert created_path.exists()

    with sqlite3.connect(created_path) as conn:
        migration = conn.execute(
            "SELECT migration_name FROM schema_migrations WHERE migration_name = ?",
            (MIGRATION_0001,),
        ).fetchone()
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='debrief_sessions'"
        ).fetchone()

    assert migration is not None
    assert table is not None
