# Imports
from flask import Flask
from config import config
from .database import close_db

# Define create_app function
# Add Google-style docstring later
def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['CONFIG_NAME'] = config_name

    app.teardown_appcontext(close_db)
    return app