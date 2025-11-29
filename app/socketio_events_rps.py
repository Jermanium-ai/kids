"""
PlaySync Socket.IO Event Handlers - RPS TIMER SYSTEM
Real-time communication with server-authoritative RPS timer
"""

from flask import request
from flask_socketio import emit, join_room, leave_room
from app import socketio
from app.room_manager import room_manager, GameType
from app.rps_manager import RockPaperScissorsManager
from app.game_logic import create_game_manager
from app.utils import generate_display_name, get_random_avatar_color
import uuid
import time
import logging

logger = logging.getLogger(__name__)

# Track socket to player mapping
socket_to_player = {}  # {socket_id: player_id}
player_sockets = {}  # {player_id: socket_id}
rps_managers = {}  # {room_id: RockPaperScissorsManager}

# Chat history
chat_history = {}  # {room_id: [messages]}


# ============================================================================
# CORE SOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connect_response', {
        'status': 'connected',
        'socket_id': request.sid,
        'message': 'Connected to PlaySync'
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    player_id = socket_to_player.pop(request.sid, None)
    if player_id and player_id in player_sockets:
        del player_sockets[player_id]
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('join_room_request')
def handle_join_room(data):
    """Join a room"""
    room_id = data.get('room_id', '').upper()
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        emit('join_room_response', {'success': False, 'error': 'Room not found'})
        return
    
    if room_obj.is_expired():
        emit('join_room_response', {'success': False, 'error': 'Room has expired'})
        return
    
    if room_obj.is_full():
        emit('join_room_response', {'success': False, 'error': 'Room is full'})
        return
    
    # Generate player identity
    player_id = str(uuid.uuid4())
    display_name = data.get('display_name') or generate_display_name()
    avatar_color = data.get('avatar_color') or get_random_avatar_color()
    
    # Add to room
    result = room_manager.join_room(room_id, player_id, display_name, avatar_color)
    if not result['success']:
        emit('join_room_response', {'success': False, 'error': result.get('error', 'Could not join')})
        return
    
    # Register socket-player mapping
    socket_to_player[request.sid] = player_id
    player_sockets[player_id] = request.sid
    
    # Join Socket.IO room
    join_room(room_id)
    
    # Send success to joining player
    emit('join_room_response', {
        'success': True,
        'player_id': player_id,
        'display_name': display_name,
        'avatar_color': avatar_color,
        'room': result['room']
    })
    
    # Broadcast to all players
    emit('player_joined', {
        'player_id': player_id,
        'display_name': display_name,
        'avatar_color': avatar_color,
        'room': result['room']
    }, room=room_id)
    
    # Initialize chat if needed
    if room_id not in chat_history:
        chat_history[room_id] = []
    
    logger.info(f"Player {player_id} joined room {room_id}")


@socketio.on('leave_room_request')
def handle_leave_room(data):
    """Leave a room"""
    room_id = data.get('room_id', '').upper()
    player_id = data.get('player_id')
    player_id_mapped = socket_to_player.get(request.sid)
    
    if player_id != player_id_mapped:
        emit('leave_room_response', {'success': False, 'error': 'Player ID mismatch'})
        return
    
    # Stop RPS manager if active
    if room_id in rps_managers:
        rps_managers[room_id].stop()
        del rps_managers[room_id]
    
    room_manager.leave_room(room_id, player_id)
    
    if request.sid in socket_to_player:
        del socket_to_player[request.sid]
    if player_id in player_sockets:
        del player_sockets[player_id]
    
    leave_room(room_id)
    
    emit('leave_room_response', {'success': True})
    
    room_obj = room_manager.get_room(room_id)
    if room_obj:
        emit('player_left', {
            'player_id': player_id,
            'room': room_manager.get_room_info(room_id)
        }, room=room_id)
    
    logger.info(f"Player {player_id} left room {room_id}")


# ============================================================================
# GAME CONTROL
# ============================================================================

@socketio.on('start_game_request')
def handle_start_game(data):
    """Start a new game"""
    room_id = data.get('room_id', '').upper()
    game_type = data.get('game_type', '').lower()
    player_id = socket_to_player.get(request.sid)
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        emit('start_game_response', {'success': False, 'error': 'Room not found'})
        return
    
    if player_id not in room_obj.players:
        emit('start_game_response', {'success': False, 'error': 'Not a member of this room'})
        return
    
    if room_obj.get_player_count() < 2:
        emit('start_game_response', {'success': False, 'error': 'Need 2 players'})
        return
    
    # For RPS, use new timer-based manager
    if game_type == 'rps':
        try:
            # Stop any existing RPS manager
            if room_id in rps_managers:
                rps_managers[room_id].stop()
            
            # Initialize game on room
            room_obj.start_game(GameType.RPS, reset_scores=data.get('reset_scores', False))
            
            # Create new RPS manager
            rps_mgr = RockPaperScissorsManager(room_obj)
            rps_managers[room_id] = rps_mgr
            rps_mgr.start()
            
            logger.info(f"RPS game started in room {room_id}")
            
            emit('start_game_response', {'success': True})
            
            # Broadcast to all players
            emit('game_started', {
                'game_type': 'rps',
                'room': room_manager.get_room_info(room_id)
            }, room=room_id)
            
            return
        
        except Exception as e:
            logger.error(f"Error starting RPS: {e}")
            emit('start_game_response', {'success': False, 'error': str(e)})
            return
    
    # For other games, use legacy system
    try:
        game_type_enum = None
        for gt in GameType:
            if gt.value == game_type:
                game_type_enum = gt
                break
        
        if not game_type_enum:
            emit('start_game_response', {'success': False, 'error': f'Unknown game: {game_type}'})
            return
        
        room_obj.start_game(game_type_enum, reset_scores=data.get('reset_scores', False))
        game_mgr = create_game_manager(game_type_enum, room_obj)
        
        if not game_mgr:
            emit('start_game_response', {'success': False, 'error': 'Game manager failed'})
            return
        
        room_obj._game_manager = game_mgr
        game_mgr.start()
        
        emit('start_game_response', {'success': True})
        emit('game_started', {
            'game_type': game_type_enum.value,
            'room': room_manager.get_room_info(room_id)
        }, room=room_id)
    
    except Exception as e:
        logger.error(f"Error starting game {game_type}: {e}")
        emit('start_game_response', {'success': False, 'error': str(e)})


# ============================================================================
# RPS-SPECIFIC EVENTS
# ============================================================================

@socketio.on('rps:choose')
def handle_rps_choose(data):
    """
    Player chooses Rock/Paper/Scissors during countdown.
    Can change choice during timer; only last one counts.
    """
    room_id = data.get('room_id', '').upper()
    choice = data.get('choice', '').lower()
    player_id = socket_to_player.get(request.sid)
    
    if room_id not in rps_managers:
        emit('rps:choose_response', {'valid': False, 'error': 'Game not active'})
        return
    
    rps_mgr = rps_managers[room_id]
    result = rps_mgr.record_choice(player_id, choice)
    
    emit('rps:choose_response', {
        'valid': result['valid'],
        'message': result['message']
    })
    
    # Broadcast choice to all (for UI feedback)
    if result['valid']:
        emit('rps:choice_recorded', {
            'player_id': player_id
        }, room=room_id)
    
    logger.info(f"Player {player_id} chose {choice} in room {room_id}")


# ============================================================================
# GENERIC GAME EVENTS (for non-RPS games)
# ============================================================================

@socketio.on('game_move')
def handle_game_move(data):
    """Generic game move (for non-RPS games)"""
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj or not room_obj.current_game:
        emit('game_move_response', {'success': False, 'error': 'No active game'})
        return
    
    if not hasattr(room_obj, '_game_manager'):
        emit('game_move_response', {'success': False, 'error': 'Game manager not ready'})
        return
    
    game_mgr = room_obj._game_manager
    move_data = data.get('move', {})
    
    result = game_mgr.process_move(player_id, move_data)
    
    emit('game_move_response', {
        'success': result.get('valid', False),
        'message': result.get('message', '')
    })
    
    emit('move_made', {
        'player_id': player_id,
        'room': room_manager.get_room_info(room_id)
    }, room=room_id, include_self=True)
    
    if game_mgr.is_game_complete():
        game_results = game_mgr.get_results()
        room_obj.end_game(game_results)
        
        emit('game_ended', {
            'results': game_results,
            'room': room_manager.get_room_info(room_id)
        }, room=room_id, include_self=True)
        
        room_obj.current_game = None


# ============================================================================
# CHAT
# ============================================================================

@socketio.on('send_chat')
def handle_send_chat(data):
    """Send chat message"""
    room_id = data.get('room_id', '').upper()
    message = data.get('message', '').strip()
    player_id = socket_to_player.get(request.sid)
    
    if not message:
        return
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        return
    
    if player_id not in room_obj.players:
        return
    
    player = room_obj.players[player_id]
    timestamp = time.time()
    
    chat_msg = {
        'player_id': player_id,
        'display_name': player.display_name,
        'avatar_color': player.avatar_color,
        'message': message,
        'timestamp': timestamp
    }
    
    if room_id not in chat_history:
        chat_history[room_id] = []
    
    chat_history[room_id].append(chat_msg)
    
    emit('chat_message', chat_msg, room=room_id)
