#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate weekly usage summary from SQLite usage events.')
    parser.add_argument('--db', required=True, help='Path to SQLite DB')
    parser.add_argument('--out', required=True, help='Output markdown file path')
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)

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
    ]

    lines = ['# Weekly Usage Summary', '', f'- Window start (UTC): {since}', '']
    for key in keys:
        lines.append(f'- {key}: {totals.get(key, 0)}')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
