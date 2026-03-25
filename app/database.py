from flask import g, current_app
import sqlite3

# Store a database connection on g and set row_factory to Row
# Add Google-style docstring in post
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_URI"])
        g.db.row_factory = sqlite3.Row
    return g.db

# Close a database connection
# Add Google-style docstring in post
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Open the schema, read it, and execute it against the db
# Add Google-style docstring in post
def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql", mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()