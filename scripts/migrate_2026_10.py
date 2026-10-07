"""Upgrade an existing job-campaign-tracker database to the October 2026 schema.

Changes applied:
    - orgs.category: the four LAMP-list clusters are replaced by
      Education, NYC Government, Civic Tech, Research & Policy, Higher Ed.
      'Civic Tech' and 'Research & Policy' carry over; other old categories become blank.
    - orgs.lamp_list is replaced by orgs.tier1 (0/1, default 0).
    - interactions.interaction_type gains 'Follow-up'.

SQLite can't alter CHECK constraints in place, so each table is rebuilt
(create new table, copy rows, drop old, rename) inside one transaction.
A timestamped backup copy of the database is written first.

Usage (from the project root, with your .env in place):
    python scripts/migrate_2026_10.py
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

CARRIED_CATEGORIES = ('Civic Tech', 'Research & Policy')


def column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def migrate(db_path: str) -> None:
    if not db_path or not os.path.exists(db_path):
        sys.exit(f"Database not found at {db_path!r}. Check DATABASE_URI in your .env.")

    conn = sqlite3.connect(db_path)
    if 'tier1' in column_names(conn, 'orgs'):
        print("Database is already on the October 2026 schema. Nothing to do.")
        conn.close()
        return

    backup = f"{db_path}.backup-{datetime.now():%Y%m%d-%H%M%S}"
    conn.close()
    shutil.copy2(db_path, backup)
    print(f"Backup written to {backup}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    old_orgs = conn.execute("SELECT name, category FROM orgs").fetchall()

    try:
        conn.execute("BEGIN")
        conn.execute(
            '''
            CREATE TABLE orgs_new (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                careers_url TEXT,
                category TEXT CHECK (category IN ('Education', 'NYC Government', 'Civic Tech', 'Research & Policy', 'Higher Ed')),
                tier1 INTEGER NOT NULL CHECK (tier1 IN (0,1)) DEFAULT 0,
                notes TEXT,
                created_date TEXT DEFAULT CURRENT_DATE
            )
            '''
        )
        conn.execute(
            f'''
            INSERT INTO orgs_new (id, name, careers_url, category, tier1, notes, created_date)
            SELECT
                id, name, careers_url,
                CASE WHEN category IN {CARRIED_CATEGORIES} THEN category ELSE NULL END,
                0, notes, created_date
            FROM orgs
            '''
        )
        conn.execute("DROP TABLE orgs")
        conn.execute("ALTER TABLE orgs_new RENAME TO orgs")

        conn.execute(
            '''
            CREATE TABLE interactions_new (
                id INTEGER PRIMARY KEY,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                interaction_type TEXT NOT NULL CHECK (interaction_type IN ('Outreach Established', 'Follow-up', 'Informational Interview', 'Referral Received', 'Coffee Chat', 'Reconnect')) DEFAULT 'Outreach Established',
                notes TEXT,
                date TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            INSERT INTO interactions_new (id, contact_id, interaction_type, notes, date)
            SELECT id, contact_id, interaction_type, notes, date FROM interactions
            '''
        )
        conn.execute("DROP TABLE interactions")
        conn.execute("ALTER TABLE interactions_new RENAME TO interactions")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contact_id ON interactions (contact_id)")

        problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            raise RuntimeError(f"Foreign key check failed: {problems}")
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        print("Migration failed; the database was left unchanged.")
        raise
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    print(f"Migrated {len(old_orgs)} org(s).")
    for name, category in old_orgs:
        if category and category not in CARRIED_CATEGORIES:
            print(f"  - {name}: category '{category}' cleared; pick a new one on its detail page.")
    print("Done.")


if __name__ == '__main__':
    migrate(config['default'].DATABASE_URI)
