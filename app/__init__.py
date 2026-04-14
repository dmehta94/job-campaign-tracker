# Imports
from flask import Flask, render_template
from config import config
from .dashboard import dashboard_bp
from .contacts import contacts_bp
from .applications import applications_bp
from .orgs import orgs_bp
from .database import close_db

# Define create_app function
# Add Google-style docstring later
def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['CONFIG_NAME'] = config_name
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(orgs_bp)
    app.teardown_appcontext(close_db)
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    return app