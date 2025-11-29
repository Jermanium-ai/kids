"""
PlaySync Flask Application Factory
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

socketio = None

def create_app(config=None):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'playsync-secret-key-change-in-production'
    if config:
        app.config.update(config)
    
    # Enable CORS
    CORS(app)
    
    # Initialize Socket.IO
    global socketio
    # Use threading async mode for compatibility across all platforms
    # Threading is reliable and works with standard gunicorn sync worker
    async_mode = 'threading'
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        ping_timeout=60,
        ping_interval=25,
        async_mode=async_mode,
        # Explicitly allow all transports for better remote connectivity
        engineio_logger=False,
        # Enable both WebSocket and polling fallbacks
        transports=['websocket', 'polling'],
    )
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register Socket.IO events
    from app import socketio_events
    
    # Load persisted rooms from storage on startup
    from app import room_storage
    from app.room_manager import room_manager
    
    active_rooms = room_storage.get_all_rooms()
    for room_id in active_rooms:
        # Restore room to in-memory storage
        room_manager.get_room(room_id)
    
    if active_rooms:
        app.logger.info(f"Loaded {len(active_rooms)} persisted rooms from storage")
    
    return app, socketio
