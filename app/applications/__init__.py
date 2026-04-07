from flask import Blueprint

# Instantiate the applications blueprint
applications_bp = Blueprint("applications", __name__)

# Import the applications index route
from . import routes