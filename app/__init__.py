"""Application factory for the job-campaign-tracker Flask app."""
from flask import Flask, render_template
from config import config
from .dashboard import dashboard_bp
from .contacts import contacts_bp
from .applications import applications_bp
from .orgs import orgs_bp
from .database import close_db

def create_app(config_name='development') -> Flask:
    """Creates the flask app and registers all blueprints.
    
    Args:
        config_name (str): Configuration mode for the app (development, testing, production)
        
    Returns:
        Flask: App loaded with all blueprints and error handlers
    """
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