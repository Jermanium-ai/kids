/**
 * PlaySync - Rock Paper Scissors Game
 */

class RockPaperScissorsGame {
    constructor() {
        this.myChoice = null;
        this.opponentChoice = null;
        this.roundResults = [];
        this._lastRoundShown = 0; // track how many rounds we've displayed
        this.currentRound = 1; // current round for move submissions
    }

    render(container) {
        container.innerHTML = `
            <div class="space-y-6">
                <div class="text-center">
                    <p class="text-sm text-slate-400 mb-4">Make your choice</p>
                    <div class="grid grid-cols-3 gap-3">
                        <button class="rps-choice-btn bg-slate-600 hover:bg-slate-500 p-4 rounded-lg transition-all transform hover:scale-110" data-choice="rock">
                            <div class="text-3xl">🪨</div>
                            <div class="text-xs mt-2">Rock</div>
                        </button>
                        <button class="rps-choice-btn bg-slate-600 hover:bg-slate-500 p-4 rounded-lg transition-all transform hover:scale-110" data-choice="paper">
                            <div class="text-3xl">📄</div>
                            <div class="text-xs mt-2">Paper</div>
                        </button>
                        <button class="rps-choice-btn bg-slate-600 hover:bg-slate-500 p-4 rounded-lg transition-all transform hover:scale-110" data-choice="scissors">
                            <div class="text-3xl">✂️</div>
                            <div class="text-xs mt-2">Scissors</div>
                        </button>
                    </div>
                </div>

                <div id="rps-status" class="text-center text-sm text-slate-400">
                    Waiting for opponent...
                </div>

                <div id="rps-results" class="hidden">
                    <div class="grid grid-cols-2 gap-4 text-center">
                        <div>
                            <div class="text-xs text-slate-400 mb-2">You</div>
                            <div class="text-2xl mb-2" id="rps-your-choice"></div>
                            <div class="text-sm font-semibold" id="rps-your-result"></div>
                        </div>
                        <div>
                            <div class="text-xs text-slate-400 mb-2">Opponent</div>
                            <div class="text-2xl mb-2" id="rps-opp-choice"></div>
                            <div class="text-sm font-semibold" id="rps-opp-result"></div>
                        </div>
                    </div>
                </div>
            </div>
                `;

        // Initialize current round from passed data if available
        const gameData = window.roomState.currentGame ? (window.roomState.currentGame) : null;
        this.currentRound = gameData?.state_data?.current_round || this.currentRound;

        // Attach choice handlers
        container.querySelectorAll('.rps-choice-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const choice = e.currentTarget.dataset.choice;
                this.submitChoice(choice);
            });
        });
    }

    submitChoice(choice) {
        this.myChoice = choice;

        // Disable buttons after choice
        document.querySelectorAll('.rps-choice-btn').forEach(btn => {
            btn.disabled = true;
            btn.classList.remove('hover:bg-slate-500', 'hover:scale-110');
        });

        socketClient.submitMove({ choice: choice, round: this.currentRound });
    }

    onMoveResponse(data) {
        if (data.success) {
            document.getElementById('rps-status').textContent = 'Waiting for opponent...';
        }
    }

    onMoveMade(data) {
        // Update scores in the room display
        if (data.room) {
            updateRoomDisplay(data.room);
        }
        
        // Check if game is still ongoing
        const gameData = data.room?.current_game;
        // Reflect current submissions (if only one player has submitted)
        const currentChoices = gameData?.state_data?.choices || {};
        const myId = socketClient.playerId;
        if (myId) {
            const mySubmitted = Boolean(currentChoices[myId]);
            const buttons = document.querySelectorAll('.rps-choice-btn');
            // If we've already submitted for this round, disable buttons until next round
            buttons.forEach(btn => btn.disabled = mySubmitted);
            const statusDiv = document.getElementById('rps-status');
            if (mySubmitted) {
                statusDiv.textContent = 'Waiting for opponent...';
            }
        }

        const rounds = gameData?.state_data?.rounds || [];
            if (rounds.length > this._lastRoundShown) {
            const newLastRound = rounds[rounds.length - 1];
            // Map p1/p2 choices to the current player vs opponent so UI correctly shows your choice
            const players = data.room.players || [];
            const isPlayerOne = players.length > 0 && players[0].player_id === socketClient.playerId;
            // Determine client and opponent choice by mapping p1/p2 to player positions
            if (isPlayerOne) {
                lastRound.my_choice = lastRound.p1_choice;
                lastRound.opp_choice = lastRound.p2_choice;
            } else {
                lastRound.my_choice = lastRound.p2_choice;
                lastRound.opp_choice = lastRound.p1_choice;
            }
            if (newLastRound && newLastRound.p1_choice && newLastRound.p2_choice) {
                this.displayRound(newLastRound);
                this._lastRoundShown = rounds.length;
            }
            } else {
                // Update current round if server signals it
                this.currentRound = data.room?.current_game?.state_data?.current_round || this.currentRound;
        }
    }

    displayRound(round) {
        const statusDiv = document.getElementById('rps-status');
        const resultsDiv = document.getElementById('rps-results');

        statusDiv.classList.add('hidden');
        resultsDiv.classList.remove('hidden');

        const choiceEmoji = {
            rock: '🪨',
            paper: '📄',
            scissors: '✂️'
        };

        document.getElementById('rps-your-choice').textContent = choiceEmoji[round.my_choice];
        document.getElementById('rps-opp-choice').textContent = choiceEmoji[round.opp_choice];

        // Determine if we won or lost
        const isWin = round.winner === socketClient.playerId;
        const isTie = round.winner === null;

        if (isTie) {
            document.getElementById('rps-your-result').textContent = 'Tie';
            document.getElementById('rps-opp-result').textContent = 'Tie';
        } else {
            document.getElementById('rps-your-result').textContent = isWin ? '✓ Win' : '✗ Loss';
            document.getElementById('rps-opp-result').textContent = isWin ? '✗ Loss' : '✓ Win';
        }
        
        // After 2 seconds, reset UI for next round if game is still ongoing
        setTimeout(() => {
            this.resetForNextRound();
        }, 2000);
    }
    
    resetForNextRound() {
        const statusDiv = document.getElementById('rps-status');
        const resultsDiv = document.getElementById('rps-results');
        const choiceButtons = document.querySelectorAll('.rps-choice-btn');
        
        // Reset UI
        statusDiv.classList.remove('hidden');
        resultsDiv.classList.add('hidden');
        statusDiv.textContent = 'Make your choice';
        
        // Reset stored choices
        this.myChoice = null;
        this.opponentChoice = null;
        // Reset lastRoundShown if the server moved to a new current round
        // Otherwise if rounds array expanded, the display logic uses _lastRoundShown
        // to decide when to show a completed round's results
        // Do not reset to 0, maintain current count to avoid re-showing old rounds
        // Re-enable buttons
        choiceButtons.forEach(btn => {
            btn.disabled = false;
            btn.classList.add('hover:bg-slate-500', 'hover:scale-110');
        });
    }

    onGameEnded(results) {
        const container = document.getElementById('game-container');
        const winner = results.winner === socketClient.playerId;
        
        container.innerHTML = `
            <div class="text-center space-y-4">
                <div class="text-4xl font-bold">
                    ${winner ? '🎉 You Won!' : '😅 You Lost'}
                </div>
                <div class="text-2xl">Best of ${results.best_of}</div>
                <div class="grid grid-cols-2 gap-4 text-lg font-semibold">
                    <div>You: ${results.scores[socketClient.playerId] || 0}</div>
                    <div>Opponent: ${results.scores[Object.keys(results.scores).find(k => k !== socketClient.playerId)] || 0}</div>
                </div>
            </div>
        `;
        
        // Show Truth or Dare if in Challenge mode and this player lost
        const gameMode = this.gameMode || roomState.gameMode || 'simple';
        console.log('[RPS] onGameEnded - gameMode:', gameMode, 'winner:', winner);
        if (gameMode === 'challenge' && !winner) {
            console.log('[RPS] Showing Truth or Dare for loser');
            setTimeout(() => {
                const loserName = roomState.displayName;
                const todModal = new TruthOrDareModal();
                todModal.showChallenge(loserName, true);
            }, 1000);
        }
    }
}

window.RockPaperScissorsGame = RockPaperScissorsGame;
