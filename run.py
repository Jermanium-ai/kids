"""
PlaySync - Main Application Entry Point
"""

import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, socketio

app, socketio = create_app()

if __name__ == '__main__':
    # Use threading for production deployment
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development',
        log_output=True
    )
