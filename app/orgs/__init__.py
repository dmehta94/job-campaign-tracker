"""Instantiates orgs blueprint for the job-campaign-tracker application."""
from flask import Blueprint

orgs_bp = Blueprint("orgs", __name__)

from . import routes