"""Execution file for the job-campaign-tracker Flask app."""
import sys
import os

# Set project root at pos 0 in sys.path to ensure relative imports resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app


app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])