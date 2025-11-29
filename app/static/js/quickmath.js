/**
 * PlaySync - Quick Math Duel
 */

class QuickMathGame {
    constructor() {
        this.question = null;
        this.answer = null;
    }

    render(container, gameData) {
        const stateData = gameData.state_data;
        this.question = stateData.question;
        
        container.innerHTML = `
            <div class="space-y-6">
                <div class="bg-slate-600 p-6 rounded-lg text-center">
                    <div class="text-sm text-slate-400 mb-2">Solve this:</div>
                    <div class="text-4xl md:text-5xl font-poppins font-bold text-teal-300 break-words">
                        ${this.question}
                    </div>
                </div>

                <div class="flex flex-col md:flex-row gap-3 md:gap-2">
                    <input 
                        type="number" 
                        id="math-answer-input" 
                        placeholder="Your answer" 
                        class="flex-1 bg-slate-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-lg"
                        autocomplete="off"
                    >
                    <button id="math-submit-btn" class="bg-green-500 hover:bg-green-600 text-white font-semibold px-8 py-3 rounded-lg transition-colors whitespace-nowrap">
                        Submit
                    </button>
                </div>

                <div id="math-status" class="text-center text-sm text-slate-400">
                    First correct answer wins!
                </div>
            </div>
        `;

        const input = document.getElementById('math-answer-input');
        const btn = document.getElementById('math-submit-btn');

        input.focus();

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                btn.click();
            }
        });

        btn.addEventListener('click', () => {
            const answer = input.value.trim();
            if (answer) {
                socketClient.submitMove({ answer: parseInt(answer) });
                input.disabled = true;
                btn.disabled = true;
            }
        });
    }

    onMoveResponse(data) {
        const statusDiv = document.getElementById('math-status');
        
        if (data.success) {
            const isCorrect = data.data?.correct;
            if (isCorrect) {
                statusDiv.textContent = '✓ Correct!';
                statusDiv.classList.add('text-green-400');
            } else {
                statusDiv.textContent = '✗ Wrong answer';
                statusDiv.classList.add('text-red-400');
            }
        }
    }

    onGameEnded(results) {
        const container = document.getElementById('game-container');
        const isWinner = results.winner === socketClient.playerId;
        
        container.innerHTML = `
            <div class="text-center space-y-4">
                <div class="text-4xl font-bold">
                    ${isWinner ? '🧠 Correct!' : '🤔 Better luck next time'}
                </div>
                <div class="text-lg font-semibold">
                    ${results.question} = <span class="text-teal-400">${results.correct_answer}</span>
                </div>
                <div class="text-sm text-slate-400">
                    ${results.result_type === 'first_correct' ? 'First correct wins!' : 'No one got it right'}
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

window.QuickMathGame = QuickMathGame;
