/**
 * PlaySync - Room Management (UPDATED FOR RPS TIMER SYSTEM)
 * Fixes currentGame undefined error and ensures proper game initialization
 */

const ROOM_ID = window.location.pathname.split('/').pop();

// Safe logger (fallback if not defined)
const logger = window.logger || {
    info: (msg) => console.log('[LOG]', msg),
    warn: (msg) => console.warn('[WARN]', msg),
    error: (msg) => console.error('[ERROR]', msg)
};

// FIX FOR CURRENTGAME UNDEFINED:
// Initialize roomState with explicit null checks and validation
let roomState = {
    roomId: ROOM_ID,
    playerId: null,
    displayName: null,
    avatarColor: null,
    room: null,  // Full room object
    players: {},
    currentGame: null,  // Will be set to game type (e.g., 'rps') when game starts
    gameManager: null,  // Instance of game class
    gameMode: 'simple',
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
    logger.info('[INIT] DOM loaded, connecting socket...');
    socketClient.connect();

    socketClient.on('connect_response', () => {
        logger.info('[INIT] Socket connected, joining room...');
        const displayName = generateDisplayName();
        const avatarColor = getRandomAvatarColor();
        
        if (socketClient.socket && socketClient.socket.connected) {
            socketClient.joinRoom(ROOM_ID, displayName, avatarColor);
        } else {
            logger.warn('[INIT] Socket not connected yet, retrying...');
            setTimeout(() => {
                socketClient.joinRoom(ROOM_ID, displayName, avatarColor);
            }, 1000);
        }
    });

    setupEventListeners();
    setupSocketListeners();
    setupRPSListeners();
});

// ============================================================================
// EVENT LISTENERS
// ============================================================================

function setupEventListeners() {
    // Leave button
    const leaveBtn = document.getElementById('leave-room-btn');
    if (leaveBtn) {
        leaveBtn.addEventListener('click', () => {
            if (confirm('Leave the room?')) {
                socketClient.leaveRoom();
                setTimeout(() => {
                    window.location.href = '/';
                }, 500);
            }
        });
    }

    // Copy link button
    const copyBtn = document.getElementById('copy-link-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const linkInput = document.getElementById('room-link-input');
            linkInput.select();
            document.execCommand('copy');
            
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = originalText;
            }, 2000);
        });
    }

    // Download QR
    const downloadBtn = document.getElementById('download-qr-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            const qrImg = document.getElementById('qr-code');
            const link = document.createElement('a');
            link.href = qrImg.src;
            link.download = `playsync-${ROOM_ID}.png`;
            link.click();
        });
    }

    // Game selection buttons
    document.querySelectorAll('.game-select-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const gameType = e.currentTarget.dataset.game;
            logger.info(`[GAME] Game button clicked: ${gameType}`);
            
            const modeModal = document.getElementById('mode-modal');
            if (modeModal) {
                modeModal.classList.remove('hidden');
                
                const simpleBtnId = 'mode-simple-btn';
                const challengeBtnId = 'mode-challenge-btn';
                
                const simpleBtn = document.getElementById(simpleBtnId);
                const challengeBtn = document.getElementById(challengeBtnId);
                
                if (simpleBtn) {
                    simpleBtn.onclick = () => {
                        modeModal.classList.add('hidden');
                        roomState.gameMode = 'simple';
                        socketClient.startGame(gameType, true);
                    };
                }
                
                if (challengeBtn) {
                    challengeBtn.onclick = () => {
                        modeModal.classList.add('hidden');
                        roomState.gameMode = 'challenge';
                        socketClient.startGame(gameType, true);
                    };
                }
            }
        });
    });

    // Rematch button
    const rematchBtn = document.getElementById('rematch-btn');
    if (rematchBtn) {
        rematchBtn.addEventListener('click', () => {
            logger.info('[GAME] Rematch clicked');
            if (roomState.currentGame) {
                socketClient.startGame(roomState.currentGame, false);
            }
        });
    }

    // Switch game button
    const switchBtn = document.getElementById('switch-game-btn');
    if (switchBtn) {
        switchBtn.addEventListener('click', () => {
            logger.info('[GAME] Switch game clicked');
            resetGameState();
            setPhase('game_selection');
        });
    }

    // Change game header button
    const changeHeaderBtn = document.getElementById('change-game-header-btn');
    if (changeHeaderBtn) {
        changeHeaderBtn.addEventListener('click', () => {
            logger.info('[GAME] Change game header clicked');
            resetGameState();
            setPhase('game_selection');
        });
    }

    // Chat
    const chatSendBtn = document.getElementById('chat-send-btn');
    if (chatSendBtn) {
        chatSendBtn.addEventListener('click', () => {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (message) {
                socketClient.sendChat(message);
                input.value = '';
            }
        });
    }

    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('chat-send-btn').click();
            }
        });
    }
}

// ============================================================================
// SOCKET LISTENERS
// ============================================================================

function setupSocketListeners() {
    socketClient.on('join_room_response', (data) => {
        logger.info('[SOCKET] Join room response:', data);
        if (data.success) {
            roomState.playerId = data.player_id;
            roomState.displayName = data.display_name;
            roomState.avatarColor = data.avatar_color;
            roomState.room = data.room;
            socketClient.setPlayerId(data.player_id);
            socketClient.roomId = ROOM_ID;

            updateRoomDisplay(data.room);
            
            if (data.room?.players && data.room.players.length >= 2 && roomState.phase === 'waiting') {
                logger.info('[SOCKET] 2 players detected, enabling game selection');
                setPhase('game_selection');
            }
        } else {
            logger.error('[SOCKET] Failed to join room:', data.error);
            alert('Could not join room: ' + (data.error || 'Unknown error'));
            setTimeout(() => {
                window.location.href = '/';
            }, 500);
        }
    });

    socketClient.on('player_joined', (data) => {
        logger.info('[SOCKET] Player joined:', data.display_name);
        roomState.room = data.room;
        updateRoomDisplay(data.room);
        
        if (data.room?.players && data.room.players.length >= 2 && roomState.phase === 'waiting') {
            logger.info('[SOCKET] 2 players detected, enabling game selection');
            setPhase('game_selection');
        }
    });

    socketClient.on('player_left', (data) => {
        logger.info('[SOCKET] Player left');
        roomState.room = data.room;
        updateRoomDisplay(data.room);
        
        if (data.room?.players && data.room.players.length < 2) {
            resetGameState();
            setPhase('waiting');
        }
    });

    socketClient.on('game_started', (data) => {
        logger.info('[SOCKET] Game started:', data.game_type);
        
        // FIX: Set currentGame BEFORE initializing UI
        roomState.currentGame = data.game_type;
        roomState.room = data.room;
        
        const modeModal = document.getElementById('mode-modal');
        if (modeModal && !modeModal.classList.contains('hidden')) {
            modeModal.classList.add('hidden');
        }
        
        setPhase('game');
        
        // Initialize game UI
        initializeGameUI(data.game_type, data.room);
    });

    socketClient.on('game_ended', (data) => {
        logger.info('[SOCKET] Game ended');
        
        if (data.room) {
            roomState.room = data.room;
            updateRoomDisplay(data.room);
        }
        
        setPhase('results');
        showGameResults(data.results);
    });

    socketClient.on('move_made', (data) => {
        logger.info('[SOCKET] Move made');
        if (data.room) {
            roomState.room = data.room;
        }
        
        if (roomState.gameManager && roomState.gameManager.onMoveMade) {
            roomState.gameManager.onMoveMade(data);
        }
    });

    socketClient.on('game_move_response', (data) => {
        if (roomState.gameManager && roomState.gameManager.onMoveResponse) {
            roomState.gameManager.onMoveResponse(data);
        }
    });

    socketClient.on('chat_message', (data) => {
        appendChatMessage(data);
    });
}

// ============================================================================
// RPS-SPECIFIC LISTENERS (NEW TIMER SYSTEM)
// ============================================================================

function setupRPSListeners() {
    socketClient.on('rps:tick', (data) => {
        // Timer tick from server
        if (roomState.gameManager && roomState.gameManager.onTick) {
            roomState.gameManager.onTick(data.remaining);
        }
    });

    socketClient.on('rps:new_round', (data) => {
        // Next round is starting
        logger.info('[RPS] New round starting');
        if (roomState.gameManager && roomState.gameManager.onNewRound) {
            roomState.gameManager.onNewRound(data);
        }
    });

    socketClient.on('rps:reveal_result', (data) => {
        // Show round result
        logger.info('[RPS] Reveal result');
        if (roomState.gameManager && roomState.gameManager.revealResult) {
            roomState.gameManager.revealResult(data);
        }
    });

    socketClient.on('rps:choose_response', (data) => {
        logger.info('[RPS] Choose response:', data);
    });

    socketClient.on('rps:choice_recorded', (data) => {
        // Another player made a choice
        logger.info('[RPS] Choice recorded from player:', data.player_id);
    });
}

// ============================================================================
// GAME UI INITIALIZATION
// ============================================================================

function initializeGameUI(gameType, room) {
    logger.info(`[GAME] Initializing game UI: ${gameType}`);

    // FIX: Ensure roomState.currentGame is set
    if (!roomState.currentGame) {
        logger.error('[GAME] ERROR: roomState.currentGame is null! Setting it...');
        roomState.currentGame = gameType;
    }

    const gameContainer = document.getElementById('game-container');
    if (!gameContainer) {
        logger.error('[GAME] No game-container element found');
        return;
    }

    // Get game class
    const GameClass = gameClasses[gameType];
    if (!GameClass) {
        logger.error(`[GAME] No game class for ${gameType}`);
        gameContainer.innerHTML = `<div class="text-red-500">Unknown game: ${gameType}</div>`;
        return;
    }

    // Create game instance with current roomState
    // FIX: Ensure roomState has valid currentGame before creating manager
    if (!roomState.currentGame) {
        roomState.currentGame = gameType;
    }

    try {
        roomState.gameManager = new GameClass(roomState);
        
        // Validate game manager was created
        if (!roomState.gameManager) {
            logger.error(`[GAME] Failed to create game manager for ${gameType}`);
            gameContainer.innerHTML = `<div class="text-red-500">Failed to initialize game</div>`;
            return;
        }

        roomState.gameManager.render(gameContainer);
        logger.info(`[GAME] Game UI initialized successfully for ${gameType}`);
    } catch (error) {
        logger.error(`[GAME] Error initializing game: ${error.message}`);
        gameContainer.innerHTML = `<div class="text-red-500">Error: ${error.message}</div>`;
    }
}

// ============================================================================
// PHASE MANAGEMENT
// ============================================================================

function setPhase(phase) {
    logger.info(`[PHASE] Setting phase to: ${phase}`);
    roomState.phase = phase;

    const waitingPhase = document.getElementById('phase-waiting');
    const selectionPhase = document.getElementById('phase-game-selection');
    const gamePhase = document.getElementById('phase-game');
    const resultsPhase = document.getElementById('phase-results');

    // Hide all phases
    [waitingPhase, selectionPhase, gamePhase, resultsPhase].forEach(el => {
        if (el) el.classList.add('hidden');
    });

    // Show current phase
    let phaseEl = null;
    if (phase === 'waiting') phaseEl = waitingPhase;
    else if (phase === 'game_selection') phaseEl = selectionPhase;
    else if (phase === 'game') phaseEl = gamePhase;
    else if (phase === 'results') phaseEl = resultsPhase;

    if (phaseEl) {
        phaseEl.classList.remove('hidden');
    }
}

// ============================================================================
// ROOM DISPLAY
// ============================================================================

function updateRoomDisplay(room) {
    roomState.room = room;
    
    const linkInput = document.getElementById('room-link-input');
    if (linkInput) {
        linkInput.value = window.location.href;
    }

    const playersList = document.getElementById('players-list');
    if (playersList && room?.players) {
        playersList.innerHTML = room.players
            .map((p, i) => `
                <div class="flex items-center justify-between">
                    <span class="text-sm">Player ${i + 1}</span>
                    <span class="text-xs text-slate-400">${p.display_name}</span>
                </div>
            `)
            .join('');
    }

    const scoreDisplay = document.getElementById('score-display');
    if (scoreDisplay && room?.current_game && room.player_scores) {
        const scores = room.player_scores;
        const scoreText = room.players
            .map((p, i) => `${p.display_name}: ${scores[p.player_id] || 0}`)
            .join(' - ');
        scoreDisplay.textContent = scoreText;
    }
}

// ============================================================================
// GAME RESULTS
// ============================================================================

function showGameResults(results) {
    const resultsContainer = document.getElementById('phase-results');
    if (!resultsContainer) return;

    const winner = results.winner === roomState.playerId;
    const resultsHTML = `
        <div class="text-center space-y-4">
            <div class="text-4xl font-bold">
                ${winner ? '🎉 You Won!' : '😅 You Lost!'}
            </div>
            <div class="text-lg font-semibold">
                Final Score
            </div>
            <div class="grid grid-cols-2 gap-4 text-lg">
                <div>
                    <div class="text-sm text-slate-400">You</div>
                    <div class="text-2xl font-bold">${results.scores[roomState.playerId] || 0}</div>
                </div>
                <div>
                    <div class="text-sm text-slate-400">Opponent</div>
                    <div class="text-2xl font-bold">
                        ${Object.entries(results.scores)
                            .filter(([pid]) => pid !== roomState.playerId)
                            .map(([, score]) => score)[0] || 0}
                    </div>
                </div>
            </div>
            <div class="flex gap-2 justify-center pt-4">
                <button id="rematch-btn" class="px-4 py-2 bg-blue-600 rounded hover:bg-blue-500">
                    Rematch
                </button>
                <button id="switch-game-btn" class="px-4 py-2 bg-slate-600 rounded hover:bg-slate-500">
                    Switch Game
                </button>
            </div>
        </div>
    `;

    resultsContainer.innerHTML = resultsHTML;

    document.getElementById('rematch-btn').addEventListener('click', () => {
        if (roomState.currentGame) {
            socketClient.startGame(roomState.currentGame, false);
        }
    });

    document.getElementById('switch-game-btn').addEventListener('click', () => {
        resetGameState();
        setPhase('game_selection');
    });
}

// ============================================================================
// HELPERS
// ============================================================================

function resetGameState() {
    roomState.currentGame = null;
    roomState.gameManager = null;
    roomState.gameMode = 'simple';
}

function appendChatMessage(data) {
    const chatBox = document.getElementById('chat-box');
    if (!chatBox) return;

    const msg = document.createElement('div');
    msg.className = 'text-xs text-slate-400 pb-1';
    msg.textContent = `${data.display_name}: ${data.message}`;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function generateDisplayName() {
    const adjectives = ['Happy', 'Clever', 'Quick', 'Bright', 'Witty'];
    const nouns = ['Tiger', 'Fox', 'Eagle', 'Shark', 'Falcon'];
    return adjectives[Math.floor(Math.random() * adjectives.length)] +
           nouns[Math.floor(Math.random() * nouns.length)];
}

function getRandomAvatarColor() {
    const colors = ['bg-red-500', 'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500'];
    return colors[Math.floor(Math.random() * colors.length)];
}
