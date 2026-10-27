"""Log applications and rejections from your Gmail into the tracker.

Usage (from the project root, with GMAIL_ADDRESS and GMAIL_APP_PASSWORD in your .env):
    python scripts/import_from_gmail.py              # last 14 days
    python scripts/import_from_gmail.py --days 400   # first run: backfill past applications
    python scripts/import_from_gmail.py --dry-run    # show what would change, change nothing

The dashboard's "Check email" button runs the same thing for the last 14 days.
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.email_import import run
from config import config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=14, help="how far back to look (default 14)")
    parser.add_argument("--dry-run", action="store_true", help="show changes without saving them")
    args = parser.parse_args()

    db_path = config["default"].DATABASE_URI
    if not db_path or not os.path.exists(db_path):
        sys.exit(f"Database not found at {db_path!r}. Run this from the project root with your .env in place.")
    conn = sqlite3.connect(db_path)
    try:
        changes = run(conn, days=args.days, dry_run=args.dry_run)
    except RuntimeError as exc:
        sys.exit(str(exc))
    finally:
        conn.close()
    prefix = "Would change" if args.dry_run else "Changed"
    print(f"{prefix} {len(changes)} item(s)" + (":" if changes else "."))
    for line in changes:
        print("  " + line)


if __name__ == "__main__":
    main()
