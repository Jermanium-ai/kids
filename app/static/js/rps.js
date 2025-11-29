/**
 * PlaySync - Rock Paper Scissors Timer Game
 * 4-second countdown per round with server-authoritative timing
 */

class RockPaperScissorsGame {
    constructor(roomState) {
        this.roomState = roomState;
        this.myChoice = null;
        this.opponentChoice = null;
        this.gameRunning = false;
        this.timerRunning = false;
        this.currentRound = 1;
        this.myScore = 0;
        this.opponentScore = 0;
        this.scores = {};
        this.roundHistory = [];
    }

    render(container) {
        container.innerHTML = `
            <div class="space-y-4">
                <!-- Timer in top-right -->
                <div class="flex justify-between items-center mb-6">
                    <div class="text-sm text-slate-400">Round <span id="rps-round">1</span></div>
                    <div class="flex items-center gap-4">
                        <div class="text-sm text-slate-400">Score</div>
                        <div class="flex gap-4 text-sm font-semibold">
                            <div id="rps-my-score">0</div>
                            <div class="text-slate-600">-</div>
                            <div id="rps-opp-score">0</div>
                        </div>
                        <div id="rps-timer" class="text-right font-mono text-2xl font-bold text-teal-400 min-w-16">
                            --
                        </div>
                    </div>
                </div>

                <!-- Choice Buttons -->
                <div class="text-center">
                    <p class="text-xs text-slate-400 mb-4">Choose in {{ timer }}</p>
                    <div class="grid grid-cols-3 gap-3">
                        <button class="rps-choice-btn group" data-choice="rock">
                            <div class="bg-slate-700 group-hover:bg-slate-600 group-disabled:bg-slate-800 
                                        p-4 rounded-lg transition-all transform group-hover:scale-105 
                                        group-disabled:scale-100 group-disabled:opacity-50">
                                <div class="text-4xl">🪨</div>
                            </div>
                            <div class="text-xs mt-2 text-slate-400 group-disabled:text-slate-500">Rock</div>
                        </button>

                        <button class="rps-choice-btn group" data-choice="paper">
                            <div class="bg-slate-700 group-hover:bg-slate-600 group-disabled:bg-slate-800 
                                        p-4 rounded-lg transition-all transform group-hover:scale-105 
                                        group-disabled:scale-100 group-disabled:opacity-50">
                                <div class="text-4xl">📄</div>
                            </div>
                            <div class="text-xs mt-2 text-slate-400 group-disabled:text-slate-500">Paper</div>
                        </button>

                        <button class="rps-choice-btn group" data-choice="scissors">
                            <div class="bg-slate-700 group-hover:bg-slate-600 group-disabled:bg-slate-800 
                                        p-4 rounded-lg transition-all transform group-hover:scale-105 
                                        group-disabled:scale-100 group-disabled:opacity-50">
                                <div class="text-4xl">✂️</div>
                            </div>
                            <div class="text-xs mt-2 text-slate-400 group-disabled:text-slate-500">Scissors</div>
                        </button>
                    </div>
                </div>

                <!-- Result Display (initially hidden) -->
                <div id="rps-result-section" class="hidden mt-6 p-4 bg-slate-800 rounded-lg">
                    <div class="grid grid-cols-2 gap-6 text-center">
                        <!-- Player 1 -->
                        <div>
                            <div class="text-xs text-slate-400 mb-2">You</div>
                            <div class="text-5xl mb-3" id="rps-my-choice-display">?</div>
                            <div class="text-sm font-semibold" id="rps-my-result">--</div>
                        </div>

                        <!-- Player 2 -->
                        <div>
                            <div class="text-xs text-slate-400 mb-2">Opponent</div>
                            <div class="text-5xl mb-3" id="rps-opp-choice-display">?</div>
                            <div class="text-sm font-semibold" id="rps-opp-result">--</div>
                        </div>
                    </div>

                    <!-- Center result text -->
                    <div class="text-center mt-4 text-lg font-bold" id="rps-round-result">
                        Result
                    </div>
                </div>

                <!-- Game Status -->
                <div class="text-center text-sm text-slate-400 mt-4">
                    <div id="rps-status">Waiting for server...</div>
                </div>
            </div>
        `;

        // Attach event listeners
        this.attachListeners();
        this.setupSocketListeners();
    }

    attachListeners() {
        const container = document.querySelector('.game-container');
        if (!container) return;

        container.querySelectorAll('.rps-choice-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const choice = e.currentTarget.dataset.choice;
                this.submitChoice(choice);
            });
        });
    }

    setupSocketListeners() {
        // RPS Timer events
        socketClient.on('rps_round_update', (data) => this.onRoundUpdate(data));
        socketClient.on('rps_timer_tick', (data) => this.onTimerTick(data));
        socketClient.on('rps_player_ready', (data) => this.onPlayerReady(data));
        socketClient.on('rps_result', (data) => this.onResult(data));
        socketClient.on('rps_choice_response', (data) => this.onChoiceResponse(data));
    }

    submitChoice(choice) {
        if (!this.timerRunning) {
            console.warn('[RPS] Timer not running, cannot submit choice');
            return;
        }

        console.log(`[RPS] Submitting choice: ${choice}`);
        this.myChoice = choice;

        // Highlight the selected button
        document.querySelectorAll('.rps-choice-btn').forEach(btn => {
            const isSelected = btn.dataset.choice === choice;
            btn.classList.toggle('ring-2', isSelected);
            btn.classList.toggle('ring-teal-400', isSelected);
        });

        // Send to server
        socketClient.socket.emit('rps_choice', {
            room_id: socketClient.roomId,
            choice: choice
        });
    }

    onRoundUpdate(data) {
        console.log('[RPS] Round update:', data);
        
        this.currentRound = data.round;
        this.scores = data.scores || {};
        
        // Update round display
        document.getElementById('rps-round').textContent = this.currentRound;
        
        // Update scores
        const playerIds = Object.keys(this.scores).sort();
        if (playerIds.length >= 2) {
            document.getElementById('rps-my-score').textContent = this.scores[playerIds[0]] || 0;
            document.getElementById('rps-opp-score').textContent = this.scores[playerIds[1]] || 0;
        }

        // Hide previous result and reset UI
        document.getElementById('rps-result-section').classList.add('hidden');
        document.querySelectorAll('.rps-choice-btn').forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('ring-2', 'ring-teal-400');
        });

        this.myChoice = null;
        this.timerRunning = true;
        document.getElementById('rps-status').textContent = 'Make your choice!';
    }

    onTimerTick(data) {
        const remaining = data.remaining;
        console.log(`[RPS] Timer tick: ${remaining}s`);

        // Update timer display
        const timerEl = document.getElementById('rps-timer');
        if (timerEl) {
            timerEl.textContent = remaining;

            // Pulse animation when 2 seconds or less
            if (remaining <= 2) {
                timerEl.classList.add('animate-pulse');
            } else {
                timerEl.classList.remove('animate-pulse');
            }
        }

        // Disable buttons when timer runs out
        if (remaining === 0) {
            this.timerRunning = false;
            document.querySelectorAll('.rps-choice-btn').forEach(btn => {
                btn.disabled = true;
            });
            document.getElementById('rps-status').textContent = 'Revealing result...';
        }
    }

    onPlayerReady(data) {
        console.log('[RPS] Player ready:', data);
        // Player submitted a choice
        // Could show indicator here
    }

    onResult(data) {
        console.log('[RPS] Result:', data);

        this.timerRunning = false;
        const result = data.result;
        const p1Choice = data.p1_choice;
        const p2Choice = data.p2_choice;
        const winner = data.winner;
        const reason = data.reason;

        // Map emoji
        const choiceEmoji = {
            'rock': '🪨',
            'paper': '📄',
            'scissors': '✂️',
            null: '?'
        };

        // Show result section
        const resultSection = document.getElementById('rps-result-section');
        resultSection.classList.remove('hidden');

        // Show choices
        document.getElementById('rps-my-choice-display').textContent = choiceEmoji[p1Choice] || '?';
        document.getElementById('rps-opp-choice-display').textContent = choiceEmoji[p2Choice] || '?';

        // Determine result text
        let resultText = '';
        let resultColor = 'text-slate-400';

        if (result === 'tie') {
            resultText = "It's a Tie!";
            resultColor = 'text-yellow-400';
        } else if (result === 'p1_win') {
            // Assume we're player 1
            resultText = 'You Won!';
            resultColor = 'text-green-400';
        } else {
            resultText = 'You Lost!';
            resultColor = 'text-red-400';
        }

        const roundResultEl = document.getElementById('rps-round-result');
        roundResultEl.textContent = resultText;
        roundResultEl.className = `text-center mt-4 text-lg font-bold ${resultColor}`;

        // Update final scores
        const playerIds = Object.keys(data.scores).sort();
        if (playerIds.length >= 2) {
            document.getElementById('rps-my-score').textContent = data.scores[playerIds[0]] || 0;
            document.getElementById('rps-opp-score').textContent = data.scores[playerIds[1]] || 0;
        }

        document.getElementById('rps-status').textContent = `Next round in 1.5 seconds...`;

        // Store in history
        this.roundHistory.push({
            round: data.round,
            result: result,
            reason: reason,
            scores: data.scores
        });
    }

    onChoiceResponse(data) {
        if (data.success) {
            console.log(`[RPS] Choice confirmed: ${data.choice}`);
        } else {
            console.error('[RPS] Choice failed:', data.error);
        }
    }
}

window.RockPaperScissorsGame = RockPaperScissorsGame;
