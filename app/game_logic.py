"""
PlaySync - Game Logic Modules
Server-side game state management and validation
"""

import random
import time
import threading
from enum import Enum

class GameManager:
    """Base class for game managers - handles game-specific logic"""
    
    def __init__(self, room):
        self.room = room
    
    def start(self):
        """Initialize game"""
        pass
    
    def process_move(self, player_id, move_data):
        """Process a player's move. Return {'valid': bool, 'message': str}"""
        pass
    
    def is_game_complete(self):
        """Check if game should end"""
        return False
    
    def get_results(self):
        """Get final results/winner"""
        return None


class RockPaperScissorsManager(GameManager):
    """Rock Paper Scissors - Best of N"""
    
    VALID_MOVES = ["rock", "paper", "scissors"]
    BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    
    def __init__(self, room, best_of=3):
        super().__init__(room)
        self.best_of = best_of
        self.rounds = []
        self.current_round = 1
        # Track choices with explicit round number to avoid stale choice reuse across rounds
        # Format: {'round': int, 'choices': {player_id: choice}}
        self.round_choices = {'round': self.current_round, 'choices': {}}
        # Per-game lock to avoid race conditions when multiple threads/async events
        # call process_move/_resolve_round concurrently
        self._lock = threading.Lock()
        
    def start(self):
        """Start first round"""
        self.current_round = 1
        self.round_choices = {'round': self.current_round, 'choices': {}}
        self.room.current_game.state_data = {
            'current_round': self.current_round,
            'best_of': self.best_of,
            'rounds': self.rounds
        }
    
    def process_move(self, player_id, move_data):
        """Accept a choice (rock/paper/scissors)"""
        move = move_data.get('choice', '').lower()
        # Optional: client can send a round number to prevent stale moves from older rounds
        client_round = move_data.get('round')
        if client_round is not None and client_round != self.current_round:
            # Reject moves that are for different rounds
            print(f"[RPS] Rejecting move from {player_id} for round {client_round} (current={self.current_round})")
            return {'valid': False, 'message': 'Move belongs to a different round'}
        
        if move not in self.VALID_MOVES:
            return {'valid': False, 'message': 'Invalid move'}
        
        # Make changes atomically with a lock since events can be processed concurrently
        with self._lock:
            # Ensure we are recording moves for the correct round - reset if manager thinks we advanced
            if self.round_choices.get('round') != self.current_round:
                self.round_choices = {'round': self.current_round, 'choices': {}}

            if player_id in self.round_choices['choices']:
                return {'valid': False, 'message': 'Already submitted for this round'}

            self.round_choices['choices'][player_id] = move
            # update state_data so client sees when a player has submitted for the current round
            if self.room.current_game:
                self.room.current_game.state_data['choices'] = self.round_choices['choices']
        print(f"[RPS] Move recorded for player {player_id}: {move}. Round {self.current_round} choices: {len(self.round_choices['choices'])}/{len(self.room.players)}")
        
        # Check if both players have submitted
        # If this move completes the round, resolve it under the lock
        if len(self.round_choices['choices']) == len(self.room.players):
            print(f"[RPS] Both players submitted, resolving round...")
            with self._lock:
                # Double-check the set of choices is still for the current round (no race)
                if self.round_choices.get('round') == self.current_round and len(self.round_choices['choices']) == len(self.room.players):
                    self._resolve_round()
            print(f"[RPS] After resolve: round={self.current_round}, scores={self.room.current_game.player_scores}")
        
        return {'valid': True, 'message': 'Choice recorded'}
    
    def _resolve_round(self):
        """Determine winner of current round"""
        choices = self.round_choices.get('choices', {})
        # Use room.player_order to ensure consistent player ordering (p1/p2)
        player_ids = list(self.room.player_order)
        
        if len(player_ids) != 2:
            return
        
        p1, p2 = player_ids[0], player_ids[1]
        c1, c2 = choices[p1], choices[p2]
        
        winner = None
        if c1 == c2:
            result = "tie"
        elif self.BEATS.get(c1) == c2:
            winner = p1
            result = "p1_win"
        else:
            winner = p2
            result = "p2_win"
        
        round_result = {
            'round': self.current_round,
            'p1_choice': c1,
            'p2_choice': c2,
            'winner': winner,
            'result': result
        }
        
        self.rounds.append(round_result)
        
        # Update scores
        if winner:
            self.room.current_game.player_scores[winner] += 1
        elif result == "tie":
            # Award 1 point to both players on a draw
            self.room.current_game.player_scores[p1] += 1
            self.room.current_game.player_scores[p2] += 1
        
        # Check if game is over - do NOT override is_game_complete method
        scores = list(self.room.current_game.player_scores.values())
        if max(scores) > self.best_of // 2:
            # mark as complete by leaving to is_game_complete method (do nothing special)
            pass
        else:
            self.current_round += 1
            # Reset round choices for the next round and store the new round index
            self.round_choices = {'round': self.current_round, 'choices': {}}
        
        # Persist state data for clients
        self.room.current_game.state_data['current_round'] = self.current_round
        self.room.current_game.state_data['rounds'] = self.rounds
        self.room.current_game.state_data['best_of'] = self.best_of
        # choices only hold current round selections
        self.room.current_game.state_data['choices'] = self.round_choices.get('choices', {})
    
    def is_game_complete(self):
        """Check if best-of series is won"""
        if not self.room.current_game.player_scores:
            return False
        scores = list(self.room.current_game.player_scores.values())
        max_score = max(scores)
        threshold = self.best_of // 2
        is_complete = max_score > threshold
        print(f"[RPS] is_game_complete check: scores={self.room.current_game.player_scores}, max={max_score}, threshold={threshold}, complete={is_complete}")
        return is_complete
    
    def get_results(self):
        """Return game results"""
        player_ids = list(self.room.players.keys())
        if len(player_ids) < 2:
            return None
        
        scores = {pid: self.room.current_game.player_scores[pid] for pid in player_ids}
        winner = max(player_ids, key=lambda pid: scores[pid])
        
        return {
            'winner': winner,
            'scores': scores,
            'rounds': self.rounds,
            'best_of': self.best_of
        }


class TicTacToeManager(GameManager):
    """Tic Tac Toe - Turn-based"""
    
    def __init__(self, room):
        super().__init__(room)
        self.board = ['' for _ in range(9)]  # 0-8 positions, empty strings not spaces
        self.player_to_symbol = {}
        self.current_player_index = 0
        self.move_count = 0
        
    def start(self):
        """Initialize board and assign X/O to players"""
        # Reset board for new game
        self.board = ['' for _ in range(9)]
        self.move_count = 0
        self.current_player_index = 0
        
        player_ids = list(self.room.players.keys())
        if len(player_ids) >= 2:
            # Count how many TicTacToe games have been played to alternate starting player
            tictactoe_games = len([g for g in self.room.game_history if g.game_type.value == 'tictactoe'])
            
            # Alternate: even games (0, 2, 4...) player1 is X, odd games player1 is O
            if tictactoe_games % 2 == 0:
                self.player_to_symbol[player_ids[0]] = 'X'
                self.player_to_symbol[player_ids[1]] = 'O'
            else:
                self.player_to_symbol[player_ids[0]] = 'O'
                self.player_to_symbol[player_ids[1]] = 'X'
        
        # Ensure state_data is a dict
        if not self.room.current_game.state_data:
            self.room.current_game.state_data = {}
        
        self.room.current_game.state_data.update({
            'board': self.board,
            'player_to_symbol': self.player_to_symbol,
            'current_player': player_ids[0] if player_ids else None,
            'move_count': 0
        })
    
    def process_move(self, player_id, move_data):
        """Process a board move"""
        player_ids = list(self.room.players.keys())
        if len(player_ids) < 2:
            return {'valid': False, 'message': 'Not enough players'}
        
        # Check turn
        current = player_ids[self.current_player_index % 2]
        if player_id != current:
            return {'valid': False, 'message': 'Not your turn'}
        
        position = move_data.get('position')
        if not isinstance(position, int) or position < 0 or position > 8:
            return {'valid': False, 'message': 'Invalid position'}
        
        if self.board[position] != '':
            return {'valid': False, 'message': 'Position already taken'}
        
        symbol = self.player_to_symbol[player_id]
        self.board[position] = symbol
        self.move_count += 1
        
        self.room.current_game.state_data['board'] = self.board
        self.room.current_game.state_data['move_count'] = self.move_count
        
        # Switch turn
        self.current_player_index += 1
        next_player = player_ids[self.current_player_index % 2]
        self.room.current_game.state_data['current_player'] = next_player
        
        return {'valid': True, 'message': 'Move accepted'}
    
    def _check_winner(self):
        """Check if there's a winner"""
        winning_combos = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # cols
            [0, 4, 8], [2, 4, 6]  # diagonals
        ]
        
        for combo in winning_combos:
            if self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] != '':
                return self.board[combo[0]]
        
        return None
    
    def is_game_complete(self):
        """Check if game is over (win or draw)"""
        if self._check_winner():
            return True
        if self.move_count >= 9:  # Board full
            return True
        return False
    
    def get_results(self):
        """Return game results"""
        winner_symbol = self._check_winner()
        player_ids = list(self.room.players.keys())
        
        if winner_symbol:
            # Find player with this symbol
            winner = [pid for pid, sym in self.player_to_symbol.items() if sym == winner_symbol][0]
            return {'winner': winner, 'result': 'win', 'board': self.board}
        elif self.move_count >= 9:
            return {'winner': None, 'result': 'draw', 'board': self.board}
        else:
            return None


class ReactionTimeManager(GameManager):
    """Reaction Time Duel - First valid tap after random delay"""
    
    def __init__(self, room):
        super().__init__(room)
        self.delay_ms = random.randint(1000, 3000)
        self.start_time = None
        self.reaction_times = {}
        self.started = False
        
    def start(self):
        """Initialize reaction game"""
        self.start_time = time.time() * 1000  # ms
        self.started = True
        self.room.current_game.state_data = {
            'delay_ms': self.delay_ms,
            'start_time': self.start_time,
            'ready': False,
            'reactions': {}
        }
    
    def set_ready(self):
        """Server-side: trigger ready state after delay"""
        self.room.current_game.state_data['ready'] = True
    
    def process_move(self, player_id, move_data):
        """Record a tap reaction"""
        if not self.started:
            return {'valid': False, 'message': 'Game not started'}
        
        current_time = time.time() * 1000  # ms
        elapsed = current_time - self.start_time
        
        # Anti-cheat: disqualify if tapped before delay or if already recorded
        if player_id in self.reaction_times:
            return {'valid': False, 'message': 'Already recorded'}
        
        if elapsed < self.delay_ms:
            return {'valid': False, 'message': 'Too early - disqualified', 'early_tap': True}
        
        reaction_ms = elapsed - self.delay_ms
        self.reaction_times[player_id] = reaction_ms
        self.room.current_game.state_data['reactions'][player_id] = reaction_ms
        
        return {'valid': True, 'message': 'Reaction recorded', 'reaction_ms': reaction_ms}
    
    def is_game_complete(self):
        """Game ends when both players have tapped"""
        return len(self.reaction_times) >= len(self.room.players)
    
    def get_results(self):
        """Return results - fastest reaction wins"""
        if not self.reaction_times:
            return None
        
        fastest_player = min(self.reaction_times, key=self.reaction_times.get)
        
        return {
            'winner': fastest_player,
            'reaction_times': self.reaction_times,
            'delay_ms': self.delay_ms
        }


class QuickMathManager(GameManager):
    """Quick Math Duel - First correct answer wins"""
    
    def __init__(self, room):
        super().__init__(room)
        self.current_question = None
        self.correct_answer = None
        self.first_correct = None
        self.answers = {}
        
    def start(self):
        """Generate a random math question"""
        self._generate_question()
        self.room.current_game.state_data = {
            'question': self.current_question,
            'answered_count': 0
        }
    
    def _generate_question(self):
        """Generate simple addition math questions only"""
        a = random.randint(1, 99)
        b = random.randint(1, 99)
        # Only addition problems - easy and fun
        self.correct_answer = a + b
        self.current_question = f"{a} + {b}"
    
    def process_move(self, player_id, move_data):
        """Check answer"""
        if player_id in self.answers:
            return {'valid': False, 'message': 'Already answered'}
        
        try:
            answer = int(move_data.get('answer', 0))
        except (ValueError, TypeError):
            return {'valid': False, 'message': 'Invalid answer format'}
        
        self.answers[player_id] = answer
        correct = answer == self.correct_answer
        
        if correct and not self.first_correct:
            self.first_correct = player_id
        
        self.room.current_game.state_data['answered_count'] = len(self.answers)
        
        return {
            'valid': True,
            'correct': correct,
            'message': 'Answer recorded'
        }
    
    def is_game_complete(self):
        """Game ends when first player answers correctly or timeout"""
        return bool(self.first_correct) or len(self.answers) >= len(self.room.players)
    
    def get_results(self):
        """Return results"""
        if self.first_correct:
            winner = self.first_correct
            result_type = 'first_correct'
        else:
            # If no one answered correctly, no winner
            result_type = 'no_winner'
            winner = None
        
        return {
            'winner': winner,
            'question': self.current_question,
            'correct_answer': self.correct_answer,
            'result_type': result_type,
            'answers': self.answers
        }


class WouldYouRatherManager(GameManager):
    """Would You Rather - Both choose, compare results"""
    
    QUESTIONS = [
        {"a": "Have the ability to fly", "b": "Have the ability to be invisible"},
        {"a": "Live on the beach", "b": "Live in the mountains"},
        {"a": "Have the power to read minds", "b": "Have the power to see the future"},
        {"a": "Be able to talk to animals", "b": "Be able to speak all languages"},
        {"a": "Have a rewind button in life", "b": "Have a pause button in life"},
        {"a": "Always know what others think of you", "b": "Be able to teleport anywhere"},
        {"a": "Win the lottery", "b": "Find your soulmate"},
        {"a": "Never have to sleep", "b": "Never have to eat"},
        {"a": "Be a famous actor", "b": "Be a famous musician"},
        {"a": "Live without internet", "b": "Live without air conditioning/heating"},
        {"a": "Always use cash", "b": "Always use cards"},
        {"a": "Always be slightly late", "b": "Always be slightly early"},
        {"a": "Travel to the past", "b": "Travel to the future"},
        {"a": "Have unlimited free time", "b": "Have unlimited money"},
        {"a": "Never have to work again", "b": "Have your dream job and be busy"},
        {"a": "Be able to eat anything without gaining weight", "b": "Be able to sleep anywhere instantly"},
        {"a": "Give up your smartphone", "b": "Give up social media forever"},
        {"a": "Only be able to whisper", "b": "Only be able to shout"},
        {"a": "See the world but be poor", "b": "Live comfortably but never travel"},
    ]
    
    def __init__(self, room):
        super().__init__(room)
        self.question = None
        self.choices = {}
        self.round_num = 1
        self.max_rounds = 3
        self._available_questions = []
        self.rounds = []
        
    def start(self):
        """Start first round"""
        # Prepare a pool of unique questions for this session to avoid repeats
        pool_size = min(len(self.QUESTIONS), self.max_rounds)
        self._available_questions = random.sample(self.QUESTIONS, k=pool_size)
        self.rounds = []
        self.round_num = 1
        self._generate_question()
        self.room.current_game.state_data = {
            'question': self.question,
            'round': self.round_num,
            'max_rounds': self.max_rounds,
            'choices': self.choices
        }
    
    def _generate_question(self):
        """Pick a random question"""
        # Pop one question from the available pool; fall back to random if exhausted
        if not hasattr(self, '_available_questions') or not self._available_questions:
            self._available_questions = random.sample(self.QUESTIONS, k=min(len(self.QUESTIONS), self.max_rounds))
        self.question = self._available_questions.pop(0)
        self.choices = {}
        # Update state_data on the room to reflect new question
        if self.room.current_game:
            self.room.current_game.state_data['question'] = self.question
            self.room.current_game.state_data['choices'] = self.choices
    
    def process_move(self, player_id, move_data):
        """Record a choice"""
        choice = move_data.get('choice')  # 'a' or 'b'
        
        if choice not in ['a', 'b']:
            return {'valid': False, 'message': 'Invalid choice'}
        
        if player_id in self.choices:
            return {'valid': False, 'message': 'Already answered'}
        
        self.choices[player_id] = choice
        
        # Check if both answered
        if len(self.choices) >= len(self.room.players):
            self._resolve_round()
        
        self.room.current_game.state_data['choices'] = self.choices
        return {'valid': True, 'message': 'Choice recorded'}
    
    def _resolve_round(self):
        """Resolve current round"""
        # For Would You Rather, record choices per round
        round_record = {
            'round': self.round_num,
            'question': self.question,
            'choices': self.choices.copy()
        }
        self.rounds.append(round_record)

        # Update state_data with round history
        if self.room.current_game:
            self.room.current_game.state_data['rounds'] = self.rounds

        self.round_num += 1
        # If still have rounds left, generate next question
        if self.round_num <= self.max_rounds:
            self._generate_question()
            if self.room.current_game:
                self.room.current_game.state_data['round'] = self.round_num
    
    def is_game_complete(self):
        """Game ends after max rounds"""
        return self.round_num > self.max_rounds
    
    def get_results(self):
        """Return match statistics"""
        player_ids = list(self.room.players.keys())
        if len(player_ids) < 2:
            return None
        
        # Return rounds and choices for the frontend to calculate compatibility
        return {
            'result_type': 'would_you_rather_complete',
            'max_rounds': self.max_rounds,
            'rounds': self.rounds,
            'message': 'Game complete - compare your preferences!'
        }


def create_game_manager(game_type, room):
    """Factory function to create appropriate game manager"""
    from app.room_manager import GameType
    
    if game_type == GameType.ROCK_PAPER_SCISSORS or game_type == 'rps':
        return RockPaperScissorsManager(room)
    elif game_type == GameType.TIC_TAC_TOE or game_type == 'tictactoe':
        return TicTacToeManager(room)
    elif game_type == GameType.REACTION_TIME or game_type == 'reaction':
        return ReactionTimeManager(room)
    elif game_type == GameType.QUICK_MATH or game_type == 'quickmath':
        return QuickMathManager(room)
    elif game_type == GameType.WOULD_YOU_RATHER or game_type == 'would_you_rather':
        return WouldYouRatherManager(room)
    else:
        return None
