'''Tests for the October 2026 relaunch changes: categories, follow-ups, weekly quota, and migration.'''
import os
import sqlite3
import subprocess
import sys
from datetime import date, timedelta

from app.database import get_db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_add_org_with_new_category_and_tier1(app, client):
    response = client.post('/orgs/add', data={
        'name': 'Zearn', 'careers_url': '', 'category': 'Education', 'tier1': '1', 'notes': ''
    })
    assert response.status_code == 302
    row = get_db().execute("SELECT category, tier1 FROM orgs WHERE name = 'Zearn'").fetchone()
    assert row['category'] == 'Education'
    assert row['tier1'] == 1


def test_unknown_category_is_stored_blank(app, client):
    client.post('/orgs/add', data={
        'name': 'Old Cluster Org', 'careers_url': '', 'category': 'Enforcement & Accountability',
        'tier1': '0', 'notes': ''
    })
    row = get_db().execute("SELECT category FROM orgs WHERE name = 'Old Cluster Org'").fetchone()
    assert row['category'] is None


def test_follow_up_keeps_status_and_schedules_next(app, seeded_client):
    db = get_db()
    db.execute("UPDATE contacts SET status = 'Contacted' WHERE id = 1")
    db.commit()
    seeded_client.post('/contacts/1/interact', data={
        'interaction_type': 'Follow-up', 'notes': '', 'date': '2026-10-07'
    })
    row = db.execute("SELECT status, next_follow_up_date FROM contacts WHERE id = 1").fetchone()
    assert row['status'] == 'Contacted'
    assert row['next_follow_up_date'] == '2026-10-14'


def test_conversation_sets_response_received(app, seeded_client):
    db = get_db()
    db.execute("UPDATE contacts SET status = 'Contacted' WHERE id = 1")
    db.commit()
    seeded_client.post('/contacts/1/interact', data={
        'interaction_type': 'Coffee Chat', 'notes': '', 'date': '2026-10-07'
    })
    assert db.execute("SELECT status FROM contacts WHERE id = 1").fetchone()['status'] == 'Response Received'


def test_dashboard_shows_overdue_follow_up(app, seeded_client):
    overdue = (date.today() - timedelta(days=3)).isoformat()
    db = get_db()
    db.execute("UPDATE contacts SET next_follow_up_date = ? WHERE id = 1", (overdue,))
    db.commit()
    html = seeded_client.get('/').get_data(as_text=True)
    assert 'Jane Smith' in html
    assert 'Overdue by 3 days' in html


def test_dashboard_hides_closed_out_contacts(app, seeded_client):
    overdue = (date.today() - timedelta(days=3)).isoformat()
    db = get_db()
    db.execute("UPDATE contacts SET next_follow_up_date = ?, status = 'Never Responded' WHERE id = 1", (overdue,))
    db.commit()
    html = seeded_client.get('/').get_data(as_text=True)
    assert 'Overdue by' not in html


def test_weekly_quota_counts_this_weeks_messages(app, seeded_client):
    today = date.today().isoformat()
    seeded_client.post('/contacts/1/interact', data={
        'interaction_type': 'Outreach Established', 'notes': '', 'date': today
    })
    seeded_client.post('/contacts/1/interact', data={
        'interaction_type': 'Follow-up', 'notes': '', 'date': today
    })
    html = seeded_client.get('/').get_data(as_text=True)
    assert 'Outreach messages' in html
    assert '<td>1</td>' in html  # one outreach, one follow-up
    assert '&#10003;' in html     # follow-up quota (1) met


def test_migration_upgrades_old_schema(tmp_path):
    db_path = tmp_path / 'old.db'
    conn = sqlite3.connect(db_path)
    conn.executescript(
        '''
        CREATE TABLE orgs (id INTEGER PRIMARY KEY, name TEXT NOT NULL, careers_url TEXT,
            category TEXT CHECK (category IN ('Civic Tech', 'Mission Aligned', 'Research & Policy', 'Enforcement & Accountability')),
            lamp_list INTEGER CHECK (lamp_list IN (0,1)), notes TEXT, created_date TEXT DEFAULT CURRENT_DATE);
        CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            org_id INTEGER REFERENCES orgs(id) ON DELETE SET NULL, platform TEXT, contact_value TEXT, capacity TEXT,
            status TEXT NOT NULL DEFAULT 'Contacted', next_follow_up_date TEXT, notes TEXT, created_date TEXT DEFAULT CURRENT_DATE);
        CREATE TABLE interactions (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            interaction_type TEXT NOT NULL CHECK (interaction_type IN ('Outreach Established', 'Informational Interview', 'Referral Received', 'Coffee Chat', 'Reconnect')),
            notes TEXT, date TEXT NOT NULL);
        INSERT INTO orgs (name, category, lamp_list) VALUES ('Code for America', 'Civic Tech', 1), ('FINRA', 'Enforcement & Accountability', 1);
        INSERT INTO contacts (name, org_id) VALUES ('Matt Gerken', 1);
        INSERT INTO interactions (contact_id, interaction_type, date) VALUES (1, 'Informational Interview', '2026-04-01');
        '''
    )
    conn.close()

    env = dict(os.environ, DATABASE_URI=str(db_path))
    result = subprocess.run([sys.executable, 'scripts/migrate_2026_10.py'], cwd=ROOT, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(db_path)
    orgs = conn.execute("SELECT name, category, tier1 FROM orgs ORDER BY id").fetchall()
    assert orgs == [('Code for America', 'Civic Tech', 0), ('FINRA', None, 0)]
    assert conn.execute("SELECT org_id FROM contacts").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0] == 1
    conn.execute("INSERT INTO interactions (contact_id, interaction_type, date) VALUES (1, 'Follow-up', '2026-10-07')")
    conn.close()
    assert any(f.startswith('old.db.backup-') for f in os.listdir(tmp_path))

    # Running it a second time is a no-op.
    again = subprocess.run([sys.executable, 'scripts/migrate_2026_10.py'], cwd=ROOT, env=env,
                           capture_output=True, text=True)
    assert 'Nothing to do' in again.stdout
