#!/usr/bin/env python3
"""
CLI-friendly log viewer for Chalukya Tiles admin diagnostics.

Usage (from project root, with venv active):

  python -m tools.logs_cli
  python -m tools.logs_cli --kind app --limit 50
  python -m tools.logs_cli --kind user --limit 100
  python -m tools.logs_cli --kind both --level ERROR

Timestamps are ISO-8601 UTC as stored in SQLite.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db import init_db, list_app_logs, list_user_logs, utc_now_iso  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="logs_cli",
        description="Dump Chalukya Tiles application / user logs (CLI-friendly).",
    )
    parser.add_argument(
        "--kind",
        choices=("app", "user", "both"),
        default="both",
        help="Which logs to print (default: both)",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max rows per log type")
    parser.add_argument("--level", default=None, help="Filter app logs by level e.g. ERROR")
    parser.add_argument("--user", default=None, dest="username", help="Filter user logs by username")
    args = parser.parse_args()

    init_db()
    print(f"# Chalukya Tiles logs · {utc_now_iso()} UTC")
    print(f"# kind={args.kind} limit={args.limit}")

    if args.kind in ("app", "both"):
        print("\n## APPLICATION LOGS")
        rows = list_app_logs(limit=args.limit, level=args.level)
        if not rows:
            print("(empty)")
        for r in rows:
            extra = f" | {r.get('detail')}" if r.get("detail") else ""
            print(
                f"[{r.get('created_at')}] {r.get('level')} {r.get('source')}: "
                f"{r.get('message')}{extra}"
            )

    if args.kind in ("user", "both"):
        print("\n## USER LOGS")
        rows = list_user_logs(limit=args.limit, username=args.username)
        if not rows:
            print("(empty)")
        for r in rows:
            ent = ""
            if r.get("entity_type"):
                ent = f" entity={r.get('entity_type')}:{r.get('entity_id')}"
            extra = f" | {r.get('detail')}" if r.get("detail") else ""
            print(
                f"[{r.get('created_at')}] user={r.get('username')} "
                f"action={r.get('action')}{ent}{extra}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
