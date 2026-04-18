'''Test module for dashboard query shape for the job-campaign-tracker Flask app.'''
from app.database import get_db

def test_application_pipeline_shape(app, seeded_client):
    db = get_db()
    rows = db.execute(
        '''
        SELECT
            a.id,
            a.date_applied AS app_submitted,
            o.name AS org_name,
            a.role_title AS role,
            a.status
        FROM applications AS a
        LEFT JOIN orgs AS o
        ON a.org_id = o.id
        ORDER BY app_submitted DESC
        '''
    ).fetchall()
    assert len(rows) == 2
    assert rows[0]['org_name'] == 'Civic Tech Partners'