"""Generate sample data for the job-campaign-tracker application for demonstration purposes."""
import sys
import os

# Add project root to sys.path so the app package is importable from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import get_db

app = create_app()

with app.app_context():
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
    print("Seed data inserted successfully.")