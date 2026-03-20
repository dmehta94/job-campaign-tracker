import sys
import os

# Set the project root at position 0 in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app


app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])