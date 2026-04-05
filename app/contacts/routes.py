from flask import render_template, request, redirect, url_for
from . import contacts_bp
from ..database import get_db

@contacts_bp.route('/contacts')
def list_contacts():
    db = get_db()

    contacts = db.execute(
        '''
        SELECT
            c.name AS name,
            o.name AS org_name,
            status,
            next_follow_up_date
        FROM contacts AS c
        LEFT JOIN orgs AS o
        ON c.org_id = o.id
        '''
    ).fetchall()
    return render_template('contacts/index.html', contacts = contacts)

@contacts_bp.route('/contacts/add', methods=['GET', 'POST'])
def add_contact():
    if request.method == 'POST':
        name = request.form['name']
        org_name = request.form['org_name']
        platform = request.form['platform']
        contact_value = request.form['contact_value']
        capacity = request.form['capacity']
        next_follow_up_date = request.form['next_follow_up_date']
        notes = request.form['notes']

        db = get_db()

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
            INSERT INTO contacts (name, org_id, platform, contact_value, capacity, next_follow_up_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (name, org_id, platform, contact_value, capacity, next_follow_up_date, notes)
        )
        db.commit()
        return redirect(url_for('contacts.list_contacts'))
    else:
        return render_template('contacts/add.html')