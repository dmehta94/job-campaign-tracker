from flask import Blueprint

# Instantiate the contacts blueprint
contacts_bp = Blueprint("contacts", __name__)

# Import the contacts index route
from . import routes