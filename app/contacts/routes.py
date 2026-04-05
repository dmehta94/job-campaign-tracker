from flask import render_template
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