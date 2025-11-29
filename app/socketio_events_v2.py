"""
PlaySync Socket.IO Event Handlers (Enhanced with logging and error handling)
Real-time communication for rooms, players, and games

Key improvements:
- Comprehensive logging for debugging
- Exception handling around all operations
- Prevent duplicate joins
- Server-authoritative game state validation
- Graceful error responses
"""

from flask import request
from flask_socketio import emit, join_room, leave_room, rooms as get_rooms
from app import socketio
from app.room_manager import room_manager, GameType
from app.game_logic import create_game_manager
from app.utils import generate_display_name, get_random_avatar_color
import uuid
import time
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Track socket to player mapping
socket_to_player = {}  # {socket_id: player_id}
player_sockets = {}  # {player_id: socket_id}
socket_to_room = {}   # {socket_id: room_id} for tracking

# Chat history (ephemeral, per room)
chat_history = {}  # {room_id: [messages]}

# Ephemeral token for reconnect grace period (socket_id -> token, timestamp)
reconnect_tokens = {}  # {socket_id: (ephemeral_token, timestamp, room_id, player_id)}

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        logger.info(f"Client connected: socket_id={request.sid}")
        emit('connect_response', {
            'status': 'connected',
            'socket_id': request.sid,
            'message': 'Connected to PlaySync'
        })
    except Exception as e:
        logger.error(f"Error in handle_connect: {e}", exc_info=True)
        emit('error', {'message': 'Connection error'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection - cleanup and prepare for reconnect grace period"""
    try:
        player_id = socket_to_player.pop(request.sid, None)
        room_id = socket_to_room.pop(request.sid, None)
        
        if player_id:
            logger.info(f"Client disconnected: socket_id={request.sid}, player_id={player_id}, room_id={room_id}")
            
            # Generate ephemeral token for reconnect grace period (30 seconds)
            token = str(uuid.uuid4())
            reconnect_tokens[request.sid] = (token, time.time(), room_id, player_id)
            
            # Clean up player socket mapping
            if player_id in player_sockets:
                del player_sockets[player_id]
            
            # Broadcast player left to room
            if room_id:
                room_obj = room_manager.get_room(room_id)
                if room_obj:
                    emit('player_left', {
                        'player_id': player_id,
                        'room': room_manager._serialize_room(room_obj)
                    }, room=room_id)
        else:
            logger.debug(f"Client disconnected without join: socket_id={request.sid}")
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {e}", exc_info=True)

@socketio.on('join_room_request')
def handle_join_room(data):
    """
    Join a room and register as a player
    Expected data: {'room_id': str, 'display_name': str, 'avatar_color': str}
    """
    try:
        room_id = (data.get('room_id', '') or '').upper()
        display_name = data.get('display_name') or generate_display_name()
        avatar_color = data.get('avatar_color') or get_random_avatar_color()
        
        logger.info(f"Join request: room_id={room_id}, socket_id={request.sid}, player_name={display_name}")
        
        # Prevent duplicate joins from same socket
        if request.sid in socket_to_player:
            logger.warning(f"Duplicate join attempt from socket_id={request.sid}")
            emit('join_room_response', {
                'success': False,
                'error': 'Already joined a room'
            })
            return
        
        # Validate room exists
        room_obj = room_manager.get_room(room_id)
        if not room_obj:
            logger.warning(f"Join failed: room not found (room_id={room_id})")
            emit('join_room_response', {
                'success': False,
                'error': 'Room not found'
            })
            return
        
        # Check if room expired
        if room_obj.is_expired():
            logger.warning(f"Join failed: room expired (room_id={room_id})")
            emit('join_room_response', {
                'success': False,
                'error': 'Room has expired'
            })
            return
        
        # Check if room full
        if room_obj.is_full():
            logger.warning(f"Join failed: room full (room_id={room_id})")
            emit('join_room_response', {
                'success': False,
                'error': 'Room is full'
            })
            return
        
        # Generate player identity
        player_id = str(uuid.uuid4())
        
        # Add to room (atomically)
        result = room_manager.join_room(room_id, player_id, display_name, avatar_color)
        if not result['success']:
            logger.error(f"Join failed in room_manager: {result.get('error')}")
            emit('join_room_response', {
                'success': False,
                'error': result.get('error', 'Could not join room')
            })
            return
        
        # Register socket-player mapping (NO DUPLICATES)
        socket_to_player[request.sid] = player_id
        socket_to_room[request.sid] = room_id
        player_sockets[player_id] = request.sid
        
        # Join Socket.IO room
        join_room(room_id)
        
        logger.info(f"Join successful: room_id={room_id}, player_id={player_id}, socket_id={request.sid}")
        
        # Send success response with room state
        emit('join_room_response', {
            'success': True,
            'player_id': player_id,
            'display_name': display_name,
            'avatar_color': avatar_color,
            'room': result['room']
        })
        
        # Broadcast to other players in room
        emit('player_joined', {
            'player_id': player_id,
            'display_name': display_name,
            'avatar_color': avatar_color,
            'room': result['room']
        }, room=room_id, skip_sid=request.sid)
        
    except Exception as e:
        logger.error(f"Error in handle_join_room: {e}", exc_info=True)
        emit('join_room_response', {
            'success': False,
            'error': 'Internal server error'
        })

@socketio.on('leave_room_request')
def handle_leave_room(data):
    """Leave the current room"""
    try:
        player_id = socket_to_player.get(request.sid)
        room_id = socket_to_room.get(request.sid)
        
        if not player_id or not room_id:
            logger.warning(f"Leave request from socket not in room: socket_id={request.sid}")
            return
        
        logger.info(f"Leave request: room_id={room_id}, player_id={player_id}")
        
        # Remove from room
        room_manager.leave_room(room_id, player_id)
        
        # Cleanup mappings
        socket_to_player.pop(request.sid, None)
        socket_to_room.pop(request.sid, None)
        player_sockets.pop(player_id, None)
        
        # Leave Socket.IO room
        leave_room(room_id)
        
        # Broadcast to remaining players
        room_obj = room_manager.get_room(room_id)
        if room_obj:
            emit('player_left', {
                'player_id': player_id,
                'room': room_manager._serialize_room(room_obj)
            }, room=room_id)
        
        logger.info(f"Leave successful: room_id={room_id}, player_id={player_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_leave_room: {e}", exc_info=True)
        emit('error', {'message': 'Error leaving room'})

@socketio.on('start_game_request')
def handle_start_game(data):
    """Start a new game in the room"""
    try:
        player_id = socket_to_player.get(request.sid)
        room_id = socket_to_room.get(request.sid)
        game_type = data.get('game_type', '').lower()
        reset_scores = data.get('reset_scores', False)
        
        if not player_id or not room_id:
            logger.warning(f"Start game request from socket not in room: socket_id={request.sid}")
            emit('error', {'message': 'Not in a room'})
            return
        
        logger.info(f"Start game request: room_id={room_id}, game_type={game_type}, reset_scores={reset_scores}")
        
        # Validate game type
        try:
            game_enum = GameType[game_type.upper()]
        except KeyError:
            logger.warning(f"Invalid game type: {game_type}")
            emit('start_game_response', {
                'success': False,
                'error': 'Invalid game type'
            })
            return
        
        # Get room and start game
        room_obj = room_manager.get_room(room_id)
        if not room_obj:
            emit('start_game_response', {'success': False, 'error': 'Room not found'})
            return
        
        room_obj.start_game(game_enum, reset_scores=reset_scores)
        
        logger.info(f"Game started: room_id={room_id}, game_type={game_type}")
        
        emit('start_game_response', {'success': True})
        emit('game_started', {
            'game_type': game_type,
            'room': room_manager._serialize_room(room_obj)
        }, room=room_id)
        
    except Exception as e:
        logger.error(f"Error in handle_start_game: {e}", exc_info=True)
        emit('start_game_response', {
            'success': False,
            'error': 'Internal server error'
        })

@socketio.on('rps:choose')
def handle_rps_choose(data):
    """Handle RPS move submission (server-authoritative)"""
    try:
        player_id = socket_to_player.get(request.sid)
        room_id = socket_to_room.get(request.sid)
        choice = (data.get('choice', '') or '').lower()
        
        if not player_id or not room_id:
            logger.warning(f"RPS move from socket not in room: socket_id={request.sid}")
            emit('rps:move_error', {'reason': 'not_in_room'})
            return
        
        logger.debug(f"RPS choice: room_id={room_id}, player_id={player_id}, choice={choice}")
        
        # Validate choice
        valid_choices = ['rock', 'paper', 'scissors']
        if choice not in valid_choices:
            logger.warning(f"Invalid RPS choice: {choice}")
            emit('rps:move_error', {'reason': 'invalid_choice'})
            return
        
        # Get room and game
        room_obj = room_manager.get_room(room_id)
        if not room_obj or not room_obj.current_game:
            logger.warning(f"RPS move in room without active game")
            emit('rps:move_error', {'reason': 'no_active_game'})
            return
        
        # Process move through game manager
        game_mgr = create_game_manager(room_obj.current_game.game_type, room_obj)
        result = game_mgr.process_move(player_id, {'choice': choice})
        
        if not result['valid']:
            logger.warning(f"RPS move validation failed: {result.get('message')}")
            emit('rps:move_error', {'reason': result.get('message', 'invalid_move')})
            return
        
        emit('rps:move_accepted', {'message': 'Move received'})
        
        # Check if game is complete (both players chosen)
        if game_mgr.is_game_complete():
            logger.info(f"RPS round complete: room_id={room_id}")
            results = game_mgr.get_results()
            game_mgr.room.end_game(results)
            
            emit('rps:round_result', {
                'choices': results.get('choices'),
                'winner': results.get('winner'),
                'scores': results.get('scores'),
                'roundIndex': results.get('roundIndex')
            }, room=room_id)
            
            # Emit new round signal so clients reset UI
            emit('rps:new_round', {
                'message': 'Next round starting...'
            }, room=room_id)
        else:
            logger.debug(f"Waiting for second player: room_id={room_id}")
            emit('rps:waiting_for_opponent', {'message': 'Waiting for opponent...'}, room=room_id)
        
    except Exception as e:
        logger.error(f"Error in handle_rps_choose: {e}", exc_info=True)
        emit('rps:move_error', {'reason': 'server_error'})

@socketio.on('chat:send_message')
def handle_chat_message(data):
    """Handle chat message"""
    try:
        player_id = socket_to_player.get(request.sid)
        room_id = socket_to_room.get(request.sid)
        message = data.get('message', '').strip()
        
        if not player_id or not room_id:
            return
        
        if not message or len(message) > 500:
            logger.warning(f"Invalid chat message length")
            emit('error', {'message': 'Message too long'})
            return
        
        logger.debug(f"Chat message: room_id={room_id}, player_id={player_id}, len={len(message)}")
        
        # Store in history
        if room_id not in chat_history:
            chat_history[room_id] = []
        
        chat_history[room_id].append({
            'player_id': player_id,
            'message': message,
            'timestamp': time.time()
        })
        
        # Broadcast to room
        emit('chat_message', {
            'player_id': player_id,
            'message': message,
            'timestamp': time.time()
        }, room=room_id)
        
    except Exception as e:
        logger.error(f"Error in handle_chat_message: {e}", exc_info=True)

@socketio.on('chat:request_history')
def handle_chat_history_request(data):
    """Send chat history for the current room"""
    try:
        room_id = socket_to_room.get(request.sid)
        
        if not room_id:
            return
        
        history = chat_history.get(room_id, [])
        logger.debug(f"Chat history requested: room_id={room_id}, messages={len(history)}")
        
        emit('chat_history', {'messages': history})
        
    except Exception as e:
        logger.error(f"Error in handle_chat_history_request: {e}", exc_info=True)
