/**
 * PlaySync Socket.IO Client Wrapper (UPDATED FOR RPS TIMER SYSTEM)
 */

class SocketIOClient {
    constructor() {
        this.socket = null;
        this.playerId = null;
        this.roomId = null;
        this.eventListeners = {};
    }

    connect() {
        this.socket = io({
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000
        });

        // Built-in handlers
        this.socket.on('connect', () => {
            console.log('[Socket] Connected:', this.socket.id);
            this.emit('connect_response');
        });

        this.socket.on('disconnect', () => {
            console.log('[Socket] Disconnected');
        });

        this.socket.on('connect_error', (error) => {
            console.error('[Socket] Connection error:', error);
        });

        // Forward all events to listeners
        this.socket.onAny((eventName, ...args) => {
            if (this.eventListeners[eventName]) {
                this.eventListeners[eventName].forEach(callback => callback(...args));
            }
        });
    }

    on(eventName, callback) {
        if (!this.eventListeners[eventName]) {
            this.eventListeners[eventName] = [];
        }
        this.eventListeners[eventName].push(callback);
    }

    emit(eventName, data) {
        if (!this.socket) {
            console.warn('[Socket] Socket not connected');
            return;
        }
        this.socket.emit(eventName, data);
    }

    setPlayerId(playerId) {
        this.playerId = playerId;
    }

    // ========================================================================
    // ROOM MANAGEMENT
    // ========================================================================

    joinRoom(roomId, displayName, avatarColor) {
        this.emit('join_room_request', {
            room_id: roomId,
            display_name: displayName,
            avatar_color: avatarColor
        });
    }

    leaveRoom() {
        this.emit('leave_room_request', {
            room_id: this.roomId,
            player_id: this.playerId
        });
    }

    // ========================================================================
    // GAME CONTROL
    // ========================================================================

    startGame(gameType, resetScores = true) {
        this.emit('start_game_request', {
            room_id: this.roomId,
            game_type: gameType,
            reset_scores: resetScores
        });
    }

    // ========================================================================
    // RPS SPECIFIC
    // ========================================================================

    rpsChoose(choice) {
        this.emit('rps:choose', {
            room_id: this.roomId,
            choice: choice
        });
    }

    // ========================================================================
    // GENERIC GAME MOVES (for non-RPS games)
    // ========================================================================

    submitMove(move) {
        this.emit('game_move', {
            room_id: this.roomId,
            move: move
        });
    }

    // ========================================================================
    // CHAT
    // ========================================================================

    sendChat(message) {
        this.emit('send_chat', {
            room_id: this.roomId,
            message: message
        });
    }
}

const socketClient = new SocketIOClient();
