from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_weekly_usage_summary(db_path: str | Path, out_path: str | Path) -> Path:
    db_path = Path(db_path)
    out_path = Path(out_path)

    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) as n
            FROM debrief_usage_events
            WHERE created_at >= ?
            GROUP BY event_type
            ORDER BY event_type ASC
            """,
            (since,),
        ).fetchall()

    totals = {str(event): int(n) for event, n in rows}
    keys = [
        'session_created',
        'session_started',
        'session_ended',
        'transcribe',
        'followup_question',
        'followup_audio',
        'document_generated',
        'document_downloaded',
        'feedback_received',
    ]

    lines = ['# Weekly Usage Summary', '', f'- Window start (UTC): {since}', '']
    for key in keys:
        lines.append(f'- {key}: {totals.get(key, 0)}')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return out_path
