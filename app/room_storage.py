"""
Persistent room storage using JSON file
Allows rooms to survive app restarts on Render free tier
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

STORAGE_FILE = os.environ.get('ROOM_STORAGE_FILE', 'rooms_data.json')

def load_rooms():
    """Load rooms from persistent storage"""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)
                # Clean up expired rooms
                current_time = datetime.now().isoformat()
                active_rooms = {}
                for room_id, room_data in data.items():
                    if room_data.get('expires_at', current_time) > current_time:
                        active_rooms[room_id] = room_data
                return active_rooms
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_rooms(rooms):
    """Save rooms to persistent storage"""
    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(rooms, f, indent=2, default=str)
    except IOError as e:
        print(f"Error saving rooms: {e}")

def add_room(room_id, room_data):
    """Add or update a room"""
    rooms = load_rooms()
    # Set expiration time (24 hours from now)
    room_data['expires_at'] = (datetime.now() + timedelta(hours=24)).isoformat()
    rooms[room_id] = room_data
    save_rooms(rooms)

def get_room(room_id):
    """Get a specific room"""
    rooms = load_rooms()
    return rooms.get(room_id)

def delete_room(room_id):
    """Delete a room"""
    rooms = load_rooms()
    if room_id in rooms:
        del rooms[room_id]
        save_rooms(rooms)

def get_all_rooms():
    """Get all active rooms"""
    return load_rooms()

def clear_expired_rooms():
    """Remove expired rooms from storage"""
    rooms = load_rooms()
    current_time = datetime.now().isoformat()
    active_rooms = {
        room_id: room_data 
        for room_id, room_data in rooms.items()
        if room_data.get('expires_at', current_time) > current_time
    }
    save_rooms(active_rooms)
    return len(active_rooms)
