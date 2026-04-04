from flask import render_template
from . import contacts_bp
from ..database import get_db

@contacts_bp.route('/contacts')
def list_contacts():
    return "contacts list coming soon"