"""Database connection utilities for the job-campaign-tracker Flask app."""
from flask import g, current_app
import sqlite3

def get_db() -> sqlite3.Connection:
    """Retrieve the database connection for the current request.
    
    Creates a new connection if one does not exist on Flask's g object.
    
    Returns:
        sqlite3.Connection: An active connection to the application database.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_URI"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error):
    """Close the database connection at the end of the request context.
    
    Args:
        error: Exception passed by Flask's teardown context, or None if
            the request completed without error. Not used directly.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database schema from schema.sql."""
    db = get_db()
    with current_app.open_resource("schema.sql", mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()