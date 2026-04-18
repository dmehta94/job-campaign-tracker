"""Organization management routes for the job-campaign-tracker Flask app."""
from flask import render_template, request, redirect, url_for, abort, flash
from . import orgs_bp
from ..database import get_db

@orgs_bp.route('/orgs')
def list_orgs():
    """Generate a list of all organizations of interest from the orgs table.
    
    Returns:
        Response: rendered template for the full list of organizations applied to or interacted with.
    """
    db = get_db()

    orgs = db.execute(
        '''
        SELECT
            id,
            name,
            careers_url,
            category
        FROM orgs
        '''
    ).fetchall()
    return render_template('/orgs/index.html', orgs = orgs)

@orgs_bp.route('/orgs/add', methods=['GET', 'POST'])
def add_org():
    """Add a new organization entry to the orgs table.
    
    Returns:
        Response: rendered template for the updated orgs table.
    """

    # Serve the entry form on GET; process and save the submission on POST
    if request.method == 'POST':
        name = request.form['name']
        careers_url = request.form['careers_url']
        category = request.form['category']
        lamp_list = request.form['lamp_list']
        notes = request.form['notes']

        # Require the user to submit a name for the organization
        if not name:
            flash('Organization name is required')
            return redirect(url_for('orgs.add_org'))
        
        db = get_db()

        db.execute(
            '''
            INSERT INTO orgs (name, careers_url, category, lamp_list, notes)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (name, careers_url, category, lamp_list, notes)
        )

        db.commit()
        return redirect(url_for('orgs.list_orgs'))
    
    else:
        return(render_template('orgs/add.html'))

@orgs_bp.route('/orgs/<int:id>')
def org_detail(id):
    """Display detail view for a selected organization.
    
    Args:
        id (int): the organization's internal identifier.
        
    Returns:
        Response: rendered template with organization details.
    """
    db = get_db()

    details = db.execute(
        '''
        SELECT *
        FROM orgs
        WHERE id = ?
        ''',
        (id,)
    ).fetchone()

    if details is None:
        abort(404)
    return render_template('orgs/detail.html', org=details)

@orgs_bp.route('/orgs/<int:id>/edit', methods=['POST'])
def edit_org(id):
    """Edit the url, category, lamp list designation, and notes for an existing organization.
    
    Args:
        id (int): the organization's internal identifier.
        
    Returns:
        Response: redirect to the organization detail page with the organization details edited.
    """

    careers_url = request.form['careers_url']
    category = request.form['category']
    lamp_list = request.form['lamp_list']
    notes = request.form['notes']

    db = get_db()
    existence = db.execute(
        "SELECT 1 FROM orgs WHERE id = ?", (id,)
    ).fetchone()

    if existence is None:
        abort(404)

    existing = db.execute(
        '''
        SELECT notes
        FROM orgs
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
        UPDATE orgs
        SET
            careers_url = ?,
            category = ?,
            lamp_list = ?,
            notes = ?
        WHERE id = ?
        ''',
        (careers_url, category, lamp_list, new_notes, id)
    )

    db.commit()

    return redirect(url_for('orgs.org_detail', id=id))