"""Populate the dashboard with summary metrics and activity tables."""
from flask import render_template
from . import dashboard_bp
from ..database import get_db

@dashboard_bp.route('/')
def index():
    """Render the dashboard with summary metrics and activity tables.
    
    Returns:
        Response: rendered dashboard template with prepopulated summary metrics and activity tables.
    """
    db = get_db()
    
    num_apps = db.execute(
        "SELECT COUNT(*) FROM applications"
    ).fetchone()[0]

    progress = db.execute(
        "SELECT COUNT(*) FROM applications WHERE status IN ('Recruiter Screened', 'Technical Screened', 'Interviewed', 'Offered', 'Accepted', 'Rejected Offer')"
    ).fetchone()[0]

    referred = db.execute(
        "SELECT COUNT(*) FROM interactions WHERE interaction_type = 'Referral Received'"
    ).fetchone()[0]

    # follow_up_data performs calendar arithmetic to compute the number of days between now and the next follow-up
    follow_ups = db.execute(
        '''
        WITH follow_up_data AS (
            SELECT
                c.id,
                c.name,
                o.name AS org_name,
                c.next_follow_up_date,
                -- julianday() converts dates to a float to enable date arithmetic
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

    apps_pipeline = db.execute(
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

    # interactions_by_org ranks organizations by the number of interactions the user has had with contacts there.
    org_rankings = db.execute(
        '''
        WITH interactions_by_org AS (
            SELECT
                o.name AS org_name,
                COUNT(i.id) AS number_of_interactions
            FROM interactions AS i
            LEFT JOIN contacts AS c
                ON i.contact_id = c.id
            LEFT JOIN orgs AS o
                ON c.org_id = o.id
            GROUP BY o.id
            )
        SELECT
            org_name,
            number_of_interactions,
            -- rank by the number of interactions had with contacts at each org in descending order
            RANK() OVER (
                ORDER BY number_of_interactions DESC
                ) AS rank
        FROM interactions_by_org
        '''
        ).fetchall()
    
    return render_template(
        'dashboard/index.html',
        num_apps = num_apps,
        progress = progress,
        referred = referred,
        follow_ups = follow_ups,
        active_conversations = active_conversations,
        apps_pipeline = apps_pipeline,
        org_rankings = org_rankings
        )