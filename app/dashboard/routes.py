from flask import render_template
from . import dashboard_bp
from ..database import get_db

@dashboard_bp.route('/')
def index():
    db = get_db()
    
    num_apps = db.execute(
        "SELECT COUNT(*) FROM applications"
    ).fetchone()[0]
    print(f'Applications Submitted: {num_apps}')

    progress = db.execute(
        "SELECT COUNT(*) FROM applications WHERE status IN ('Recruiter Screened', 'Technical Screened', 'Interviewed', 'Offered', 'Accepted', 'Rejected Offer')"
    ).fetchone()[0]
    print(f'Applications Progressed to Interview: {progress}')

    referred = db.execute(
        "SELECT COUNT(*) FROM interactions WHERE interaction_type = 'Referral Received'"
    ).fetchone()[0]
    print(f'Referrals Received: {referred}')

    follow_ups = db.execute(
        '''
        WITH follow_up_data AS (
            SELECT
                c.id,
                c.name,
                o.name AS org_name,
                c.next_follow_up_date,
                julianday(next_follow_up_date) - julianday('now') AS days_until_followup
            FROM contacts AS c
            LEFT JOIN orgs AS o
            ON c.org_id = o.id
            )
        SELECT *
        FROM follow_up_data
        WHERE (days_until_followup >= 0) AND (days_until_followup <= 7);
        '''
    ).fetchall()

    active_conversations = db.execute(
        '''
        SELECT 
            c.id,
            c.name,
            o.name AS org_name,
            c.status
        FROM contacts AS c
        LEFT JOIN orgs AS o
        ON c.org_id = o.id
        WHERE c.status IN ("Response Received", "Referred and Recommended")
        '''
    ).fetchall()

    return render_template('dashboard/index.html', num_apps = num_apps, progress = progress, referred = referred, follow_ups = follow_ups)