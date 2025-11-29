"""
PlaySync - Real-time multiplayer game rooms
Room Manager: Persistent room storage and player lifecycle management
Uses file-based storage to survive app restarts on Render free tier
"""

import uuid
import random
import string
import time
from datetime import datetime, timedelta
from enum import Enum
from app import room_storage

class GameType(Enum):
    ROCK_PAPER_SCISSORS = "rps"
    TIC_TAC_TOE = "tictactoe"
    REACTION_TIME = "reaction"
    QUICK_MATH = "quickmath"
    WOULD_YOU_RATHER = "would_you_rather"

class PlayerSlot:
    """Represents a player in a room"""
    def __init__(self, player_id, display_name, avatar_color):
        self.player_id = player_id
        self.display_name = display_name
        self.avatar_color = avatar_color
        self.socket_id = None
        self.score = 0
        self.is_ready = False
        self.is_active = True
        self.joined_at = datetime.now()

class GameState:
    """Manages state for the current game"""
    def __init__(self, game_type):
        self.game_type = game_type
        self.started_at = datetime.now()
        self.player_scores = {}
        self.round_data = {}
        self.results = None
        self.state_data = {}  # Game-specific data

class Room:
    """Represents an ephemeral game room"""
    def __init__(self, room_id, max_players=2, inactivity_timeout_seconds=1200):
        self.room_id = room_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.max_players = max_players
        self.inactivity_timeout = inactivity_timeout_seconds
        
        self.players = {}  # {player_id: PlayerSlot}
        self.player_order = []  # Track join order
        self.current_game = None  # GameState or None
        self.game_history = []  # Log of past games
        self.cumulative_scores = {}  # Track scores between games
        
    def is_full(self):
        """Check if room has reached max players"""
        return len(self.players) >= self.max_players
    
    def is_empty(self):
        """Check if no players in room"""
        return len(self.players) == 0
    
    def is_expired(self):
        """Check if room has exceeded inactivity timeout"""
        return (datetime.now() - self.last_activity).total_seconds() > self.inactivity_timeout
    
    def add_player(self, player_id, display_name, avatar_color):
        """Add a player to the room"""
        if self.is_full():
            return False
        
        player = PlayerSlot(player_id, display_name, avatar_color)
        self.players[player_id] = player
        self.player_order.append(player_id)
        self.last_activity = datetime.now()
        return True
    
    def remove_player(self, player_id):
        """Remove a player from the room"""
        if player_id in self.players:
            del self.players[player_id]
            if player_id in self.player_order:
                self.player_order.remove(player_id)
            self.last_activity = datetime.now()
            return True
        return False
    
    def get_player_count(self):
        """Return number of active players"""
        return len(self.players)
    
    def get_players_list(self):
        """Return serializable list of players"""
        return [
            {
                'player_id': p.player_id,
                'display_name': p.display_name,
                'avatar_color': p.avatar_color,
                'score': p.score,
                'is_ready': p.is_ready,
                'is_active': p.is_active,
            }
            for p in [self.players[pid] for pid in self.player_order]
        ]
    
    def start_game(self, game_type, reset_scores=False):
        """Initialize a new game session"""
        self.current_game = GameState(game_type)
        
        # Initialize scores - reset if requested, otherwise use cumulative scores
        if reset_scores:
            for player_id in self.players:
                self.current_game.player_scores[player_id] = 0
        else:
            # PRESERVE cumulative scores from previous games
            old_scores = self.cumulative_scores.copy() if self.cumulative_scores else {}
            for player_id in self.players:
                self.current_game.player_scores[player_id] = old_scores.get(player_id, 0)
        
        # Reset ready states
        for player in self.players.values():
            player.is_ready = False
        self.last_activity = datetime.now()
    
    def end_game(self, results):
        """End current game, update scores, and log results"""
        if self.current_game and results:
            # Update scores based on result
            if results.get('winner'):
                # Player won
                winner_id = results['winner']
                if winner_id in self.current_game.player_scores:
                    self.current_game.player_scores[winner_id] += 1
            elif results.get('result') == 'draw':
                # Draw - award 1 point to each player
                for player_id in self.current_game.player_scores:
                    self.current_game.player_scores[player_id] += 1
            
            # CRITICAL: Save cumulative scores before clearing current_game
            # This allows us to preserve scores and send them to the frontend
            self.cumulative_scores = dict(self.current_game.player_scores)
            
            self.current_game.results = results
            self.game_history.append(self.current_game)
            # NOTE: Keep current_game set until after game_ended is emitted (handled in socketio_events)
        self.last_activity = datetime.now()


class RoomManager:
    """Manages all active rooms"""
    def __init__(self):
        self.rooms = {}  # {room_id: Room}
        self.player_to_room = {}  # {player_id: room_id} for quick lookup
        self.cleanup_interval = 60  # Run cleanup every 60 seconds
        self.last_cleanup = datetime.now()
    
    def generate_room_id(self, length=8):
        """Generate a secure, human-friendly room ID"""
        chars = string.ascii_uppercase + string.digits
        # Exclude confusing chars like 0/O, 1/I/L
        chars = chars.replace('0', '').replace('1', '').replace('I', '').replace('O', '')
        return ''.join(random.choice(chars) for _ in range(length))
    
    def create_room(self, inactivity_timeout_seconds=1200):
        """Create a new room and persist it"""
        room_id = self.generate_room_id()
        while room_id in self.rooms:  # Ensure uniqueness
            room_id = self.generate_room_id()
        
        room = Room(room_id, inactivity_timeout_seconds=inactivity_timeout_seconds)
        self.rooms[room_id] = room
        
        # Persist to storage
        room_storage.add_room(room_id, {
            'room_id': room_id,
            'created_at': room.created_at.isoformat(),
            'max_players': room.max_players,
            'players': {},
            'status': 'active'
        })
        
        return room_id
    
    def get_room(self, room_id):
        """Retrieve a room by ID, loading from storage if needed"""
        # Check in-memory first
        if room_id in self.rooms:
            return self.rooms[room_id]
        
        # Check persistent storage
        room_data = room_storage.get_room(room_id)
        if room_data:
            # Restore room from storage
            room = Room(room_id, inactivity_timeout_seconds=1200)
            self.rooms[room_id] = room
            return room
        
        return None
    
    def join_room(self, room_id, player_id, display_name, avatar_color):
        """Add a player to a room"""
        room = self.get_room(room_id)
        if not room:
            return {'success': False, 'error': 'Room not found'}
        
        if room.is_full():
            return {'success': False, 'error': 'Room is full'}
        
        if player_id in room.players:
            return {'success': False, 'error': 'Player already in room'}
        
        if room.add_player(player_id, display_name, avatar_color):
            self.player_to_room[player_id] = room_id
            return {'success': True, 'room': self._serialize_room(room)}
        
        return {'success': False, 'error': 'Could not add player'}
    
    def leave_room(self, room_id, player_id):
        """Remove a player from a room"""
        room = self.get_room(room_id)
        if not room:
            return False
        
        room.remove_player(player_id)
        if player_id in self.player_to_room:
            del self.player_to_room[player_id]
        
        # Clean up empty rooms
        if room.is_empty():
            del self.rooms[room_id]
            # Also remove from persistent storage
            room_storage.delete_room(room_id)
        
        return True
    
    def _serialize_room(self, room):
        """Convert room to JSON-serializable dict"""
        game_state = None
        if room.current_game:
            game_state = {
                'game_type': room.current_game.game_type.value,
                'started_at': room.current_game.started_at.isoformat(),
                'player_scores': room.current_game.player_scores,
                'state_data': room.current_game.state_data,
            }
        
        return {
            'room_id': room.room_id,
            'created_at': room.created_at.isoformat(),
            'player_count': room.get_player_count(),
            'max_players': room.max_players,
            'players': room.get_players_list(),
            'current_game': game_state,
            'game_history': [
                {
                    'game_type': g.game_type.value,
                    'results': g.results,
                    'started_at': g.started_at.isoformat(),
                }
                for g in room.game_history
            ]
        }
    
    def cleanup_expired_rooms(self):
        """Remove expired rooms (no activity for timeout period)"""
        now = datetime.now()
        expired = [rid for rid, room in self.rooms.items() if room.is_expired()]
        
        for room_id in expired:
            # Remove players from tracking
            room = self.rooms[room_id]
            for player_id in list(room.players.keys()):
                if player_id in self.player_to_room:
                    del self.player_to_room[player_id]
            # Remove room
            del self.rooms[room_id]
        
        self.last_cleanup = now
        return len(expired)
    
    def maybe_cleanup(self):
        """Optionally run cleanup if interval has passed"""
        if (datetime.now() - self.last_cleanup).total_seconds() > self.cleanup_interval:
            self.cleanup_expired_rooms()
    
    def get_room_info(self, room_id):
        """Get serialized room info (safe to send to client)"""
        room = self.get_room(room_id)
        if not room:
            return None
        return self._serialize_room(room)

# Global instance
room_manager = RoomManager()
