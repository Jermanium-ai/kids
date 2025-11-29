"""
PlaySync - RPS Timer-Based Game Manager
Implements a 4-second round timer with server-authoritative logic
"""

import threading
import time
from datetime import datetime


class RPSTimerManager:
    """
    Rock Paper Scissors with 4-second countdown timer per round.
    
    Server-authoritative:
    - Backend controls all timing (no client-side timers)
    - Choices are locked after 4 seconds
    - Results automatically trigger next round
    - Infinite rounds with automatic progression
    """
    
    VALID_CHOICES = ['rock', 'paper', 'scissors']
    BEATS = {'rock': 'scissors', 'scissors': 'paper', 'paper': 'rock'}
    ROUND_DURATION = 4  # seconds
    REVEAL_DURATION = 1.5  # seconds to show result
    
    def __init__(self, room, socketio, room_id):
        self.room = room
        self.socketio = socketio
        self.room_id = room_id
        
        # Game state
        self.running = False
        self.current_round = 1
        self.scores = {}  # {player_id: score}
        self.choices = {}  # {player_id: choice}
        self.round_history = []  # List of round results
        
        # Timer state
        self.timer_thread = None
        self.timer_lock = threading.Lock()
        self.stop_flag = threading.Event()
        
        # Initialize scores for all players
        for player_id in room.players.keys():
            self.scores[player_id] = 0
    
    def start(self):
        """Start the game and begin first round"""
        print(f"[RPS_TIMER] Starting game for room {self.room_id}")
        with self.timer_lock:
            if self.running:
                return
            self.running = True
            self.stop_flag.clear()
        
        # Start the timer thread
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()
        
        # Broadcast game started
        self.socketio.emit('rps_round_update', {
            'round': self.current_round,
            'timer': self.ROUND_DURATION,
            'scores': self.scores,
            'message': 'Round started. Make your choice!'
        }, room=self.room_id)
    
    def submit_choice(self, player_id, choice):
        """
        Submit a choice for the current round.
        Can be changed anytime before the 4-second timer ends.
        """
        choice = choice.lower() if isinstance(choice, str) else ''
        
        if choice not in self.VALID_CHOICES:
            return {'success': False, 'error': 'Invalid choice'}
        
        with self.timer_lock:
            self.choices[player_id] = choice
            print(f"[RPS_TIMER] Player {player_id} chose {choice}")
        
        # Broadcast that player has submitted
        self.socketio.emit('rps_player_ready', {
            'player_id': player_id,
            'ready': True
        }, room=self.room_id)
        
        return {'success': True, 'choice': choice}
    
    def _timer_loop(self):
        """
        Background thread that manages round timing.
        Emits tick events, locks choices, determines winners, and progresses rounds.
        """
        while not self.stop_flag.is_set():
            try:
                # Start new round
                with self.timer_lock:
                    self.choices = {}  # Clear choices for new round
                
                print(f"[RPS_TIMER] Starting round {self.current_round}")
                
                # Countdown from 4 to 1
                for remaining in range(self.ROUND_DURATION, 0, -1):
                    if self.stop_flag.is_set():
                        return
                    
                    # Emit tick event
                    self.socketio.emit('rps_timer_tick', {
                        'round': self.current_round,
                        'remaining': remaining,
                        'total': self.ROUND_DURATION
                    }, room=self.room_id)
                    
                    print(f"[RPS_TIMER] Round {self.current_round} - {remaining}s")
                    time.sleep(1)
                
                if self.stop_flag.is_set():
                    return
                
                # Timer ended - lock choices and determine winner
                self._finalize_round()
                
                # Show result for 1.5 seconds
                time.sleep(self.REVEAL_DURATION)
                
                if self.stop_flag.is_set():
                    return
                
                # Move to next round
                with self.timer_lock:
                    self.current_round += 1
                
            except Exception as e:
                print(f"[RPS_TIMER] Error in timer loop: {e}")
                self.stop_flag.set()
    
    def _finalize_round(self):
        """
        Lock choices, determine winner, update scores, and broadcast result.
        Called when 4-second timer expires.
        """
        with self.timer_lock:
            # Get all player IDs in consistent order
            player_ids = list(self.room.player_order)
            
            if len(player_ids) < 2:
                print(f"[RPS_TIMER] Not enough players to finalize round")
                return
            
            # Get choices, default to None if not submitted
            p1_id, p2_id = player_ids[0], player_ids[1]
            p1_choice = self.choices.get(p1_id)
            p2_choice = self.choices.get(p2_id)
            
            print(f"[RPS_TIMER] Finalizing round {self.current_round}")
            print(f"  P1 ({p1_id}): {p1_choice}")
            print(f"  P2 ({p2_id}): {p2_choice}")
            
            # Determine winner
            winner = None
            result = None
            
            if p1_choice is None and p2_choice is None:
                result = 'tie'
                reason = 'Both players did not choose'
            elif p1_choice is None:
                winner = p2_id
                result = 'p2_win'
                reason = 'Player 1 did not choose'
            elif p2_choice is None:
                winner = p1_id
                result = 'p1_win'
                reason = 'Player 2 did not choose'
            elif p1_choice == p2_choice:
                result = 'tie'
                reason = 'Same choice'
            elif self.BEATS[p1_choice] == p2_choice:
                winner = p1_id
                result = 'p1_win'
                reason = f'{p1_choice} beats {p2_choice}'
            else:
                winner = p2_id
                result = 'p2_win'
                reason = f'{p2_choice} beats {p1_choice}'
            
            # Update scores
            if winner:
                self.scores[winner] += 1
            else:
                # Tie - award both players a point
                self.scores[p1_id] += 1
                self.scores[p2_id] += 1
            
            # Record round
            round_record = {
                'round': self.current_round,
                'choices': {p1_id: p1_choice, p2_id: p2_choice},
                'winner': winner,
                'result': result,
                'reason': reason,
                'scores': dict(self.scores)
            }
            self.round_history.append(round_record)
            
            print(f"[RPS_TIMER] Round {self.current_round} result: {result} ({reason})")
            print(f"[RPS_TIMER] Current scores: {self.scores}")
        
        # Broadcast result
        self.socketio.emit('rps_result', {
            'round': self.current_round,
            'p1_id': p1_id,
            'p1_choice': p1_choice,
            'p2_id': p2_id,
            'p2_choice': p2_choice,
            'winner': winner,
            'result': result,
            'reason': reason,
            'scores': self.scores
        }, room=self.room_id)
    
    def stop(self):
        """Stop the game"""
        print(f"[RPS_TIMER] Stopping game for room {self.room_id}")
        self.stop_flag.set()
        with self.timer_lock:
            self.running = False
    
    def get_stats(self):
        """Get current game statistics"""
        return {
            'current_round': self.current_round,
            'scores': self.scores,
            'round_history': self.round_history,
            'running': self.running
        }
