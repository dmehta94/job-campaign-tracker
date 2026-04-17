"""Configuration testing module for the job-campaign-tracker Flask app."""
import pytest
import sys
import os

# Set project root at pos(0) in sys.path to ensure relative imports resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import init_db, get_db

@pytest.fixture
def app():
    """Create and configure a Flask app instance for testing.
    
    Initializes a fresh test database from schema, yields the app with an
    active application context, then removes the test database on teardown.
    """
    app = create_app("testing")
    with app.app_context():
        init_db()
        yield app
    os.remove(app.config['DATABASE_URI'])

@pytest.fixture
def client(app):
    """Provide a test client for making HTTP requests against the app."""
    with app.test_client() as client:
        yield client

@pytest.fixture
def seeded_client(app, client):
    """Provide a test client with known seed data pre-loaded.
    
    Inserts one org, one contact, one interaction, and two applications
    so that detail routes have records to resolve against.
    Yields the same test client as the client fixture.
    """
    db = get_db()
 
    # Org
    db.execute(
        "INSERT INTO orgs (name, category) VALUES (?, ?)", ("Civic Tech Partners", "Civic Tech")
    )

    # Contact
    db.execute(
        "INSERT INTO contacts (name, org_id, status) VALUES (?, ?, ?)", ("Jane Smith", 1, "Response Received")
    )

    # Interaction - referral
    db.execute(
        "INSERT INTO interactions (contact_id, interaction_type, date) VALUES (?, ?, ?)", (1, "Referral Received", "2026-03-01")
    )
    
    # Application - with progress
    db.execute(
        "INSERT INTO applications (org_id, role_title, date_applied, status) VALUES (?, ?, ?, ?)",
        (1, "Data Analyst", "2026-03-10", "Applied")
    )

    # Application — with progress
    db.execute(
        "INSERT INTO applications (org_id, role_title, date_applied, status) VALUES (?, ?, ?, ?)",
        (1, "Data Scientist", "2026-03-15", "Recruiter Screened")
    )

    db.commit()
    yield client