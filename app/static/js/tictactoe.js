/**
 * PlaySync - Tic Tac Toe Game
 */

class TicTacToeGame {
    constructor() {
        this.board = Array(9).fill('');
        this.mySymbol = null;
        this.currentPlayer = null;
    }

    render(container, gameData) {
        // Determine our symbol
        const state = gameData.state_data || {};
        const boardStates = state.board || Array(9).fill('');
        const playerSymbols = state.player_to_symbol || {};
        const currentPlayer = state.current_player;
        
        if (!playerSymbols[socketClient.playerId]) {
            console.error('Player symbol not found in game data');
            container.innerHTML = '<div>Error: Game not properly initialized. Please start again.</div>';
            return;
        }
        
        // Store state for later reference
        this.playerSymbol = playerSymbols[socketClient.playerId];
        this.boardState = [...boardStates];
        this.playerSymbols = playerSymbols;
        this.currentPlayer = currentPlayer;
        
        // Determine status message
        const isMyTurn = currentPlayer === socketClient.playerId;
        const statusMessage = isMyTurn ? 'Your Turn' : 'Waiting for opponent...';
        
        container.innerHTML = `
            <div class="space-y-4">
                <div class="text-center">
                    <div class="text-sm text-slate-400 mb-2">
                        Playing as: ${this.playerSymbol === 'X' ? '❌ X' : '⭕ O'}
                    </div>
                </div>
                <div class="grid grid-cols-3 gap-2 mx-auto w-fit" id="ttt-board">
                    ${Array(9).fill(0).map((_, i) => {
                        const symbol = boardStates[i];
                        const display = symbol ? (symbol === 'X' ? '❌' : '⭕') : '';
                        return `
                        <button class="ttt-cell bg-slate-600 hover:bg-slate-500 w-16 h-16 rounded-lg font-poppins text-2xl font-bold transition-all"
                                data-position="${i}"
                                data-symbol="${symbol || ''}"
                                ${symbol ? 'disabled' : ''}
                                >
                            ${display}
                        </button>
                    `;
                    }).join('')}
                </div>
                <div id="ttt-status" class="text-center text-xs text-slate-400 mt-3">
                    ${statusMessage}
                </div>
            </div>
        `;

        // Attach handlers
        container.querySelectorAll('.ttt-cell').forEach(cell => {
            const position = parseInt(cell.dataset.position);
            const symbol = boardStates[position];
            
            // Style filled cells
            if (symbol) {
                cell.disabled = true;
                cell.classList.add('opacity-60', 'cursor-not-allowed');
            }
            
            cell.addEventListener('click', (e) => {
                if (!symbol) {  // Only allow click if cell is empty
                    this.submitMove(position, container);
                }
            });
        });
    }

    submitMove(position, container) {
        socketClient.submitMove({ position: position });
    }

    updateBoardDisplay(container, board, symbols) {
        const cells = container.querySelectorAll('.ttt-cell');
        cells.forEach((cell, idx) => {
            const symbol = board[idx];
            cell.dataset.symbol = symbol || '';
            cell.textContent = symbol === 'X' ? '❌' : (symbol === 'O' ? '⭕' : '');
            cell.disabled = symbol !== '';
            
            // Style filled cells
            if (symbol) {
                cell.classList.add('opacity-60', 'cursor-not-allowed');
            } else {
                cell.classList.remove('opacity-60', 'cursor-not-allowed');
            }
        });
    }

    onMoveResponse(data) {
        // Board will be updated by move_made event
    }

    onMoveMade(data) {
        console.log('[TicTacToe] Move made event received');
        const gameData = data.room?.current_game;
        if (gameData && gameData.state_data && gameData.state_data.board) {
            console.log('[TicTacToe] Updating board with state:', gameData.state_data.board);
            const container = document.getElementById('game-container');
            if (container) {
                // Update board display with new moves
                const board = gameData.state_data.board;
                const cells = container.querySelectorAll('.ttt-cell');
                const statusEl = document.getElementById('ttt-status');
                
                cells.forEach((cell, idx) => {
                    const symbol = board[idx];
                    const oldSymbol = cell.dataset.symbol;
                    
                    // Only update if changed
                    if (oldSymbol !== (symbol || '')) {
                        cell.dataset.symbol = symbol || '';
                        cell.textContent = symbol === 'X' ? '❌' : (symbol === 'O' ? '⭕' : '');
                        cell.disabled = symbol !== '';
                        
                        // Add styling for filled cells
                        if (symbol) {
                            cell.classList.add('opacity-60', 'cursor-not-allowed');
                        } else {
                            cell.classList.remove('opacity-60', 'cursor-not-allowed');
                        }
                    }
                });
                
                // Update turn status with simple text (no emoji)
                if (statusEl) {
                    const currentPlayer = gameData.state_data.current_player;
                    const isMyTurn = currentPlayer === socketClient.playerId;
                    const statusMessage = isMyTurn ? 'Your Turn' : 'Waiting for opponent...';
                    statusEl.textContent = statusMessage;
                    statusEl.className = 'text-center text-xs text-slate-400 mt-3';
                }
            }
        }
    }

    onGameEnded(results) {
        const container = document.getElementById('game-container');
        const winner = results.winner === socketClient.playerId;
        
        container.innerHTML = `
            <div class="text-center space-y-4">
                <div class="text-4xl font-bold">
                    ${winner ? '🎉 You Won!' : (results.result === 'draw' ? '🤝 Draw!' : '😅 You Lost')}
                </div>
                ${results.result === 'draw' ? '<div class="text-xl">Great match!</div>' : ''}
            </div>
        `;
        
        // Show Truth or Dare if in Challenge mode and this player lost
        const gameMode = this.gameMode || roomState.gameMode || 'simple';
        if (gameMode === 'challenge' && !winner && results.result !== 'draw') {
            setTimeout(() => {
                const loserName = roomState.displayName;
                const todModal = new TruthOrDareModal();
                todModal.showChallenge(loserName, true);
            }, 1000);
        }
    }
}

window.TicTacToeGame = TicTacToeGame;
