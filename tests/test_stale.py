"""Tests for closing applications that got no reply within three months."""
import os
import sqlite3
from datetime import date

from app import email_import as ei
from app import stale
from app.database import get_db


def _add(db, role, applied, status="Applied", org="Example Labs"):
    org_id = db.execute("SELECT id FROM orgs WHERE name = ?", (org,)).fetchone()
    org_id = org_id[0] if org_id else db.execute("INSERT INTO orgs (name) VALUES (?)", (org,)).lastrowid
    db.execute("INSERT INTO applications (org_id, role_title, date_applied, status, follow_up_date) "
               "VALUES (?, ?, ?, ?, '2026-01-01')", (org_id, role, applied, status))
    db.commit()


def test_closes_only_unanswered_applications_older_than_three_months(app):
    db = get_db()
    _add(db, "Old, no reply", "2026-08-04")
    _add(db, "Exactly three months", "2026-08-05")
    _add(db, "Recent", "2026-09-01")
    _add(db, "Old but interviewed", "2026-04-01", status="Interviewed")
    _add(db, "Old ATS screen", "2026-05-01", status="ATS Screened")
    changes = stale.close_unanswered(db, today=date(2026, 11, 5))
    assert len(changes) == 3
    rows = dict(db.execute("SELECT role_title, status FROM applications").fetchall())
    assert rows["Old, no reply"] == rows["Exactly three months"] == rows["Old ATS screen"] == stale.NO_RESPONSE
    assert rows["Recent"] == "Applied" and rows["Old but interviewed"] == "Interviewed"
    follow = db.execute("SELECT follow_up_date, notes FROM applications WHERE role_title = 'Old, no reply'").fetchone()
    assert follow[0] is None and "No reply within three months" in follow[1]
    assert stale.close_unanswered(db, today=date(2026, 11, 5)) == []  # nothing left to close


def test_dry_run_changes_nothing(app):
    db = get_db()
    _add(db, "Old", "2026-01-10")
    assert len(stale.close_unanswered(db, today=date(2026, 11, 5), dry_run=True)) == 1
    assert db.execute("SELECT status FROM applications").fetchone()[0] == "Applied"


def test_late_rejection_email_replaces_no_response(app):
    db = get_db()
    _add(db, "Data Analyst", "2026-06-01", status=stale.NO_RESPONSE, org="Example Analytics")
    m = ei.Message("<late>", date(2026, 10, 1), "Your application to Example Analytics - Data Analyst",
                   "", "no-reply@example.com",
                   "Unfortunately, we will not be moving forward with your candidacy for the Data Analyst role.")
    assert ei.apply_messages(db, [m]) == ["Rejected: Example Analytics — Data Analyst (2026-10-01)"]
    assert db.execute("SELECT status FROM applications").fetchone()[0] == "Rejected by Org"


def test_reapplying_in_a_later_cycle_logs_a_new_application(app):
    db = get_db()
    _add(db, "Data Analyst", "2026-03-01", status=stale.NO_RESPONSE, org="Example Analytics")
    m = ei.Message("<again>", date(2026, 11, 4), "Thank you for applying to Example Analytics - Data Analyst",
                   "", "no-reply@example.com", "Thank you for your application to the Data Analyst position.")
    assert ei.apply_messages(db, [m]) == ["Applied: Example Analytics — Data Analyst (2026-11-04)"]
    assert db.execute("SELECT count(*) FROM applications").fetchone()[0] == 2


def test_dashboard_closes_stale_applications(client, app):
    db = get_db()
    _add(db, "Forgotten role", "2025-12-01")
    page = client.get("/").get_data(as_text=True)
    assert "no reply after three months" in page and "Forgotten role" in page


def test_upgrade_adds_status_to_an_old_database(tmp_path):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE orgs (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY, org_id INTEGER REFERENCES orgs(id) ON DELETE SET NULL,
            role_title TEXT NOT NULL, job_url TEXT, date_applied TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Applied', 'ATS Screened', 'Recruiter Screened',
                'Technical Screened', 'Interviewed', 'Offered', 'Accepted', 'Rejected by Org', 'Rejected Offer'))
                DEFAULT 'Applied',
            referral_contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
            follow_up_date TEXT, notes TEXT);
        INSERT INTO orgs (name) VALUES ('Example Labs');
        INSERT INTO applications (org_id, role_title, date_applied) VALUES (1, 'Analyst', '2026-01-02');
        """)
    conn.commit()
    conn.close()
    backup = stale.upgrade_database(path)
    assert backup and os.path.exists(backup)
    conn = sqlite3.connect(path)
    assert not stale.needs_upgrade(conn)
    assert conn.execute("SELECT role_title, status FROM applications").fetchone() == ("Analyst", "Applied")
    assert len(stale.close_unanswered(conn, today=date(2026, 11, 5))) == 1
    conn.close()
    assert stale.upgrade_database(path) is None  # second run: nothing to do
