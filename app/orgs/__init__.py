from flask import Blueprint

# Instantiate the applications blueprint
orgs_bp = Blueprint("orgs", __name__)

# Import the applications index route
from . import routes