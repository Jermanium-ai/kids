/**
 * PlaySync - Room Management (Main Controller)
 */

const ROOM_ID = window.location.pathname.split('/').pop();

let roomState = {
    roomId: ROOM_ID,
    playerId: null,
    displayName: null,
    avatarColor: null,
    players: {},
    currentGame: null,
    gameManager: null,
    phase: 'waiting' // waiting, game_selection, game, results
};

const gameClasses = {
    'rps': RockPaperScissorsGame,
    'tictactoe': TicTacToeGame,
    'reaction': ReactionTimeGame,
    'quickmath': QuickMathGame,
    'would_you_rather': WouldYouRatherGame
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    socketClient.connect();

    // Join room when socket connects
    socketClient.on('connect_response', () => {
        console.log('Socket connected, joining room...');
        const displayName = generateDisplayName();
        const avatarColor = getRandomAvatarColor();
        
        // Only join if socket is actually connected
        if (socketClient.socket && socketClient.socket.connected) {
            socketClient.joinRoom(ROOM_ID, displayName, avatarColor);
        } else {
            console.warn('Socket not connected yet, retrying...');
            setTimeout(() => {
                socketClient.joinRoom(ROOM_ID, displayName, avatarColor);
            }, 1000);
        }
    });

    // Setup event listeners
    setupEventListeners();
    setupSocketListeners();
});

// ============================================================================
// EVENT LISTENERS
// ============================================================================

function setupEventListeners() {
    // Leave button
    document.getElementById('leave-room-btn').addEventListener('click', () => {
        if (confirm('Leave the room?')) {
            socketClient.leaveRoom();
            setTimeout(() => {
                window.location.href = '/';
            }, 500);
        }
    });

    // Copy link button
    document.getElementById('copy-link-btn').addEventListener('click', () => {
        const linkInput = document.getElementById('room-link-input');
        linkInput.select();
        document.execCommand('copy');
        
        const btn = document.getElementById('copy-link-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    });

    // Download QR
    document.getElementById('download-qr-btn').addEventListener('click', () => {
        const qrImg = document.getElementById('qr-code');
        const link = document.createElement('a');
        link.href = qrImg.src;
        link.download = `playsync-${ROOM_ID}.png`;
        link.click();
    });

    // Game selection
    document.querySelectorAll('.game-select-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const gameType = e.currentTarget.dataset.game;
            console.log('Game button clicked:', gameType, 'Room ID:', socketClient.roomId);
            
            // Show mode selection modal
            const modeModal = document.getElementById('mode-modal');
            modeModal.classList.remove('hidden');
            
            // Set up mode buttons
            document.getElementById('mode-simple-btn').onclick = () => {
                modeModal.classList.add('hidden');
                roomState.gameMode = 'simple';
                socketClient.startGame(gameType, true);  // true = reset scores on new game
            };
            
            document.getElementById('mode-challenge-btn').onclick = () => {
                modeModal.classList.add('hidden');
                roomState.gameMode = 'challenge';
                socketClient.startGame(gameType, true);  // true = reset scores on new game
            };
        });
    });

    // Game action buttons - Rematch should auto-restart, Switch should change game
    document.getElementById('rematch-btn').addEventListener('click', () => {
        console.log('Rematch clicked - auto-restarting:', roomState.currentGame);
        socketClient.startGame(roomState.currentGame);
    });

    document.getElementById('switch-game-btn').addEventListener('click', () => {
        console.log('Switch Game clicked');
        roomState.currentGame = null;
        roomState.gameMode = 'simple';
        roomState.gameManager = null;
        setPhase('game_selection');
    });
    
    // Persistent Change Game button in game header
    document.getElementById('change-game-header-btn').addEventListener('click', () => {
        console.log('Change Game (header) clicked');
        roomState.currentGame = null;
        roomState.gameMode = 'simple';
        roomState.gameManager = null;
        setPhase('game_selection');
    });
    // Chat
    document.getElementById('chat-send-btn').addEventListener('click', () => {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (message) {
            socketClient.sendChat(message);
            input.value = '';
        }
    });

    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('chat-send-btn').click();
        }
    });
}

function setupSocketListeners() {
    socketClient.on('join_room_response', (data) => {
        console.log('Join room response:', data);
        if (data.success) {
            roomState.playerId = data.player_id;
            roomState.displayName = data.display_name;
            roomState.avatarColor = data.avatar_color;
            socketClient.setPlayerId(data.player_id);
            socketClient.roomId = ROOM_ID;  // Set room ID so startGame() works

            console.log('Joined room as:', data.display_name, 'Total players:', data.room.players.length);
            updateRoomDisplay(data.room);
            
            // If joining and there are already 2 players, enable game selection immediately
            if (data.room.players && data.room.players.length >= 2 && roomState.phase === 'waiting') {
                console.log('2 players already present, enabling game selection');
                setPhase('game_selection');
            }
        } else {
            console.error('Failed to join room:', data.error);
            const errorMsg = data.error || 'Unknown error';
            alert('Could not join room: ' + errorMsg);
            setTimeout(() => {
                window.location.href = '/';
            }, 500);
        }
    });

    socketClient.on('player_joined', (data) => {
        console.log('Player joined:', data.display_name, 'Total players:', data.room.players.length);
        updateRoomDisplay(data.room);
        
        // If we now have 2 players, enable game selection
        if (data.room.players && data.room.players.length >= 2 && roomState.phase === 'waiting') {
            console.log('2 players detected, enabling game selection');
            setPhase('game_selection');
        }
    });

    socketClient.on('player_left', (data) => {
        console.log('Player left');
        updateRoomDisplay(data.room);
        
        // Reset to waiting if we're back to 1 player
        if (data.room.players && data.room.players.length < 2) {
            setPhase('waiting');
            roomState.currentGame = null;
        }
    });

    socketClient.on('game_started', (data) => {
        console.log('Game started:', data.game_type, 'Mode:', roomState.gameMode);
        roomState.currentGame = data.game_type;
        
        // Hide mode modal if visible
        const modeModal = document.getElementById('mode-modal');
        if (modeModal && !modeModal.classList.contains('hidden')) {
            modeModal.classList.add('hidden');
        }
        
        // Clear game container and results
        const gameContainer = document.getElementById('game-container');
        const resultsContainer = document.getElementById('phase-results');
        if (gameContainer) gameContainer.innerHTML = '';
        
        setPhase('game');
        
        // Initialize game UI with fresh state
        initializeGameUI(data.game_type, data.room);
    });

    socketClient.on('game_move_response', (data) => {
        if (roomState.gameManager?.onMoveResponse) {
            roomState.gameManager.onMoveResponse(data);
        }
    });

    socketClient.on('move_made', (data) => {
        console.log('Move made');
        if (roomState.gameManager?.onMoveMade) {
            roomState.gameManager.onMoveMade(data);
        }
    });

    socketClient.on('game_ended', (data) => {
        console.log('Game ended:', data);
        
        // Update room display with final scores FIRST
        if (data.room) {
            updateRoomDisplay(data.room);
        }
        
        const results = data.results;
        
        // Display game-specific results on game container for a moment
        if (roomState.gameManager?.onGameEnded) {
            roomState.gameManager.onGameEnded(results);
        }
        
        // Show results phase briefly, then auto-restart
        setPhase('results');
        displayResultsDetails(results);
        
        // After 2 seconds, auto-restart the game
        setTimeout(() => {
            console.log('Auto-restarting game:', roomState.currentGame);
            socketClient.startGame(roomState.currentGame);
        }, 2000);
    });

    socketClient.on('chat_message', (data) => {
        addChatMessage(data);
    });

    socketClient.on('chat_history', (data) => {
        data.messages.forEach(msg => addChatMessage(msg));
    });

    socketClient.on('game_switched', (data) => {
        console.log('Game switched');
        roomState.currentGame = null;
        setPhase('game_selection');
    });
}

// ============================================================================
// UI MANAGEMENT
// ============================================================================

function setPhase(phase) {
    roomState.phase = phase;
    
    // Hide all phases
    document.getElementById('phase-waiting').classList.add('hidden');
    document.getElementById('phase-game-selection').classList.add('hidden');
    document.getElementById('phase-game').classList.add('hidden');
    document.getElementById('phase-results').classList.add('hidden');

    // Show target phase
    const phaseMap = {
        'waiting': 'phase-waiting',
        'game_selection': 'phase-game-selection',
        'game': 'phase-game',
        'results': 'phase-results'
    };

    document.getElementById(phaseMap[phase])?.classList.remove('hidden');

    // Show chat if game is active
    const chatSection = document.getElementById('chat-section');
    if (phase === 'game' || phase === 'results') {
        chatSection.classList.remove('hidden');
        socketClient.requestChat();
    } else {
        chatSection.classList.add('hidden');
    }
}

function updateRoomDisplay(room) {
    roomState.players = {};
    
    // Clear all player slots first
    document.getElementById('player-slot-1').innerHTML = '';
    document.getElementById('player-slot-2').innerHTML = '';
    
    room.players.forEach((player, idx) => {
        roomState.players[player.player_id] = player;
        
        // Assign to correct slot based on join order (0 = Player 1, 1 = Player 2)
        const slotNumber = idx + 1;  // Convert 0-based to 1-based
        const slotDiv = document.getElementById(`player-slot-${slotNumber}`);
        
        if (slotDiv) {
            const isMe = player.player_id === roomState.playerId;
            const playerLabel = isMe ? 'You' : `Player ${slotNumber}`;
            
            slotDiv.innerHTML = `
                <div class="text-sm text-slate-400">${playerLabel}</div>
                <div class="w-12 h-12 rounded-lg" style="background-color: ${player.avatar_color}; opacity: 0.8;"></div>
                <div class="text-sm font-semibold">${player.display_name}</div>
            `;
            slotDiv.classList.add('animate-fade-in');
        }
    });

    // Update scores if game is ongoing
    if (room.current_game) {
        const players = room.players;
        if (players.length >= 2) {
            document.getElementById('player1-name').textContent = players[0].display_name;
            document.getElementById('player1-score').textContent = room.current_game.player_scores[players[0].player_id] || 0;
            document.getElementById('player2-name').textContent = players[1].display_name;
            document.getElementById('player2-score').textContent = room.current_game.player_scores[players[1].player_id] || 0;
        }
    }
}

function initializeGameUI(gameType, room) {
    const container = document.getElementById('game-container');
    const titleDiv = document.getElementById('game-title');

    // Map game type to title
    const titles = {
        'rps': 'Rock Paper Scissors',
        'tictactoe': 'Tic Tac Toe',
        'reaction': 'Reaction Time Duel',
        'quickmath': 'Quick Math Duel',
        'would_you_rather': 'Would You Rather'
    };

    titleDiv.textContent = titles[gameType] || gameType;

    // Create game manager
    const GameClass = gameClasses[gameType];
    if (GameClass) {
        roomState.gameManager = new GameClass();
        // Pass gameMode to game manager so it can access it for Truth or Dare logic
        roomState.gameManager.gameMode = roomState.gameMode;
        roomState.gameManager.render(container, room.current_game);
    }
}

function displayResultsDetails(results) {
    const detailsDiv = document.getElementById('results-details');
    
    if (!results) {
        detailsDiv.innerHTML = '<p>Game results unavailable</p>';
        return;
    }

    let html = '<div class="space-y-2">';

    if (results.rounds) {
        html += '<div class="font-semibold text-sm mb-3">Rounds:</div>';
        results.rounds.forEach((round, idx) => {
            const emoji = round.result === 'tie' ? '🤝' : (round.result === 'p1_win' ? '✓' : '✗');
            html += `<div class="text-sm text-slate-400">${emoji} Round ${idx + 1}</div>`;
        });
    }

    if (results.reaction_times) {
        html += '<div class="font-semibold text-sm mb-2 mt-3">Reaction Times:</div>';
        Object.entries(results.reaction_times).forEach(([playerId, time]) => {
            html += `<div class="text-sm text-slate-400">${time}ms</div>`;
        });
    }

    html += '</div>';
    detailsDiv.innerHTML = html;
}

function addChatMessage(data) {
    const chatDiv = document.getElementById('chat-messages');
    const msgEl = document.createElement('div');
    msgEl.className = 'text-xs py-1 px-2 bg-slate-600 rounded';
    msgEl.innerHTML = `<span class="font-semibold" style="color: ${data.avatar_color};">${data.display_name}:</span> <span class="text-slate-300">${data.message}</span>`;
    chatDiv.appendChild(msgEl);
    chatDiv.scrollTop = chatDiv.scrollHeight;

    // Limit to 50 messages visible
    while (chatDiv.children.length > 50) {
        chatDiv.removeChild(chatDiv.firstChild);
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function generateDisplayName() {
    const adjectives = [
        "Swift", "Clever", "Bold", "Brave", "Quick", "Sharp",
        "Smart", "Keen", "Alert", "Nimble", "Slick", "Deft"
    ];
    const nouns = [
        "Phoenix", "Tiger", "Falcon", "Eagle", "Wolf", "Lion",
        "Raven", "Fox", "Cheetah", "Hawk", "Osprey", "Lynx"
    ];
    const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    return `${adj} ${noun}`;
}

function getRandomAvatarColor() {
    const colors = [
        "#0D9488",  // Teal-700
        "#14B8A6",  // Teal-500
        "#2DD4BF",  // Teal-400
        "#06B6D4",  // Cyan-500
        "#0891B2",  // Cyan-600
        "#155E75",  // Slate-900
        "#1F2937",  // Gray-800
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}
