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
    return render_template('/applications/index.html', applications=applications)

@applications_bp.route('/applications/add', methods=['GET', 'POST'])
def add_application():
    db = get_db()
    if request.method == 'POST':
        date_applied = request.form['app_submitted']
        org_name = request.form['org_name']
        role_title = request.form['role']
        job_url = request.form['url']
        referral_contact_id = request.form['referral_contact_id']
        referral_contact_id = None if referral_contact_id == "" else referral_contact_id
        status = request.form['status']
        follow_up_date = request.form['follow_up_date']
        notes = request.form['notes']
    
        org = db.execute(
            "SELECT id FROM orgs WHERE name = ?", (org_name,)
        ).fetchone()

        if org is None:
            org_id = db.execute(
                "INSERT INTO orgs (name) VALUES (?)", (org_name,)
            ).lastrowid
        else:
            org_id = org['id']

        db.execute(
            '''
            INSERT INTO applications (date_applied, org_id, role_title, job_url, referral_contact_id, status, follow_up_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (date_applied, org_id, role_title, job_url, referral_contact_id, status, follow_up_date, notes)
        )

        db.commit()
        return redirect(url_for('applications.list_applications'))

    else:
        ref_info = db.execute(
            '''
            SELECT id, name
            FROM contacts
            WHERE status = ?
            ''',
            ("Referred and Recommended",)
        ).fetchall()
        return render_template('applications/add.html', ref_info = ref_info)
    
@applications_bp.route('/applications/<int:id>')
def application_detail(id):
    db = get_db()

    details = db.execute(
        '''
        SELECT
            a.id AS id,
            a.date_applied AS app_submitted,
            o.name AS org_name,
            a.role_title AS role,
            a.job_url AS url,
            c.name as contact_name,
            a.status AS status,
            a.follow_up_date AS follow_up_date,
            a.notes AS notes
        FROM applications AS a
        INNER JOIN orgs AS o
        ON a.org_id = o.id
        LEFT JOIN contacts AS c
        ON a.referral_contact_id = c.id
        WHERE a.id = ?
        ''',
        (id,)
    ).fetchone()
    return render_template('applications/detail.html', application=details)