/**
 * PlaySync - Reaction Time Duel
 */

class ReactionTimeGame {
    constructor() {
        this.readyTime = null;
        this.tapTime = null;
        this.isReady = false;
        this.canTap = false;
    }

    render(container, gameData) {
        const stateData = gameData.state_data;
        this.isReady = stateData.ready;
        
        container.innerHTML = `
            <div class="space-y-6 text-center">
                <div id="reaction-status" class="text-4xl font-bold font-poppins">
                    ${this.isReady ? '🎯 GET READY!' : '⏳ Preparing...'}
                </div>
                
                <button id="reaction-tap-btn" class="w-full h-32 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 rounded-xl font-poppins text-2xl font-bold transition-all transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">
                    TAP WHEN READY
                </button>
                
                <div id="reaction-message" class="text-sm text-slate-400">
                    Click TAP when the screen turns green
                </div>
            </div>
        `;

        const tapBtn = document.getElementById('reaction-tap-btn');
        
        // Start countdown if not ready yet
        if (!this.isReady) {
            tapBtn.disabled = true;
            setTimeout(() => {
                this.startReady(container);
            }, 1000 + Math.random() * 2000); // 1-3 second random delay
        } else {
            tapBtn.disabled = false;
            tapBtn.classList.add('ring-4', 'ring-green-400', 'animate-pulse');
            document.getElementById('reaction-status').textContent = '🎯 NOW!';
        }

        tapBtn.addEventListener('click', () => {
            this.tapReaction(container);
        });
    }

    startReady(container) {
        this.isReady = true;
        const statusDiv = document.getElementById('reaction-status');
        const tapBtn = document.getElementById('reaction-tap-btn');
        
        statusDiv.textContent = '🎯 NOW!';
        statusDiv.classList.add('text-green-400');
        tapBtn.disabled = false;
        tapBtn.classList.add('ring-4', 'ring-green-400', 'animate-pulse');
        
        // Haptic feedback
        navigator.vibrate?.(50);
    }

    tapReaction(container) {
        const tapBtn = document.getElementById('reaction-tap-btn');
        tapBtn.disabled = true;
        
        socketClient.submitMove({});
    }

    onMoveResponse(data) {
        const container = document.getElementById('game-container');
        const statusDiv = document.getElementById('reaction-status');
        const tapBtn = document.getElementById('reaction-tap-btn');
        
        if (data.success) {
            const reactionMs = data.data?.reaction_ms;
            statusDiv.textContent = `⚡ ${reactionMs}ms`;
            statusDiv.classList.add('text-green-400');
            statusDiv.classList.remove('text-orange-400');
            
            // Haptic feedback
            navigator.vibrate?.([50, 50, 50]);
        } else if (data.data?.early_tap) {
            statusDiv.textContent = '⚠️ Too Early!';
            statusDiv.classList.add('text-red-400');
            tapBtn.classList.add('animate-shake');
            
            // Haptic feedback
            navigator.vibrate?.(200);
        }
    }

    onGameEnded(results) {
        const container = document.getElementById('game-container');
        const isWinner = results.winner === socketClient.playerId;
        
        const times = results.reaction_times;
        const myTime = times[socketClient.playerId];
        
        container.innerHTML = `
            <div class="text-center space-y-4">
                <div class="text-4xl font-bold">
                    ${isWinner ? '🏆 Fastest!' : '🥈 Good try!'}
                </div>
                <div class="space-y-2 text-lg">
                    <div>Your time: <span class="font-bold text-teal-400">${myTime}ms</span></div>
                    <div>Opponent: <span class="font-bold text-cyan-400">${Object.values(times).find(t => t !== myTime) || 'N/A'}ms</span></div>
                </div>
            </div>
        `;
        
        // Show Truth or Dare if in Challenge mode and this player lost
        const gameMode = this.gameMode || roomState.gameMode || 'simple';
        if (gameMode === 'challenge' && !isWinner) {
            setTimeout(() => {
                const loserName = roomState.displayName;
                const todModal = new TruthOrDareModal();
                todModal.showChallenge(loserName, true);
            }, 1000);
        }
    }
}

window.ReactionTimeGame = ReactionTimeGame;
