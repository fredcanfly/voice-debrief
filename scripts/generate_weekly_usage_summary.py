#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.usage_reports import generate_weekly_usage_summary


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate weekly usage summary from SQLite usage events.')
    parser.add_argument('--db', required=True, help='Path to SQLite DB')
    parser.add_argument('--out', required=True, help='Output markdown file path')
    args = parser.parse_args()

    generate_weekly_usage_summary(args.db, args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
