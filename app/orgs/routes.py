from flask import render_template, request, redirect, url_for, abort
from . import orgs_bp
from ..database import get_db

@orgs_bp.route('/orgs')
def list_orgs():
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

@orgs_bp.route('/orgs/<int:id>')
def org_detail(id):
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