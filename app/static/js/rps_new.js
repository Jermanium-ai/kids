/**
 * PlaySync - Rock Paper Scissors Game (NEW TIMER-BASED SYSTEM)
 * Server-authoritative timer, no best-of-N, clean minimal UI
 */

class RockPaperScissorsGame {
    constructor(roomState) {
        this.roomState = roomState;
        this.myChoice = null;
        this.opponentChoice = null;
        this.timerRunning = false;
        this.currentTimer = null;
        this.gameContainer = null;
        this.isRevealing = false;
        
        // Ensure roomState has currentGame (fix for undefined crash)
        if (!roomState.currentGame) {
            console.warn('[RPS] WARNING: roomState.currentGame is undefined. Initializing...');
            roomState.currentGame = 'rps';
        }
    }

    render(container) {
        // Safety check: ensure we have valid game state
        if (!this.roomState || !this.roomState.currentGame) {
            console.error('[RPS] Cannot render: invalid roomState');
            container.innerHTML = '<div class="text-center text-red-500">Error: Invalid game state</div>';
            return;
        }

        this.gameContainer = container;

        container.innerHTML = `
            <div class="relative">
                <!-- Timer (top-right corner) -->
                <div class="absolute top-2 right-4 text-2xl font-bold text-slate-300 font-mono"
                     id="rps-timer">4</div>
                
                <!-- Game Card -->
                <div class="space-y-6 pt-8">
                    <!-- Choice Buttons -->
                    <div id="rps-choices-section" class="text-center">
                        <p class="text-sm text-slate-400 mb-4">Make your choice</p>
                        <div class="grid grid-cols-3 gap-3">
                            <button class="rps-choice-btn" data-choice="rock">
                                <div class="text-4xl">🪨</div>
                                <div class="text-xs mt-2 font-semibold">Rock</div>
                            </button>
                            <button class="rps-choice-btn" data-choice="paper">
                                <div class="text-4xl">📄</div>
                                <div class="text-xs mt-2 font-semibold">Paper</div>
                            </button>
                            <button class="rps-choice-btn" data-choice="scissors">
                                <div class="text-4xl">✂️</div>
                                <div class="text-xs mt-2 font-semibold">Scissors</div>
                            </button>
                        </div>
                    </div>

                    <!-- Results Section (hidden initially) -->
                    <div id="rps-results-section" class="hidden text-center">
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <div class="text-xs text-slate-400 mb-2">You</div>
                                <div class="text-5xl mb-3" id="rps-your-choice">?</div>
                                <div class="text-sm font-bold text-slate-300" id="rps-your-result">-</div>
                            </div>
                            <div>
                                <div class="text-xs text-slate-400 mb-2">Opponent</div>
                                <div class="text-5xl mb-3" id="rps-opp-choice">?</div>
                                <div class="text-sm font-bold text-slate-300" id="rps-opp-result">-</div>
                            </div>
                        </div>
                    </div>

                    <!-- Scores -->
                    <div class="text-center text-sm text-slate-400">
                        <span>You: <span id="rps-your-score" class="font-bold">0</span></span>
                        <span class="mx-2">|</span>
                        <span>Opponent: <span id="rps-opp-score" class="font-bold">0</span></span>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
        logger.info('[RPS] Game rendered successfully');
    }

    attachEventListeners() {
        document.querySelectorAll('.rps-choice-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const choice = e.currentTarget.dataset.choice;
                this.submitChoice(choice);
            });
        });
    }

    submitChoice(choice) {
        if (this.isRevealing) {
            return; // Don't accept choices while showing results
        }

        if (!this.timerRunning) {
            return; // Don't accept choices when timer is not running
        }

        this.myChoice = choice;

        // Visual feedback: highlight chosen button
        document.querySelectorAll('.rps-choice-btn').forEach(btn => {
            if (btn.dataset.choice === choice) {
                btn.classList.add('ring-2', 'ring-yellow-400');
            }
        });

        // Send to server
        socketClient.emit('rps:choose', {
            room_id: this.roomState.roomId,
            choice: choice
        });

        logger.info(`[RPS] Choice submitted: ${choice}`);
    }

    startRound() {
        this.myChoice = null;
        this.opponentChoice = null;
        this.isRevealing = false;
        this.timerRunning = true;

        // Show choices section, hide results
        document.getElementById('rps-choices-section').classList.remove('hidden');
        document.getElementById('rps-results-section').classList.add('hidden');

        // Enable all buttons
        document.querySelectorAll('.rps-choice-btn').forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('ring-2', 'ring-yellow-400', 'opacity-50');
        });

        // Clear timer display (will be updated by tick events)
        document.getElementById('rps-timer').textContent = '4';

        logger.info('[RPS] Round started');
    }

    onTick(remaining) {
        // Update timer display
        const timerEl = document.getElementById('rps-timer');
        if (timerEl) {
            timerEl.textContent = remaining;
        }
    }

    revealResult(data) {
        this.isRevealing = true;
        this.timerRunning = false;

        // Hide choices, show results
        document.getElementById('rps-choices-section').classList.add('hidden');
        document.getElementById('rps-results-section').classList.remove('hidden');
        document.getElementById('rps-timer').textContent = ''; // Hide timer during reveal

        // Disable all buttons
        document.querySelectorAll('.rps-choice-btn').forEach(btn => btn.disabled = true);

        const choiceEmoji = {
            rock: '🪨',
            paper: '📄',
            scissors: '✂️',
            none: '❌'
        };

        // Determine player positions
        const players = this.roomState.room?.players || [];
        const isPlayer1 = players.length > 0 && players[0].player_id === socketClient.playerId;

        const p1_choice = data.p1_choice;
        const p2_choice = data.p2_choice;
        const winner = data.winner;

        // Map to "you" and "opponent"
        let yourChoice, oppChoice;
        if (isPlayer1) {
            yourChoice = p1_choice;
            oppChoice = p2_choice;
        } else {
            yourChoice = p2_choice;
            oppChoice = p1_choice;
        }

        // Display choices
        document.getElementById('rps-your-choice').textContent = choiceEmoji[yourChoice] || '?';
        document.getElementById('rps-opp-choice').textContent = choiceEmoji[oppChoice] || '?';

        // Display result
        let yourResult, oppResult;
        if (winner === 'draw') {
            yourResult = 'Draw';
            oppResult = 'Draw';
        } else if (
            (isPlayer1 && winner === 'player1') ||
            (!isPlayer1 && winner === 'player2')
        ) {
            yourResult = '✓ Win';
            oppResult = '✗ Loss';
        } else {
            yourResult = '✗ Loss';
            oppResult = '✓ Win';
        }

        document.getElementById('rps-your-result').textContent = yourResult;
        document.getElementById('rps-opp-result').textContent = oppResult;

        // Update scores
        const scores = data.scores || {};
        if (isPlayer1) {
            document.getElementById('rps-your-score').textContent = scores[players[0]?.player_id] || 0;
            document.getElementById('rps-opp-score').textContent = scores[players[1]?.player_id] || 0;
        } else {
            document.getElementById('rps-your-score').textContent = scores[players[1]?.player_id] || 0;
            document.getElementById('rps-opp-score').textContent = scores[players[0]?.player_id] || 0;
        }

        logger.info('[RPS] Result revealed');
    }

    onNewRound(data) {
        // Called when next round is about to start
        this.startRound();
    }

    stop() {
        this.timerRunning = false;
        this.myChoice = null;
        this.opponentChoice = null;
    }
}

window.RockPaperScissorsGame = RockPaperScissorsGame;
