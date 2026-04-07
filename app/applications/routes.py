from flask import render_template, request, redirect, url_for
from . import applications_bp
from ..database import get_db

@applications_bp.route('/applications')
def list_applications():
    db = get_db()

    applications = db.execute(
        '''
        SELECT
            a.date_applied AS app_submitted,
            o.name AS org_name,
            a.role_title AS role,
            a.job_url AS url,
            CASE WHEN a.referral_contact_id IS NULL THEN 0 ELSE 1 END AS referral_flag,
            a.status AS status,
            a.follow_up_date AS follow_up_date,
            a.notes AS notes
        FROM applications AS a
        INNER JOIN orgs AS o
        ON a.org_id = o.id
        LEFT JOIN contacts AS c
        ON a.referral_contact_id = c.id
        '''
    ).fetchall()
    return render_template('applications/index.html', applications=applications)