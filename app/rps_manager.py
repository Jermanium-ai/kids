"""
PlaySync - Rock Paper Scissors Game Manager (NEW TIMER-BASED SYSTEM)
Server-authoritative timer and round management without "best of N"
"""

import time
import threading
from enum import Enum
from app import socketio


class RPSRoundState:
    """Represents a single 4-second RPS round"""
    
    TIMER_DURATION = 4  # 4-second countdown per round
    REVEAL_DURATION = 1.5  # 1.5 seconds to show result before next round
    
    def __init__(self):
        self.choices = {}  # {player_id: "rock"|"paper"|"scissors"|"none"}
        self.timer_running = False
        self.round_started_at = None
        self.winner = None  # "player1" | "player2" | "draw" | None
        self.completed = False
    
    def start(self):
        """Start the 4-second countdown"""
        self.timer_running = True
        self.round_started_at = time.time()
        self.choices = {}
        self.winner = None
        self.completed = False
    
    def record_choice(self, player_id, choice):
        """Record a player's choice. Can be changed during countdown."""
        if not self.timer_running:
            return False
        self.choices[player_id] = choice
        return True
    
    def get_elapsed_time(self):
        """Get seconds elapsed since round start"""
        if not self.round_started_at:
            return 0
        return time.time() - self.round_started_at
    
    def get_remaining_time(self):
        """Get seconds remaining in the round (0 if expired)"""
        elapsed = self.get_elapsed_time()
        remaining = max(0, self.TIMER_DURATION - elapsed)
        return remaining
    
    def is_expired(self):
        """Check if 4 seconds have passed"""
        return self.get_remaining_time() <= 0
    
    def finalize(self, player_ids):
        """
        Lock choices and compute winner.
        Called when timer expires.
        """
        self.timer_running = False
        
        # Fill in "none" for players who didn't choose
        for player_id in player_ids:
            if player_id not in self.choices:
                self.choices[player_id] = "none"
        
        # Compute winner
        self.winner = self._compute_winner(player_ids)
        self.completed = True
    
    def _compute_winner(self, player_ids):
        """
        Compute winner given 2 player IDs
        Return: "player1" | "player2" | "draw" | None
        """
        if len(player_ids) != 2:
            return None
        
        p1_id, p2_id = player_ids[0], player_ids[1]
        p1_choice = self.choices.get(p1_id, "none")
        p2_choice = self.choices.get(p2_id, "none")
        
        # If both chose nothing, it's a draw
        if p1_choice == "none" and p2_choice == "none":
            return "draw"
        
        # If one chose nothing, the other wins
        if p1_choice == "none":
            return "player2"
        if p2_choice == "none":
            return "player1"
        
        # Both made valid choices
        if p1_choice == p2_choice:
            return "draw"
        
        # Check what beats what
        beats_map = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
        if beats_map.get(p1_choice) == p2_choice:
            return "player1"
        else:
            return "player2"


class RockPaperScissorsManager:
    """
    NEW RPS Manager: Timer-based, no "best of N", server-authoritative
    """
    
    def __init__(self, room):
        self.room = room
        self.current_round = RPSRoundState()
        self._timer_thread = None
        self._lock = threading.Lock()
        self._stop_flag = False
        self.rounds_completed = []  # History of all completed rounds
    
    def start(self):
        """Start the first round immediately"""
        with self._lock:
            self._stop_flag = False
            self.current_round.start()
            
            # Initialize room state
            if self.room.current_game:
                self.room.current_game.state_data = {
                    'round_number': len(self.rounds_completed) + 1,
                    'timer_running': True,
                    'choices': {},
                    'winner': None
                }
        
        # Start server-side ticker in background
        self._start_timer_loop()
    
    def _start_timer_loop(self):
        """
        Background thread that:
        1. Emits tick events every 1 second
        2. Detects round expiry at 4 seconds
        3. Finalizes round and starts next
        """
        def run():
            last_tick = -1  # Track which second we last emitted
            
            while not self._stop_flag:
                with self._lock:
                    if not self.current_round.timer_running:
                        time.sleep(0.1)
                        continue
                    
                    remaining = self.current_round.get_remaining_time()
                    remaining_int = int(remaining)
                    
                    # Emit tick if we entered a new second
                    if remaining_int != last_tick and remaining_int > 0:
                        last_tick = remaining_int
                        self._emit_tick(remaining_int)
                    
                    # Round expired?
                    if self.current_round.is_expired():
                        self._finalize_and_next_round()
                        last_tick = -1  # Reset for next round
                
                time.sleep(0.05)  # Check frequently for accuracy
        
        self._timer_thread = threading.Thread(target=run, daemon=True)
        self._timer_thread.start()
    
    def _emit_tick(self, remaining_seconds):
        """Emit tick event to all players"""
        try:
            # remaining_seconds: 4, 3, 2, 1
            socketio.emit(
                'rps:tick',
                {'remaining': remaining_seconds},
                room=self.room.room_id
            )
        except Exception as e:
            print(f"[RPS] Error emitting tick: {e}")
    
    def _finalize_and_next_round(self):
        """
        Called when timer reaches 0:
        1. Lock choices
        2. Compute winner
        3. Emit reveal
        4. Schedule next round after 1.5s
        """
        # Get player order for winner mapping
        player_ids = [p.player_id for p in self.room.players]
        
        # Finalize current round
        self.current_round.finalize(player_ids)
        self.rounds_completed.append({
            'choices': self.current_round.choices.copy(),
            'winner': self.current_round.winner
        })
        
        # Update scores
        if self.current_round.winner == "player1":
            if player_ids[0] in self.room.player_scores:
                self.room.player_scores[player_ids[0]] += 1
        elif self.current_round.winner == "player2":
            if player_ids[1] in self.room.player_scores:
                self.room.player_scores[player_ids[1]] += 1
        
        # Update room state BEFORE emit
        if self.room.current_game:
            self.room.current_game.state_data = {
                'round_number': len(self.rounds_completed),
                'timer_running': False,
                'choices': self.current_round.choices.copy(),
                'winner': self.current_round.winner
            }
        
        # Emit reveal
        try:
            socketio.emit(
                'rps:reveal_result',
                {
                    'p1_choice': self.current_round.choices.get(player_ids[0], "none"),
                    'p2_choice': self.current_round.choices.get(player_ids[1], "none"),
                    'winner': self.current_round.winner,
                    'scores': self.room.player_scores.copy()
                },
                room=self.room.room_id
            )
        except Exception as e:
            print(f"[RPS] Error emitting reveal_result: {e}")
        
        # Schedule next round after 1.5 seconds
        if not self._stop_flag:
            self._schedule_next_round()
    
    def _schedule_next_round(self):
        """Start next round after 1.5 second delay"""
        def delayed_start():
            time.sleep(1.5)
            with self._lock:
                if not self._stop_flag:
                    self.current_round = RPSRoundState()
                    self.current_round.start()
                    
                    if self.room.current_game:
                        self.room.current_game.state_data = {
                            'round_number': len(self.rounds_completed) + 1,
                            'timer_running': True,
                            'choices': {},
                            'winner': None
                        }
                    
                    # Emit new_round to reset UI
                    try:
                        socketio.emit(
                            'rps:new_round',
                            {'round_number': len(self.rounds_completed) + 1},
                            room=self.room.room_id
                        )
                    except Exception as e:
                        print(f"[RPS] Error emitting new_round: {e}")
        
        thread = threading.Thread(target=delayed_start, daemon=True)
        thread.start()
    
    def record_choice(self, player_id, choice):
        """
        Player submitted a choice during the 4-second window.
        Can be changed multiple times; only last one counts.
        """
        with self._lock:
            if not self.current_round.timer_running:
                return {
                    'valid': False,
                    'message': 'Round not active'
                }
            
            choice_lower = choice.lower()
            if choice_lower not in ["rock", "paper", "scissors"]:
                return {
                    'valid': False,
                    'message': 'Invalid choice. Use rock, paper, or scissors.'
                }
            
            self.current_round.record_choice(player_id, choice_lower)
            
            return {
                'valid': True,
                'message': 'Choice recorded'
            }
    
    def stop(self):
        """Stop the timer loop when game ends"""
        with self._lock:
            self._stop_flag = True
    
    def get_state(self):
        """Get current round state for debugging/frontend sync"""
        with self._lock:
            return {
                'timer_running': self.current_round.timer_running,
                'remaining_time': self.current_round.get_remaining_time(),
                'choices': self.current_round.choices.copy(),
                'rounds_completed': len(self.rounds_completed)
            }
