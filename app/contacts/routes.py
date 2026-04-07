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
            c.status,
            c.next_follow_up_date
        FROM contacts AS c
        LEFT JOIN orgs AS o
        ON c.org_id = o.id
        '''
    ).fetchall()
    return render_template('contacts/index.html', contacts=contacts)

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
    
@contacts_bp.route('/contacts/<int:id>')
def contact_detail(id):
    db = get_db()

    details = db.execute(
        '''
        SELECT
            c.*,
            o.name AS org_name
        FROM contacts AS c
        LEFT JOIN orgs AS o
        ON c.org_id = o.id
        WHERE c.id = ?
        ''',
        (id,)
    ).fetchone()

    history = db.execute(
        '''
        SELECT *
        FROM interactions
        WHERE contact_id = ?
        ORDER BY date DESC
        ''',
        (id,)
    ).fetchall()
    
    return render_template('contacts/detail.html', contact=details, history=history)

@contacts_bp.route('/contacts/<int:id>/interact', methods=['POST'])
def interaction_log(id):
    interaction_type = request.form['interaction_type']
    notes = request.form['notes']
    date = request.form['date']

    db = get_db()

    db.execute(
        '''
        INSERT INTO interactions (contact_id, interaction_type, notes, date) VALUES (?, ?, ?, ?)
        ''',
        (id, interaction_type, notes, date)
    )

    if interaction_type == 'Referral Received':
        new_status = 'Referred and Recommended'
    else:
        new_status = 'Response Received'

    db.execute(
        '''
        UPDATE contacts SET status = ? WHERE id = ?
        ''',
        (new_status, id)
    )
    
    db.commit()

    return redirect(url_for('contacts.contact_detail', id=id))

@contacts_bp.route('/contacts/<int:id>/edit', methods=['POST'])
def edit_contact(id):
    status = request.form['status']
    next_follow_up_date = request.form['next_follow_up_date']
    notes = request.form['notes']

    db = get_db()
    existing = db.execute(
        '''
        SELECT notes
        FROM contacts
        WHERE id = ?
        ''',
        (id,)
    ).fetchone()

    if existing['notes'] is None:
        new_notes = notes
    else:
        new_notes = existing['notes'] + notes

    db.execute(
        '''
        UPDATE contacts
        SET 
            status = ?,
            next_follow_up_date = ?,
            notes = ?
        WHERE id = ?
            ''',
            (status, next_follow_up_date, new_notes, id)
    )

    db.commit()
    return redirect(url_for('contacts.contact_detail', id=id))

