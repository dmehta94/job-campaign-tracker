from flask import render_template, request, redirect, url_for
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