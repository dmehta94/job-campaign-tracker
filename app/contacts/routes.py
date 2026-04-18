"""Contact management routes for the job-campaign-tracker Flask app."""
from flask import render_template, request, redirect, url_for, flash, abort
from . import contacts_bp
from ..database import get_db

@contacts_bp.route('/contacts')
def list_contacts():
    """Generate a list of all contacts from the contacts table.
    
    Returns:
        Response: rendered template for the full list of contacts with associated organization names.
    """
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
    """Add a new contact entry with associated organization name to the contacts table.

    If the organization does not exist, create a new stub entry for it in the orgs table.
    
    Returns:
        Response: rendered template for the updated contacts table with associated organizations.
    """
    db = get_db()

    # Serve the empty form on GET; process and save the submission on POST
    if request.method == 'POST':
        name = request.form['name']
        org_name = request.form['org_name']
        platform = request.form['platform']
        contact_value = request.form['contact_value']
        capacity = request.form['capacity']
        next_follow_up_date = request.form['next_follow_up_date']
        notes = request.form['notes']

        if org_name == "other":
            org_name = request.form['other_org_name']

        org = db.execute(
            "SELECT id FROM orgs WHERE name = ?", (org_name,)
            ).fetchone()

        # Create a new org stub in the orgs table if an entry for the org does not exist
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

        flash('New contact added successfully!')
        return redirect(url_for('contacts.list_contacts'))
    else:
        org_info = db.execute('SELECT id, name FROM orgs').fetchall()
        return render_template('contacts/add.html', org_info = org_info)
    
@contacts_bp.route('/contacts/<int:id>')
def contact_detail(id):
    """Display detail view for a selected contact with associated organization and all interactions.
    
    Args:
        id (int): the contact's internal identifier.
        
    Returns:
        Response: rendered template with contact details and interaction history.
    """
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
    
    if details is None:
        abort(404)
    return render_template('contacts/detail.html', contact=details, history=history)

@contacts_bp.route('/contacts/<int:id>/interact', methods=['POST'])
def interaction_log(id):
    """Log a new interaction with a selected contact and update the contact status.
    
    Args:
        id (int): the contact's internal identifier.
        
    Returns:
        Response: redirect to the contact detail page
    """
    interaction_type = request.form['interaction_type']
    notes = request.form['notes']
    date = request.form['date']

    db = get_db()

    existence = db.execute(
        "SELECT 1 FROM contacts WHERE id = ?", (id,)
    ).fetchone()

    if existence is None:
        abort(404)
    
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
    """Edit the status, follow-up date, and notes for an existing contact.
    
    Args:
        id (int): the contact's internal identifier.
        
    Returns:
        Response: redirect to the contact detail page with the contact details edited.
    """
    status = request.form['status']
    next_follow_up_date = request.form['next_follow_up_date']
    notes = request.form['notes']

    db = get_db()
    existence = db.execute(
        "SELECT 1 FROM contacts WHERE id = ?", (id,)
    ).fetchone()

    if existence is None:
        abort(404)

    existing = db.execute(
        '''
        SELECT notes
        FROM contacts
        WHERE id = ?
        ''',
        (id,)
    ).fetchone()

    # Append new notes to the entry, rather than replacing the existing ones
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

