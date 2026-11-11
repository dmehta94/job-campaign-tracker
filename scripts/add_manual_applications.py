"""One-time: log applications that never sent a confirmation email.

Run after the Gmail backfill, from the project root:
    python scripts/add_manual_applications.py

Safe to run twice: an application already logged for the same org and role is skipped.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

# (org, role, date applied, status, notes)
ENTRIES = [
    ("Associated Press", "Data Scientist - Machine Learning", "2026-05-18", "Rejected (No Response)",
     "Added by hand. Date is approximate (recruiter screen with Andrea Ommen, mid-May 2026). "
     "No reply after the screen; the role was later relisted."),
    ("Protect Democracy", "Talent pool", "2026-04-02", "Applied",
     "Added by hand. Joined the talent pool; no confirmation email."),
    ("Queensborough Community College (CUNY)", "Adjunct Lecturer, Mathematics and Computer Science",
     "2026-08-21", "Applied",
     "Added by hand. Emailed availability and CV to Dr. Yao, department chair."),
]


def main() -> None:
    db_path = config["default"].DATABASE_URI
    conn = sqlite3.connect(db_path)
    for org, role, applied, status, notes in ENTRIES:
        row = conn.execute("SELECT id FROM orgs WHERE lower(name) = lower(?)", (org,)).fetchone()
        org_id = row[0] if row else conn.execute(
            "INSERT INTO orgs (name, notes) VALUES (?, ?)", (org, "Added by hand, Nov 2026.")).lastrowid
        if conn.execute("SELECT 1 FROM applications WHERE org_id = ? AND lower(role_title) = lower(?)",
                        (org_id, role)).fetchone():
            print(f"Already logged: {org} - {role}")
            continue
        conn.execute("INSERT INTO applications (org_id, role_title, date_applied, status, notes) "
                     "VALUES (?, ?, ?, ?, ?)", (org_id, role, applied, status, notes))
        print(f"Logged: {org} - {role} ({applied}, {status})")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
