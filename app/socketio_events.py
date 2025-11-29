"""
PlaySync Socket.IO Event Handlers
Real-time communication for rooms, players, and games
"""

from flask import request
from flask_socketio import emit, join_room, leave_room, rooms as get_rooms
from app import socketio
from app.room_manager import room_manager, GameType
from app.game_logic import create_game_manager
from app.utils import generate_display_name, get_random_avatar_color
import uuid
import time
import threading

# Track socket to player mapping
socket_to_player = {}  # {socket_id: player_id}
player_sockets = {}  # {player_id: socket_id}
disconnect_timers = {}  # {socket_id: timer_object}

# Chat history (ephemeral, per room)
chat_history = {}  # {room_id: [messages]}

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"[CONNECT] Client connected: {request.sid}")
    emit('connect_response', {
        'status': 'connected',
        'socket_id': request.sid,
        'message': 'Connected to PlaySync'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with safe delayed cleanup"""
    sid = request.sid
    player_id = socket_to_player.get(sid)
    
    print(f"[DISCONNECT] Client disconnected: {sid}, player_id: {player_id}")
    
    # Cancel any pending disconnect timer for this socket
    if sid in disconnect_timers:
        disconnect_timers[sid].cancel()
        del disconnect_timers[sid]
    
    # Schedule delayed cleanup (5 seconds) to verify socket is really gone
    def delayed_cleanup():
        # Check if socket has reconnected
        try:
            # If socket reconnected, socketio.server.sockets has it
            if sid in socketio.server.sids:
                print(f"[DISCONNECT_CLEANUP] Socket {sid} reconnected, keeping player {player_id}")
                return
        except:
            pass
        
        # Socket is really gone, cleanup
        if sid in socket_to_player:
            player_id_to_remove = socket_to_player.pop(sid)
            if player_id_to_remove in player_sockets:
                del player_sockets[player_id_to_remove]
            print(f"[DISCONNECT_CLEANUP] Cleaned up player {player_id_to_remove} after delayed verification")
        
        if sid in disconnect_timers:
            del disconnect_timers[sid]
    
    # Start 5-second delayed cleanup
    timer = threading.Timer(5.0, delayed_cleanup)
    disconnect_timers[sid] = timer
    timer.daemon = True
    timer.start()


@socketio.on('join_room_request')
def handle_join_room(data):
    """
    Join a room and register as a player
    Expected data: {'room_id': str}
    Optionally: {'display_name': str, 'avatar_color': str}
    """
    room_id = data.get('room_id', '').upper()
    
    # Validate room
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        emit('join_room_response', {
            'success': False,
            'error': 'Room not found'
        })
        return
    
    if room_obj.is_expired():
        emit('join_room_response', {
            'success': False,
            'error': 'Room has expired'
        })
        return
    
    if room_obj.is_full():
        emit('join_room_response', {
            'success': False,
            'error': 'Room is full'
        })
        return
    
    # Generate player identity
    player_id = str(uuid.uuid4())
    display_name = data.get('display_name') or generate_display_name()
    avatar_color = data.get('avatar_color') or get_random_avatar_color()
    
    # Add to room
    result = room_manager.join_room(room_id, player_id, display_name, avatar_color)
    if not result['success']:
        emit('join_room_response', {
            'success': False,
            'error': result.get('error', 'Could not join room')
        })
        return
    
    # Register socket-player mapping
    socket_to_player[request.sid] = player_id
    player_sockets[player_id] = request.sid
    
    # Join Socket.IO room
    join_room(room_id)
    
    # Send success response with room state
    emit('join_room_response', {
        'success': True,
        'player_id': player_id,
        'display_name': display_name,
        'avatar_color': avatar_color,
        'room': result['room']
    })
    
    # Broadcast player joined to all in room
    emit('player_joined', {
        'player_id': player_id,
        'display_name': display_name,
        'avatar_color': avatar_color,
        'room': result['room']
    }, room=room_id)
    
    # Initialize chat history if needed
    if room_id not in chat_history:
        chat_history[room_id] = []

@socketio.on('leave_room_request')
def handle_leave_room(data):
    """
    Leave a room
    Expected data: {'room_id': str, 'player_id': str}
    """
    room_id = data.get('room_id', '').upper()
    player_id = data.get('player_id')
    
    player_id_mapped = socket_to_player.get(request.sid)
    
    # Validate player identity
    if player_id != player_id_mapped:
        emit('leave_room_response', {
            'success': False,
            'error': 'Player ID mismatch'
        })
        return
    
    room_manager.leave_room(room_id, player_id)
    
    # Clean up mappings
    if request.sid in socket_to_player:
        del socket_to_player[request.sid]
    if player_id in player_sockets:
        del player_sockets[player_id]
    
    # Leave Socket.IO room
    leave_room(room_id)
    
    emit('leave_room_response', {'success': True})
    
    # Notify others
    room_obj = room_manager.get_room(room_id)
    if room_obj:
        emit('player_left', {
            'player_id': player_id,
            'room': room_manager.get_room_info(room_id)
        }, room=room_id)

@socketio.on('start_game_request')
def handle_start_game(data):
    """
    Start a new game in a room
    Expected data: {'room_id': str, 'game_type': str, 'reset_scores': bool (optional)}
    """
    print(f"[START_GAME] Received start_game_request: {data}")
    room_id = data.get('room_id', '').upper()
    game_type = data.get('game_type', '').lower()
    reset_scores = data.get('reset_scores', False)  # Default to False for rematch
    player_id = socket_to_player.get(request.sid)
    print(f"[START_GAME] room_id={room_id}, game_type={game_type}, reset_scores={reset_scores}, player_id={player_id}")
    
    room_obj = room_manager.get_room(room_id)
    print(f"[START_GAME] room_obj found: {room_obj is not None}")
    if not room_obj:
        print(f"[START_GAME] Room not found: {room_id}")
        emit('start_game_response', {
            'success': False,
            'error': 'Room not found'
        })
        return
    
    if player_id not in room_obj.players:
        print(f"[START_GAME] Player {player_id} not in room {room_id}")
        emit('start_game_response', {
            'success': False,
            'error': 'Not a member of this room'
        })
        return
    
    if room_obj.get_player_count() < 2:
        print(f"[START_GAME] Not enough players: {room_obj.get_player_count()}")
        emit('start_game_response', {
            'success': False,
            'error': 'Need at least 2 players to start'
        })
        return
    
    # Start game
    try:
        # Convert game_type string to GameType enum by matching against .value
        game_type_enum = None
        for gt in GameType:
            if gt.value == game_type:
                game_type_enum = gt
                break
        if not game_type_enum:
            raise KeyError(f"No GameType with value '{game_type}'")
        print(f"[START_GAME] game_type_enum: {game_type_enum}")
    except KeyError as e:
        print(f"[START_GAME] Invalid game type: {game_type} - {e}")
        emit('start_game_response', {
            'success': False,
            'error': f'Unknown game type: {game_type}'
        })
        return
    
    room_obj.start_game(game_type_enum, reset_scores=reset_scores)
    
    # Create game manager
    game_mgr = create_game_manager(game_type_enum, room_obj)
    print(f"[START_GAME] game_mgr created: {game_mgr is not None}")
    if not game_mgr:
        print(f"[START_GAME] Failed to create game manager for {game_type_enum}")
        emit('start_game_response', {
            'success': False,
            'error': 'Game manager not available'
        })
        return
    
    # Store game manager in room for event handling
    room_obj._game_manager = game_mgr
    
    game_mgr.start()
    print(f"[START_GAME] Game manager started")
    
    emit('start_game_response', {'success': True})
    print(f"[START_GAME] Emitted start_game_response success")
    
    # Broadcast game started
    print(f"[START_GAME] Emitting game_started to room {room_id}")
    emit('game_started', {
        'game_type': game_type_enum.value,
        'room': room_manager.get_room_info(room_id)
    }, room=room_id)
    print(f"[START_GAME] Emitted game_started")

@socketio.on('game_move')
def handle_game_move(data):
    """
    Submit a game move
    Expected data: {'room_id': str, 'move': <game_specific>}
    """
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj or not room_obj.current_game:
        emit('game_move_response', {
            'success': False,
            'error': 'No active game'
        })
        return
    
    if not hasattr(room_obj, '_game_manager'):
        emit('game_move_response', {
            'success': False,
            'error': 'Game manager not ready'
        })
        return
    
    game_mgr = room_obj._game_manager
    move_data = data.get('move', {})
    
    # Process move with game manager
    result = game_mgr.process_move(player_id, move_data)
    
    emit('game_move_response', {
        'success': result.get('valid', False),
        'message': result.get('message', ''),
        'data': {k: v for k, v in result.items() if k not in ['valid', 'message']}
    })
    
    # Send success response to current player
    # NOTE: We already emitted a response above; avoid duplicating.
    
    # Broadcast move to ALL players in room (including self)
    emit('move_made', {
        'player_id': player_id,
        'room': room_manager.get_room_info(room_id)
    }, room=room_id, include_self=True)
    
    # Check if game is complete
    if game_mgr.is_game_complete():
        print(f"[GAME_END] Game complete for room {room_id}")
        game_results = game_mgr.get_results()
        room_obj.end_game(game_results)
        print(f"[GAME_END] Results: {game_results}")
        
        # Broadcast game ended to ALL players (with current_game still set so scores serialize correctly)
        emit('game_ended', {
            'results': game_results,
            'room': room_manager.get_room_info(room_id)
        }, room=room_id, include_self=True)
        
        # NOW clear current_game after emission
        room_obj.current_game = None

@socketio.on('reaction_ready')
def handle_reaction_ready(data):
    """
    Signal that player is ready for reaction time game
    """
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj or not room_obj.current_game:
        return
    
    if hasattr(room_obj, '_game_manager'):
        game_mgr = room_obj._game_manager
        
        # Mark player as ready
        if hasattr(game_mgr, 'set_ready'):
            game_mgr.set_ready()

@socketio.on('chat_message')
def handle_chat_message(data):
    """
    Send a chat message in a room
    Expected data: {'room_id': str, 'message': str}
    """
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    message = data.get('message', '').strip()
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        return
    
    if player_id not in room_obj.players:
        return
    
    if not message or len(message) > 200:
        return
    
    # Initialize chat history if needed
    if room_id not in chat_history:
        chat_history[room_id] = []
    
    player = room_obj.players[player_id]
    chat_entry = {
        'player_id': player_id,
        'display_name': player.display_name,
        'avatar_color': player.avatar_color,
        'message': message,
        'timestamp': time.time()
    }
    
    # Keep only last 50 messages per room
    chat_history[room_id].append(chat_entry)
    if len(chat_history[room_id]) > 50:
        chat_history[room_id].pop(0)
    
    # Broadcast message
    emit('chat_message', chat_entry, room=room_id)

@socketio.on('rematch_request')
def handle_rematch(data):
    """
    Request a rematch
    Expected data: {'room_id': str}
    """
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        return
    
    if player_id not in room_obj.players:
        return
    
    # Broadcast rematch request
    emit('rematch_requested', {
        'player_id': player_id,
        'display_name': room_obj.players[player_id].display_name
    }, room=room_id)

@socketio.on('switch_game_request')
def handle_switch_game(data):
    """
    Request to switch to a different game
    Expected data: {'room_id': str}
    """
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        return
    
    # Reset game state
    room_obj.current_game = None
    if hasattr(room_obj, '_game_manager'):
        delattr(room_obj, '_game_manager')
    
    # Broadcast game switched
    emit('game_switched', {
        'room': room_manager.get_room_info(room_id)
    }, room=room_id)

@socketio.on('get_chat_history')
def handle_get_chat_history(data):
    """
    Request chat history for a room
    """
    room_id = data.get('room_id', '').upper()
    
    history = chat_history.get(room_id, [])
    emit('chat_history', {
        'messages': history
    })

# Periodic cleanup (can be run by background task or called manually)
def cleanup_rooms():
    """Cleanup expired rooms"""
    room_manager.maybe_cleanup()


# ============================================================================
# RPS TIMER-BASED GAME HANDLERS
# ============================================================================

# Track RPS timer games
rps_timers = {}  # {room_id: RPSTimerManager}

@socketio.on('rps_start')
def handle_rps_start(data):
    """Start a new RPS timer-based game"""
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    
    print(f"[RPS_START] Received RPS start request for room {room_id}, player {player_id}")
    
    room_obj = room_manager.get_room(room_id)
    if not room_obj:
        print(f"[RPS_START] Room not found: {room_id}")
        emit('rps_start_response', {'success': False, 'error': 'Room not found'})
        return
    
    if player_id not in room_obj.players:
        print(f"[RPS_START] Player not in room")
        emit('rps_start_response', {'success': False, 'error': 'Not a member of this room'})
        return
    
    if len(room_obj.players) < 2:
        print(f"[RPS_START] Not enough players: {len(room_obj.players)}")
        emit('rps_start_response', {'success': False, 'error': 'Need 2 players'})
        return
    
    # Stop any existing RPS timer
    if room_id in rps_timers:
        old_timer = rps_timers[room_id]
        old_timer.stop()
        del rps_timers[room_id]
    
    # Start new RPS timer
    from app.rps_timer import RPSTimerManager
    timer = RPSTimerManager(room_obj, socketio, room_id)
    rps_timers[room_id] = timer
    timer.start()
    
    print(f"[RPS_START] RPS timer started for room {room_id}")
    emit('rps_start_response', {'success': True})


@socketio.on('rps_choice')
def handle_rps_choice(data):
    """Submit a choice for RPS timer game"""
    room_id = data.get('room_id', '').upper()
    choice = data.get('choice', '')
    player_id = socket_to_player.get(request.sid)
    
    print(f"[RPS_CHOICE] Player {player_id} chose {choice} in room {room_id}")
    
    if room_id not in rps_timers:
        print(f"[RPS_CHOICE] No RPS game in room {room_id}")
        emit('rps_choice_response', {'success': False, 'error': 'Game not started'})
        return
    
    timer_game = rps_timers[room_id]
    result = timer_game.submit_choice(player_id, choice)
    
    if result['success']:
        emit('rps_choice_response', {'success': True, 'choice': choice})
    else:
        emit('rps_choice_response', {'success': False, 'error': result.get('error')})


@socketio.on('rps_stop')
def handle_rps_stop(data):
    """Stop RPS game"""
    room_id = data.get('room_id', '').upper()
    player_id = socket_to_player.get(request.sid)
    
    if room_id not in rps_timers:
        return
    
    timer_game = rps_timers[room_id]
    timer_game.stop()
    del rps_timers[room_id]
    
    print(f"[RPS_STOP] RPS game stopped for room {room_id}")
    emit('rps_stopped', {'room_id': room_id}, room=room_id)

