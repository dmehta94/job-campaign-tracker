"""Populate the dashboard with summary metrics and activity tables."""
import time

from flask import render_template, redirect, url_for, flash
from . import dashboard_bp
from ..database import get_db
from .. import email_import
from ..stale import close_unanswered

# After a failed automatic check (offline, wrong password), wait this long before trying again,
# so the dashboard doesn't stall on every page load.
RETRY_AFTER_FAILURE_SECONDS = 60 * 60
_last_failed_auto_check = 0.0


def _auto_check_email(db) -> None:
    """Check email when the dashboard opens, if the last successful check is more than 12 hours old."""
    global _last_failed_auto_check
    if time.time() - _last_failed_auto_check < RETRY_AFTER_FAILURE_SECONDS:
        return
    if not email_import.check_due(db):
        return
    try:
        changes = email_import.run(db)
    except Exception as exc:  # network or login problems: note it and carry on with the dashboard
        _last_failed_auto_check = time.time()
        flash(f"Couldn't check email automatically ({type(exc).__name__}). "
              "It will try again later, or use the Check email button.")
        return
    if changes:
        flash("Updated from your email: " + "; ".join(changes))

# Weekly quota: a small fixed number of outgoing messages instead of application volume.
WEEKLY_QUOTA = {'Outreach Established': 2, 'Follow-up': 1}

@dashboard_bp.route('/')
def index():
    """Render the dashboard with summary metrics and activity tables.
    
    Returns:
        Response: rendered dashboard template with prepopulated summary metrics and activity tables.
    """
    db = get_db()
    _auto_check_email(db)
    closed = close_unanswered(db)
    if closed:
        flash("Closed with no reply after three months: " + "; ".join(closed))

    num_apps = db.execute(
        "SELECT COUNT(*) FROM applications"
    ).fetchone()[0]

    progress = db.execute(
        "SELECT COUNT(*) FROM applications WHERE status IN ('Recruiter Screened', 'Technical Screened', 'Interviewed', 'Offered', 'Accepted', 'Rejected Offer')"
    ).fetchone()[0]

    referred = db.execute(
        "SELECT COUNT(*) FROM interactions WHERE interaction_type = 'Referral Received'"
    ).fetchone()[0]

    # Monday-to-Sunday count of outgoing messages, compared against the weekly quota.
    # date('now', 'localtime', 'weekday 0', '-6 days') is the Monday of the current week.
    week_counts = dict(db.execute(
        '''
        SELECT interaction_type, COUNT(*) AS n
        FROM interactions
        WHERE date >= date('now', 'localtime', 'weekday 0', '-6 days')
            AND date <= date('now', 'localtime')
            AND interaction_type IN ('Outreach Established', 'Follow-up')
        GROUP BY interaction_type
        '''
    ).fetchall())
    quota = [
        {'label': label, 'done': week_counts.get(itype, 0), 'goal': goal}
        for itype, goal, label in [
            ('Outreach Established', WEEKLY_QUOTA['Outreach Established'], 'Outreach messages'),
            ('Follow-up', WEEKLY_QUOTA['Follow-up'], 'Follow-ups'),
        ]
    ]

    # follow_up_data performs calendar arithmetic to compute the number of days between today and the next follow-up.
    # Overdue follow-ups (negative days) stay on the list until handled; closed-out contacts are excluded.
    follow_ups = db.execute(
        '''
        WITH follow_up_data AS (
            SELECT
                c.id,
                c.name,
                o.name AS org_name,
                c.next_follow_up_date,
                -- julianday() converts dates to a float to enable date arithmetic
                julianday(c.next_follow_up_date) - julianday(date('now', 'localtime')) AS days_until_followup
            FROM contacts AS c
            LEFT JOIN orgs AS o
            ON c.org_id = o.id
            WHERE c.next_follow_up_date IS NOT NULL
                AND c.next_follow_up_date != ''
                AND c.status NOT IN ('Declined', 'Never Responded')
            )
        SELECT *
        FROM follow_up_data
        WHERE days_until_followup <= 7
        ORDER BY days_until_followup;
        '''
    ).fetchall()

    # Applications still waiting on a reply whose check-in date is near or past.
    app_follow_ups = db.execute(
        '''
        SELECT
            a.id,
            o.name AS org_name,
            a.role_title AS role,
            a.date_applied,
            a.follow_up_date,
            julianday(a.follow_up_date) - julianday(date('now', 'localtime')) AS days_until_followup
        FROM applications AS a
        LEFT JOIN orgs AS o
        ON a.org_id = o.id
        WHERE a.follow_up_date IS NOT NULL
            AND a.follow_up_date != ''
            AND a.status IN ('Applied', 'ATS Screened')
            AND julianday(a.follow_up_date) - julianday(date('now', 'localtime')) <= 7
        ORDER BY days_until_followup
        '''
    ).fetchall()

    apps_this_week = db.execute(
        "SELECT COUNT(*) FROM applications WHERE date_applied >= date('now', 'localtime', 'weekday 0', '-6 days') "
        "AND status != 'Rejected by Org'"
    ).fetchone()[0]

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
        quota = quota,
        num_apps = num_apps,
        progress = progress,
        referred = referred,
        follow_ups = follow_ups,
        app_follow_ups = app_follow_ups,
        apps_this_week = apps_this_week,
        active_conversations = active_conversations,
        apps_pipeline = apps_pipeline,
        org_rankings = org_rankings
        )


@dashboard_bp.route('/check-email', methods=['POST'])
def check_email():
    """Log applications and rejections from recent email (at least two weeks), then return to the dashboard."""
    try:
        changes = email_import.run(get_db())
    except RuntimeError as exc:
        flash(str(exc))
    except Exception as exc:  # network or login problems: say so instead of showing an error page
        flash(f"Couldn't check email ({type(exc).__name__}). Check your internet connection and app password.")
    else:
        if changes:
            flash("Updated from your email: " + "; ".join(changes))
        else:
            flash("Checked email: nothing new.")
    return redirect(url_for('dashboard.index'))
