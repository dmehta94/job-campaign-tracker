'''Tests for logging applications and rejections from email.'''
from datetime import date, datetime

import pytest

from app import email_import as ei
from app.database import get_db


def msg(subject, body, sent=date(2026, 10, 1), mid=None, sender="no-reply@us.greenhouse-mail.io", name=""):
    return ei.Message(message_id=mid or f"<{subject}|{sent}>", sent=sent, subject=subject,
                      sender_name=name, sender_address=sender, body=body)


CONFIRM = ("Hi Deval, Thank you very much for your recent application to the Early Career Data Analyst "
           "position. Our talent acquisition team will review it.")
REJECT = ("Hi Deval, Unfortunately, we have decided not to proceed with your candidacy for the "
          "Applied Data Scientist opening at Example Analytics.")


@pytest.mark.parametrize("subject,body,expected", [
    ("Thank you for applying to Example Labs", CONFIRM, "confirmation"),
    ("Information about your application to Example Analytics - Applied Data Scientist", REJECT, "rejection"),
    ("Application for Data Analyst I - Example Academy",
     "Thank you for your interest! Unfortunately, we won't be able to move you forward with your candidacy.",
     "rejection"),
    ("Security code for your application to Example Labs", "Your code is 123456 for this job.", None),
    ("Important information about your loan application", "Unfortunately your loan was not approved.", None),
    ("Thank you for your interest in the All-New Sedan", "Book a test drive today.", None),
])
def test_classify(subject, body, expected):
    assert ei.classify(subject, body) == expected


@pytest.mark.parametrize("subject,body,org,role", [
    ("Thank you for applying to Example Labs", CONFIRM, "Example Labs", "Early Career Data Analyst"),
    ("Thank you for applying at Example Research Institute", CONFIRM, "Example Research Institute",
     "Early Career Data Analyst"),
    ("Information about your application to Example Analytics - Applied Data Scientist (Contract)", REJECT,
     "Example Analytics", "Applied Data Scientist (Contract)"),
    ("Application for Data Analyst I, Analytics Reporting - Example Academy", "Unfortunately...",
     "Example Academy", "Data Analyst I, Analytics Reporting"),
    ("Thank you for Applying at Example Lab - Anywhere, USA", CONFIRM, "Example Lab", "Early Career Data Analyst"),
    ("Data Analyst - Example Org", "Thanks for applying to the Data Analyst role.", "Example Org", "Data Analyst"),
    ("Fwd: Thank you for applying to Example Bio", "We received your application.", "Example Bio", None),
])
def test_extract(subject, body, org, role):
    assert ei.extract(subject, body) == (org, role)


def test_confirmation_adds_application_once(app):
    db = get_db()
    m = msg("Thank you for applying to Example Labs", CONFIRM)
    changes = ei.apply_messages(db, [m, m])
    assert changes == ["New organization: Example Labs",
                       "Applied: Example Labs — Early Career Data Analyst (2026-10-01)"]
    row = db.execute("SELECT role_title, date_applied, status, follow_up_date FROM applications").fetchone()
    assert tuple(row) == ("Early Career Data Analyst", "2026-10-01", "Applied", "2026-10-11")
    assert ei.apply_messages(db, [m]) == []  # same email on a later run


def test_rejection_updates_matching_application(app):
    db = get_db()
    ei.apply_messages(db, [msg("Thank you for applying to Example Analytics",
                               "Thank you for your application to the Applied Data Scientist position.")])
    changes = ei.apply_messages(db, [msg("Information about your application to Example Analytics - "
                                         "Applied Data Scientist", REJECT, sent=date(2026, 10, 20))])
    assert changes == ["Rejected: Example Analytics — Applied Data Scientist (2026-10-20)"]
    row = db.execute("SELECT status, follow_up_date FROM applications").fetchone()
    assert tuple(row) == ("Rejected by Org", None)
    assert db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 1


def test_rejection_without_logged_application_adds_one(app):
    db = get_db()
    changes = ei.apply_messages(db, [msg("Data Analyst - Example Org",
                                         "Unfortunately we will not be moving forward with your candidacy.")])
    assert changes[-1].startswith("Rejected (application not logged before): Example Org — Data Analyst")
    assert db.execute("SELECT status FROM applications").fetchone()[0] == "Rejected by Org"


def test_matches_existing_org_by_name_words(app):
    db = get_db()
    db.execute("INSERT INTO orgs (name, category) VALUES ('The Example Research Institute', 'Research & Policy')")
    db.commit()
    changes = ei.apply_messages(db, [msg("Thank you for applying at Example Research", CONFIRM)])
    assert not any(c.startswith("New organization") for c in changes)


def test_dry_run_changes_nothing(app):
    db = get_db()
    changes = ei.apply_messages(db, [msg("Thank you for applying to Example Labs", CONFIRM)], dry_run=True)
    assert changes and db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0


def test_skips_emails_you_sent(app):
    db = get_db()
    mine = msg("Example Fellows | Application Received", CONFIRM, sender="me@example.com")
    assert ei.apply_messages(db, [mine], own_address="me@example.com") == []


def test_dashboard_button_reports_changes(app, client, monkeypatch):
    monkeypatch.setattr(ei, "run", lambda db, days=14: ["Applied: Example Labs — Data Analyst (2026-10-01)"])
    response = client.post('/check-email', follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated from your email: Applied: Example Labs" in response.data


def test_dashboard_button_explains_missing_setup(app, client, monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    response = client.post('/check-email', follow_redirects=True)
    assert b"GMAIL_APP_PASSWORD" in response.data


def test_dashboard_lists_applications_to_check_on(app, client):
    db = get_db()
    ei.apply_messages(db, [msg("Thank you for applying to Example Labs", CONFIRM, sent=date.today())])
    response = client.get('/')
    assert b"Applications to Check On" in response.data and b"Example Labs" in response.data
    assert b"Applications this week: 1" in response.data


def test_days_to_check_covers_the_gap_since_last_check(app):
    db = get_db()
    assert ei.days_to_check(db, today=date(2026, 11, 5)) == 14  # never checked
    ei.record_check(db, datetime(2026, 11, 1, 9, 0))
    assert ei.days_to_check(db, today=date(2026, 11, 5)) == 14  # recent: still two weeks
    ei.record_check(db, datetime(2026, 9, 1, 9, 0))  # older rows don't matter; the latest counts
    assert ei.days_to_check(db, today=date(2026, 12, 1)) == 31  # laptop off for a month
    assert ei.days_to_check(db, today=date(2028, 1, 1)) == ei.MAX_DAYS


def test_check_due_needs_credentials_and_an_old_check(app, monkeypatch):
    db = get_db()
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    assert not ei.check_due(db)
    monkeypatch.setenv("GMAIL_ADDRESS", "me@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password")
    assert ei.check_due(db)
    ei.record_check(db, datetime(2026, 11, 5, 8, 0))
    assert not ei.check_due(db, now=datetime(2026, 11, 5, 12, 0))
    assert ei.check_due(db, now=datetime(2026, 11, 5, 20, 0))


def test_run_records_the_check_and_uses_catch_up_window(app, monkeypatch):
    db = get_db()
    monkeypatch.setenv("GMAIL_ADDRESS", "me@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password")
    seen = {}
    monkeypatch.setattr(ei, "fetch_messages", lambda a, p, days: seen.setdefault("days", days) and [])
    ei.run(db, dry_run=True)
    assert seen["days"] == 14 and ei.last_checked(db) is None  # dry runs aren't recorded
    ei.run(db)
    assert ei.last_checked(db) is not None


def test_dashboard_checks_email_on_its_own(client, monkeypatch):
    from app.dashboard import routes
    monkeypatch.setattr(routes, "_last_failed_auto_check", 0.0)
    monkeypatch.setattr(ei, "check_due", lambda db: True)
    monkeypatch.setattr(ei, "run", lambda db, **kw: ["Applied: Example Labs — Data Analyst (2026-11-04)"])
    page = client.get("/").get_data(as_text=True)
    assert "Updated from your email: Applied: Example Labs" in page


def test_dashboard_auto_check_failure_does_not_break_page(client, monkeypatch):
    from app.dashboard import routes
    monkeypatch.setattr(routes, "_last_failed_auto_check", 0.0)
    monkeypatch.setattr(ei, "check_due", lambda db: True)

    def boom(db, **kw):
        raise OSError("offline")
    monkeypatch.setattr(ei, "run", boom)
    resp = client.get("/")
    assert resp.status_code == 200 and "check email automatically" in resp.get_data(as_text=True)
    calls = []
    monkeypatch.setattr(ei, "run", lambda db, **kw: calls.append(1) or [])
    client.get("/")
    assert calls == []  # waits before retrying after a failure


@pytest.mark.parametrize("subject,body,name,address,kind,org,role", [
    ("Your Application to Example University",
     "Thank you for your interest in employment at Example University for the position of "
     "Data Analyst II (Requisition No: 1). This notification is automated.",
     "", "noreply-1@mail.pageuppeople.com", "confirmation", "Example University", "Data Analyst II"),
    ("Thank you for your application!",
     "Thank you for your interest in the Research Analyst - REMOTE position. We will review it.",
     "", "myworkday@example.edu", "confirmation", "Example", "Research Analyst"),
    ("We received your Example Corps application",
     "Thanks, your application is in. We'll update you at each stage of the fellowship.",
     "", "no-reply@us.greenhouse-mail.io", "confirmation", "Example Corps", None),
    ("Example Fellows - Application Update",
     "Unfortunately we are not able to move forward with your candidacy.",
     "", "no-reply@ashbyhq.com", "rejection", "Example Fellows", None),
])
def test_platform_confirmations(subject, body, name, address, kind, org, role):
    assert ei.classify(subject, body) == kind
    assert ei.extract(subject, body, name, address) == (org, role)


def test_filled_role_is_a_rejection():
    body = "Thank you for your interest in joining Example as a Data Analyst. We have just filled the role."
    assert ei.classify("Data Analyst - Example", body) == "rejection"
