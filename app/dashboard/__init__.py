from flask import Blueprint

# Instantiate the dashboard blueprint
dashboard_bp = Blueprint("dashboard", __name__)

# Import the dashboard index route
from . import routes