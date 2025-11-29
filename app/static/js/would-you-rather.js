/**
 * PlaySync - Would You Rather Game
 */

class WouldYouRatherGame {
    constructor() {
        this.currentRound = 1;
        this.maxRounds = 3;
        this.question = null;
    }

    render(container, gameData) {
        const stateData = gameData.state_data;
        this.question = stateData.question;
        this.currentRound = stateData.round;
        this.maxRounds = stateData.max_rounds;
        const roundsHistory = stateData.rounds || [];

        container.innerHTML = `
            <div class="space-y-6">
                <div class="text-center">
                    <div class="text-xs text-slate-400 mb-4">Round ${this.currentRound} of ${this.maxRounds}</div>
                    <div class="text-lg font-poppins font-bold mb-6">Would you rather...</div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <button class="wyr-choice-btn bg-gradient-to-b from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 p-4 rounded-xl transition-all transform hover:scale-105 active:scale-95" data-choice="a">
                        <div class="text-sm font-semibold">${this.question.a}</div>
                    </button>
                    <button class="wyr-choice-btn bg-gradient-to-b from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 p-4 rounded-xl transition-all transform hover:scale-105 active:scale-95" data-choice="b">
                        <div class="text-sm font-semibold">${this.question.b}</div>
                    </button>
                </div>

                <div id="wyr-status" class="text-center text-sm text-slate-400">
                    Make your choice
                </div>
                <div id="wyr-history" class="mt-4 text-sm text-slate-400">
                    ${roundsHistory.length ? `<strong>Previous rounds:</strong> ${roundsHistory.map(r => `<div>Round ${r.round}: ${r.question.a} / ${r.question.b}</div>`).join('')}` : ''}
                </div>
            </div>
        `;

        container.querySelectorAll('.wyr-choice-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const choice = e.currentTarget.dataset.choice;
                this.submitChoice(choice, container);
            });
        });
    }

    submitChoice(choice, container) {
        // Disable buttons
        container.querySelectorAll('.wyr-choice-btn').forEach(btn => {
            btn.disabled = true;
        });

        socketClient.submitMove({ choice: choice });

        document.getElementById('wyr-status').textContent = 'Waiting for opponent...';
    }

    onMoveMade(data) {
        // Update if new round available
        const gameData = data.room?.current_game;
        if (gameData) {
            const container = document.getElementById('game-container');
            
            // Re-render when round advances or the question changes
            if (gameData.state_data.round > this.currentRound || gameData.state_data.question !== this.question) {
                setTimeout(() => {
                    this.render(container, gameData);
                }, 500);
            }
        }
    }

    onGameEnded(results) {
        const container = document.getElementById('game-container');
        
        container.innerHTML = `
            <div class="text-center space-y-4">
                <div class="text-3xl font-bold font-poppins">
                    Game Complete!
                </div>
                <div class="text-lg">
                    You played ${results.max_rounds} rounds and compared your preferences with your opponent.
                </div>
                <div class="text-sm text-slate-400">
                    See how compatible you are!
                </div>
            </div>
        `;
        
        // Show Truth or Dare if in Challenge mode (random for this game since it has no loser)
        const gameMode = this.gameMode || roomState.gameMode || 'simple';
        if (gameMode === 'challenge' && Math.random() > 0.5) {
            setTimeout(() => {
                const loserName = roomState.displayName;
                const todModal = new TruthOrDareModal();
                todModal.showChallenge(loserName, true);
            }, 1000);
        }
    }
}

window.WouldYouRatherGame = WouldYouRatherGame;
