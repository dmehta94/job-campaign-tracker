"""Close out applications that never got a reply.

An application still marked Applied or ATS Screened three months after it was submitted is
recorded as 'Rejected (No Response)'. If a reply turns up later (a rejection email, or you
change the status yourself), that replaces it.

Databases created before November 2026 don't allow the new status yet; upgrade_database()
adds it, writing a backup copy first.
"""
import os
import shutil
import sqlite3
from datetime import date, datetime

NO_RESPONSE = "Rejected (No Response)"
NO_RESPONSE_MONTHS = 3
WAITING = ("Applied", "ATS Screened")

STATUSES = ("Applied", "ATS Screened", "Recruiter Screened", "Technical Screened", "Interviewed",
            "Offered", "Accepted", "Rejected by Org", NO_RESPONSE, "Rejected Offer")


def needs_upgrade(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'applications'").fetchone()
    return bool(row) and NO_RESPONSE not in row[0]


def upgrade_database(db_path: str) -> str | None:
    """Allow the 'Rejected (No Response)' status in an older database. Returns the backup path,
    or None if no upgrade was needed. SQLite can't change a CHECK constraint in place, so the
    applications table is rebuilt inside one transaction."""
    if not db_path or not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    try:
        if not needs_upgrade(conn):
            return None
    finally:
        conn.close()

    backup = f"{db_path}.backup-{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(db_path, backup)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    status_list = ", ".join(f"'{s}'" for s in STATUSES)
    try:
        conn.execute("BEGIN")
        conn.execute(
            f'''
            CREATE TABLE applications_new (
                id INTEGER PRIMARY KEY,
                org_id INTEGER REFERENCES orgs(id) ON DELETE SET NULL,
                role_title TEXT NOT NULL,
                job_url TEXT,
                date_applied TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ({status_list})) DEFAULT 'Applied',
                referral_contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
                follow_up_date TEXT,
                notes TEXT
            )
            '''
        )
        conn.execute(
            '''
            INSERT INTO applications_new
                (id, org_id, role_title, job_url, date_applied, status, referral_contact_id, follow_up_date, notes)
            SELECT id, org_id, role_title, job_url, date_applied, status, referral_contact_id, follow_up_date, notes
            FROM applications
            '''
        )
        conn.execute("DROP TABLE applications")
        conn.execute("ALTER TABLE applications_new RENAME TO applications")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_referral_contact_id ON applications (referral_contact_id)")
        problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            raise RuntimeError(f"Foreign key check failed: {problems}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
    return backup


def close_unanswered(db: sqlite3.Connection, today: date | None = None, dry_run: bool = False) -> list[str]:
    """Mark applications with no reply after three months as 'Rejected (No Response)'.
    Returns one line per application changed, for display."""
    if needs_upgrade(db):
        return []  # older database: upgrade_database() runs first at startup
    today = today or date.today()
    rows = db.execute(
        f'''
        SELECT a.id, coalesce(o.name, 'Unknown organization'), a.role_title, a.date_applied
        FROM applications AS a
        LEFT JOIN orgs AS o ON a.org_id = o.id
        WHERE a.status IN ({", ".join("?" for _ in WAITING)})
            AND a.date_applied != ''
            AND date(a.date_applied) <= date(?, '-{NO_RESPONSE_MONTHS} months')
        ORDER BY a.date_applied
        ''',
        (*WAITING, today.isoformat()),
    ).fetchall()
    changes = [f"No response in three months: {org} — {role} (applied {applied})" for _, org, role, applied in rows]
    if rows and not dry_run:
        db.executemany(
            "UPDATE applications SET status = ?, follow_up_date = NULL, "
            "notes = trim(coalesce(notes, '') || ' No reply within three months; closed ' || ?) WHERE id = ?",
            [(NO_RESPONSE, today.isoformat() + ".", app_id) for app_id, *_ in rows],
        )
        db.commit()
    return changes
