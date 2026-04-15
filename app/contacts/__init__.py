"""Instantiates contacts blueprint for the job-campaign-tracker application."""
from flask import Blueprint

contacts_bp = Blueprint("contacts", __name__)

from . import routes