/**
 * PlaySync - Socket.IO Client
 * Handles WebSocket connection and event management
 */

// Safe anime.js wrapper to handle play() interruptions gracefully
window.animePlay = function(target, params) {
    try {
        // Don't animate if element is being removed
        if (!document.body.contains(target)) {
            return null;
        }
        const animation = anime(Object.assign({}, params, { targets: target }));
        // Auto-pause to prevent AbortError on interruption
        animation.pause();
        animation.play();
        return animation;
    } catch (e) {
        console.warn('Animation interrupted (expected):', e.message);
        return null;
    }
};

class SocketClient {
    constructor() {
        this.socket = null;
        this.roomId = null;
        this.playerId = null;
        this.displayName = null;
        this.avatarColor = null;
        this.eventHandlers = {};
    }

    connect() {
        // Use WebSocket-only for stability
        console.log('[SOCKET] Connecting with WebSocket transport...');
        this.socket = io('/', { 
            transports: ['websocket'],
            upgrade: false,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: Infinity
        });

        this.socket.on('connect', () => {
            console.log('[SOCKET] Connected:', this.socket.id);
            this.emit('connected');
        });

        this.socket.on('disconnect', (reason) => {
            console.warn('[SOCKET] Disconnected - reason:', reason);
            this.emit('disconnected');
        });

        this.socket.on('connect_error', (error) => {
            console.error('[SOCKET] Connection error:', error);
            this.emit('connect_error', error);
        });

        this.socket.on('reconnect', () => {
            console.log('[SOCKET] Reconnected');
            this.emit('reconnected');
        });

        this.socket.on('reconnect_attempt', () => {
            console.log('[SOCKET] Attempting to reconnect...');
        });

        // Relay all server events
        this.socket.on('connect_response', (data) => this.emit('connect_response', data));
        this.socket.on('join_room_response', (data) => this.emit('join_room_response', data));
        this.socket.on('leave_room_response', (data) => this.emit('leave_room_response', data));
        this.socket.on('player_joined', (data) => this.emit('player_joined', data));
        this.socket.on('player_left', (data) => this.emit('player_left', data));
        this.socket.on('start_game_response', (data) => this.emit('start_game_response', data));
        this.socket.on('game_started', (data) => this.emit('game_started', data));
        this.socket.on('game_move_response', (data) => this.emit('game_move_response', data));
        this.socket.on('move_made', (data) => this.emit('move_made', data));
        this.socket.on('game_ended', (data) => this.emit('game_ended', data));
        this.socket.on('chat_message', (data) => this.emit('chat_message', data));
        this.socket.on('chat_history', (data) => this.emit('chat_history', data));
        this.socket.on('rematch_requested', (data) => this.emit('rematch_requested', data));
        this.socket.on('game_switched', (data) => this.emit('game_switched', data));
        
        // RPS-specific events
        this.socket.on('rps_round_update', (data) => this.emit('rps_round_update', data));
        this.socket.on('rps_timer_tick', (data) => this.emit('rps_timer_tick', data));
        this.socket.on('rps_choices_locked', (data) => this.emit('rps_choices_locked', data));
        this.socket.on('rps_result', (data) => this.emit('rps_result', data));
    }

    joinRoom(roomId, displayName, avatarColor) {
        this.roomId = roomId;
        this.displayName = displayName;
        this.avatarColor = avatarColor;

        // Ensure socket is connected before emitting
        if (!this.socket.connected) {
            console.warn('Socket not connected, waiting for connection...');
            return;
        }

        console.log('Sending join_room_request for room:', roomId);
        this.socket.emit('join_room_request', {
            room_id: roomId,
            display_name: displayName,
            avatar_color: avatarColor
        });
    }

    leaveRoom() {
        if (this.playerId && this.roomId) {
            this.socket.emit('leave_room_request', {
                room_id: this.roomId,
                player_id: this.playerId
            });
        }
    }

    startGame(gameType, resetScores = false) {
        if (this.roomId) {
            console.log('Emitting start_game_request:', { room_id: this.roomId, game_type: gameType, reset_scores: resetScores });
            this.socket.emit('start_game_request', {
                room_id: this.roomId,
                game_type: gameType,
                reset_scores: resetScores
            });
        } else {
            console.error('startGame called but roomId is not set');
        }
    }

    submitMove(move) {
        if (this.roomId) {
            this.socket.emit('game_move', {
                room_id: this.roomId,
                move: move
            });
        }
    }

    sendChat(message) {
        if (this.roomId) {
            this.socket.emit('chat_message', {
                room_id: this.roomId,
                message: message
            });
        }
    }

    requestChat() {
        if (this.roomId) {
            this.socket.emit('get_chat_history', {
                room_id: this.roomId
            });
        }
    }

    requestRematch() {
        if (this.roomId) {
            this.socket.emit('rematch_request', {
                room_id: this.roomId
            });
        }
    }

    switchGame() {
        if (this.roomId) {
            this.socket.emit('switch_game_request', {
                room_id: this.roomId
            });
        }
    }

    on(event, callback) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(callback);
    }

    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(callback => callback(data));
        }
    }

    setPlayerId(playerId) {
        this.playerId = playerId;
    }
}

// Global instance
window.socketClient = new SocketClient();
