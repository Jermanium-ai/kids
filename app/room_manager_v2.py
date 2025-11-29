"""
PlaySync - Room Manager (Enhanced with thread-safety and error handling)
Real-time multiplayer game room management with persistent storage

Key improvements:
- Thread-safe operations using Python locks
- Comprehensive error handling
- Auto-expire cleanup with configurable timeouts
- Race condition prevention for concurrent socket events
"""

import uuid
import random
import string
import time
import threading
import logging
from datetime import datetime, timedelta
from enum import Enum
from app import room_storage

# Configure logging
logger = logging.getLogger(__name__)

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
    """Represents an ephemeral game room with thread-safety"""
    def __init__(self, room_id, max_players=2, inactivity_timeout_seconds=1200):
        self.room_id = room_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.max_players = max_players
        self.inactivity_timeout = inactivity_timeout_seconds
        
        self.players = {}  # {player_id: PlayerSlot}
        self.player_order = []  # Track join order
        self.cumulative_scores = {}
        self.current_game = None
        self.game_history = []
        
        # Thread lock for safe concurrent access
        self._lock = threading.Lock()
    
    def add_player(self, player_id, display_name, avatar_color):
        """Add player to room (thread-safe)"""
        with self._lock:
            if player_id in self.players:
                raise ValueError(f"Player {player_id} already in room")
            
            if len(self.players) >= self.max_players:
                raise ValueError("Room is full")
            
            player = PlayerSlot(player_id, display_name, avatar_color)
            self.players[player_id] = player
            self.player_order.append(player_id)
            self.last_activity = datetime.now()
            
            logger.debug(f"Player added to room {self.room_id}: {player_id}")
            return player
    
    def remove_player(self, player_id):
        """Remove player from room (thread-safe)"""
        with self._lock:
            if player_id in self.players:
                del self.players[player_id]
                if player_id in self.player_order:
                    self.player_order.remove(player_id)
                self.last_activity = datetime.now()
                logger.debug(f"Player removed from room {self.room_id}: {player_id}")
    
    def get_player_count(self):
        """Get current player count"""
        with self._lock:
            return len(self.players)
    
    def is_empty(self):
        """Check if room has no players"""
        with self._lock:
            return len(self.players) == 0
    
    def is_full(self):
        """Check if room is at max capacity"""
        with self._lock:
            return len(self.players) >= self.max_players
    
    def is_expired(self):
        """Check if room has timed out"""
        timeout_seconds = self.inactivity_timeout
        elapsed = (datetime.now() - self.last_activity).total_seconds()
        return elapsed > timeout_seconds
    
    def get_players_list(self):
        """Get list of players in order (thread-safe)"""
        with self._lock:
            return [
                {
                    'player_id': p.player_id,
                    'display_name': p.display_name,
                    'avatar_color': p.avatar_color,
                    'score': p.score,
                    'is_ready': p.is_ready,
                    'is_active': p.is_active,
                }
                for p in [self.players[pid] for pid in self.player_order if pid in self.players]
            ]
    
    def start_game(self, game_type, reset_scores=False):
        """Initialize a new game session (thread-safe)"""
        with self._lock:
            self.current_game = GameState(game_type)
            
            # Initialize scores
            if reset_scores:
                for player_id in self.players:
                    self.current_game.player_scores[player_id] = 0
            else:
                old_scores = self.cumulative_scores.copy() if self.cumulative_scores else {}
                for player_id in self.players:
                    self.current_game.player_scores[player_id] = old_scores.get(player_id, 0)
            
            # Reset ready states
            for player in self.players.values():
                player.is_ready = False
            
            self.last_activity = datetime.now()
            logger.debug(f"Game started in room {self.room_id}: {game_type}")
    
    def end_game(self, results):
        """End current game and update scores (thread-safe)"""
        with self._lock:
            if self.current_game and results:
                # Update cumulative scores
                if results.get('winner'):
                    winner_id = results['winner']
                    if winner_id in self.current_game.player_scores:
                        self.current_game.player_scores[winner_id] += 1
                elif results.get('result') == 'draw':
                    for player_id in self.current_game.player_scores:
                        self.current_game.player_scores[player_id] += 1
                
                self.cumulative_scores = dict(self.current_game.player_scores)
                self.current_game.results = results
                self.game_history.append(self.current_game)
            
            self.last_activity = datetime.now()
            logger.debug(f"Game ended in room {self.room_id}")

class RoomManager:
    """Manages all rooms with thread-safety"""
    def __init__(self, cleanup_interval=60):
        self.rooms = {}  # {room_id: Room}
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = datetime.now()
        
        # Global lock for room creation/deletion
        self._lock = threading.Lock()
    
    def generate_room_id(self, length=8):
        """Generate a unique room ID"""
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('0', '').replace('1', '').replace('I', '').replace('O', '')
        return ''.join(random.choice(chars) for _ in range(length))
    
    def create_room(self, inactivity_timeout_seconds=1200):
        """Create a new room (thread-safe)"""
        try:
            with self._lock:
                room_id = self.generate_room_id()
                while room_id in self.rooms:
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
                
                logger.info(f"Room created: {room_id}")
                return room_id
        except Exception as e:
            logger.error(f"Error creating room: {e}", exc_info=True)
            raise
    
    def get_room(self, room_id):
        """Retrieve a room by ID (thread-safe)"""
        try:
            with self._lock:
                # Check in-memory first
                if room_id in self.rooms:
                    return self.rooms[room_id]
                
                # Check persistent storage
                room_data = room_storage.get_room(room_id)
                if room_data:
                    room = Room(room_id, inactivity_timeout_seconds=1200)
                    self.rooms[room_id] = room
                    logger.debug(f"Room restored from storage: {room_id}")
                    return room
                
                return None
        except Exception as e:
            logger.error(f"Error getting room {room_id}: {e}", exc_info=True)
            return None
    
    def join_room(self, room_id, player_id, display_name, avatar_color):
        """Add a player to a room (thread-safe, atomic)"""
        try:
            with self._lock:
                room = self.get_room(room_id)
                if not room:
                    return {'success': False, 'error': 'Room not found'}
                
                if room.is_full():
                    return {'success': False, 'error': 'Room is full'}
                
                if room.is_expired():
                    return {'success': False, 'error': 'Room has expired'}
                
                # Add player
                room.add_player(player_id, display_name, avatar_color)
                
                logger.info(f"Player joined room {room_id}: {player_id}")
                
                return {
                    'success': True,
                    'player_id': player_id,
                    'room': self._serialize_room(room)
                }
        except Exception as e:
            logger.error(f"Error joining room: {e}", exc_info=True)
            return {'success': False, 'error': 'Internal server error'}
    
    def leave_room(self, room_id, player_id):
        """Remove a player from a room (thread-safe)"""
        try:
            with self._lock:
                room = self.get_room(room_id)
                if not room:
                    return False
                
                room.remove_player(player_id)
                
                # Clean up empty rooms
                if room.is_empty():
                    del self.rooms[room_id]
                    room_storage.delete_room(room_id)
                    logger.info(f"Room deleted (empty): {room_id}")
                
                return True
        except Exception as e:
            logger.error(f"Error leaving room: {e}", exc_info=True)
            return False
    
    def _serialize_room(self, room):
        """Convert room to JSON-serializable dict"""
        try:
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
        except Exception as e:
            logger.error(f"Error serializing room: {e}", exc_info=True)
            return {}
    
    def cleanup_expired_rooms(self):
        """Remove expired rooms (thread-safe)"""
        try:
            with self._lock:
                expired = [rid for rid, room in self.rooms.items() if room.is_expired()]
                
                for room_id in expired:
                    room = self.rooms[room_id]
                    del self.rooms[room_id]
                    room_storage.delete_room(room_id)
                    logger.info(f"Room cleaned up (expired): {room_id}")
                
                self.last_cleanup = datetime.now()
                return len(expired)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            return 0
    
    def maybe_cleanup(self):
        """Optionally run cleanup if interval has passed"""
        if (datetime.now() - self.last_cleanup).total_seconds() > self.cleanup_interval:
            self.cleanup_expired_rooms()
    
    def get_room_info(self, room_id):
        """Get serialized room info"""
        try:
            room = self.get_room(room_id)
            if not room:
                return None
            return self._serialize_room(room)
        except Exception as e:
            logger.error(f"Error getting room info: {e}", exc_info=True)
            return None

# Global instance
room_manager = RoomManager()
