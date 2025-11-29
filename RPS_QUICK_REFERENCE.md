# RPS Timer System - Developer Quick Reference

## 🎯 Key Concepts

### Timer Flow
```
[Start] → [4s Countdown] → [Reveal 1.5s] → [Repeat]
```

### Events Flow
```
Client                          Server
------                          ------
                            rps:tick (4,3,2,1)
     [listens]    ←        
     [shows timer]

[clicks choice]
   rps:choose  →
                           [records choice]
                           [when both ready]
                            rps:reveal_result
     [listens]    ←
     [shows result]
                           [after 1.5s delay]
                            rps:new_round
     [listens]    ←
     [reset UI]
     [show timer "4"]

[clicks choice] ← [repeat]
```

---

## 🔧 Code Locations

### Backend (Python)

**File**: `app/rps_manager.py`

Key class:
```python
class RockPaperScissorsManager:
    def __init__(self, room)
    def start()                          # Initialize first round
    def record_choice(player_id, choice) # Store choice during countdown
    def _start_timer_loop()              # Background thread with ticks
    def _finalize_and_next_round()       # Called when timer expires
    def stop()                           # Stop timer thread
```

**File**: `app/socketio_events_rps.py`

Key handlers:
```python
@socketio.on('start_game_request')
def handle_start_game(data):             # Starts RPS manager

@socketio.on('rps:choose')
def handle_rps_choose(data):             # Records player choice
```

### Frontend (JavaScript)

**File**: `app/static/js/rps_new.js`

Key class:
```javascript
class RockPaperScissorsGame {
    render(container)                   // Show UI
    submitChoice(choice)                // Send choice to server
    onTick(remaining)                   // Update timer (4,3,2,1)
    revealResult(data)                  // Show choices and winner
    onNewRound(data)                    // Reset for next round
    startRound()                        // Enable buttons
}
```

**File**: `app/static/js/room_rps.js`

Key functions:
```javascript
setupRPSListeners()                     // Attach RPS event handlers
initializeGameUI(gameType, room)        // Create game instance
                                        // FIX: Sets currentGame first!
```

---

## 📡 Socket.IO Events

### Server → Client

| Event | Payload | Purpose |
|-------|---------|---------|
| `rps:tick` | `{remaining: 4\|3\|2\|1}` | Update timer display |
| `rps:new_round` | `{round_number: N}` | Start next round |
| `rps:reveal_result` | `{p1_choice, p2_choice, winner, scores}` | Show result |

### Client → Server

| Event | Payload | Purpose |
|-------|---------|---------|
| `rps:choose` | `{room_id, choice}` | Submit choice |

---

## 🚨 Common Issues & Fixes

### Issue: Timer not counting down

```javascript
// Check in rps_new.js::onTick()
onTick(remaining) {
    document.getElementById('rps-timer').textContent = remaining;
    // ✅ This should be called every second by server
}
```

**Fix**: Verify server is emitting `rps:tick` in `_start_timer_loop()`

---

### Issue: currentGame undefined

```javascript
// ❌ WRONG - happens if currentGame not set first:
roomState.currentGame = null;
new RockPaperScissorsGame(roomState).render(container);
// → Game constructor sees null currentGame → Error!

// ✅ CORRECT - in room_rps.js::initializeGameUI():
roomState.currentGame = gameType;  // SET FIRST
const mgr = new RockPaperScissorsGame(roomState);
mgr.render(container);  // NOW safe
```

**Fix**: Ensure `room_rps.js` (not old `room.js`) is loaded, and look for this line:
```javascript
roomState.currentGame = data.game_type;
```

---

### Issue: Choices not registering

```python
# Check in rps_manager.py::record_choice()
def record_choice(self, player_id, choice):
    with self._lock:
        if not self.current_round.timer_running:
            return {'valid': False, 'message': 'Round not active'}
        # ✅ Returns error if timer not running
```

**Fix**: Verify timer is running (check server logs)

---

### Issue: New round never starts

```python
# In rps_manager.py::_finalize_and_next_round()
def _schedule_next_round(self):
    def delayed_start():
        time.sleep(1.5)  # ← 1.5s delay before next round
        # Then emits rps:new_round
    thread = threading.Thread(target=delayed_start, daemon=True)
    thread.start()
```

**Fix**: Check server logs for exceptions in background thread

---

## ✅ Testing Steps

### Quick Test (2 players, 1 minute)

1. Open http://localhost:5000 in 2 browser tabs
2. Tab 1: Create room
3. Tab 2: Join room
4. Both select RPS → Simple
5. **Expected**:
   - Timer shows "4" and counts down
   - Both choose Rock/Paper/Scissors
   - After 4 seconds, choices appear
   - Winner highlighted
   - 1.5 seconds later, new round starts
   - Repeat 3 times

### Browser Console Check

```javascript
// Should see logs like:
[LOG] [INIT] DOM loaded, connecting socket...
[LOG] [SOCKET] Join room response: {success: true}
[LOG] [GAME] Initializing game UI: rps
[LOG] [RPS] Game rendered successfully
[LOG] [RPS] Round started
[LOG] [RPS] Choice submitted: rock
[LOG] [RPS] Result revealed
[LOG] [RPS] New round starting

// NO ERRORS - if any, check the error message
```

---

## 🔐 Thread Safety Notes

### Server-Side Lock

```python
# All state changes protected by lock
with self._lock:
    self.current_round.record_choice(player_id, choice)
    # Only one event handler can execute here at a time
```

### Why This Matters

If two players submit choices simultaneously:
- ❌ Without lock: Both might think they're the only one
- ✅ With lock: Atomically recorded in order

---

## 📈 Performance Expectations

| Metric | Expected |
|--------|----------|
| Timer accuracy | ±0.1s (due to network) |
| Choice submission latency | <100ms |
| Reveal after timeout | ~100ms |
| New round delay | 1.5s (by design) |

---

## 🔄 Game Loop Sequence

```
Player 1 joins
    ↓
Player 2 joins → Both see game selection
    ↓
Select RPS, pick Simple mode
    ↓
Server starts RockPaperScissorsManager
    ↓
Manager.start() → first round begins
    ↓
Background thread starts emitting ticks
    ↓
Client hears "rps:tick" events (4,3,2,1)
    ↓
Player 1 clicks "Rock" → emit rps:choose
    ↓
Player 2 clicks "Paper" → emit rps:choose
    ↓
Timer expires (4 seconds elapsed)
    ↓
Manager._finalize_and_next_round()
    - Lock choices
    - Compute: Paper beats Rock → Player 2 wins
    - Emit: rps:reveal_result
    ↓
Both clients show: P1=Rock, P2=Paper, P2 Wins
    ↓
[1.5 seconds pass]
    ↓
Emit: rps:new_round
    ↓
Both clients reset and show timer "4" again
    ↓
[Loop back to "Client hears tick" step]
```

---

## 📝 Code Walkthrough

### How a Round Works (from start to reveal)

**Server side** (`rps_manager.py`):
```python
# 1. Start round
def start(self):
    self.current_round = RPSRoundState()
    self.current_round.start()  # Sets timer_running=True, round_started_at=now()
    self._start_timer_loop()    # Background thread begins

# 2. Background thread emits ticks
def _start_timer_loop(self):
    while not self._stop_flag:
        remaining = self.current_round.get_remaining_time()  # 4, 3, 2, 1
        self._emit_tick(remaining)  # Broadcast to all players

# 3. When player submits choice
def record_choice(self, player_id, choice):
    self.current_round.record_choice(player_id, choice)  # Store choice
    if len(self.round_choices['choices']) == 2:  # Both ready?
        self._finalize_and_next_round()

# 4. Finalize and reveal
def _finalize_and_next_round(self):
    self.current_round.finalize(player_ids)  # Lock and compute winner
    socketio.emit('rps:reveal_result', {...})  # Send result to all
    self._schedule_next_round()  # Start new round in 1.5s
```

**Client side** (`rps_new.js`):
```javascript
// Listen for server events
socketClient.on('rps:tick', (data) => {
    gameManager.onTick(data.remaining);  // Update timer display
});

socketClient.on('rps:reveal_result', (data) => {
    gameManager.revealResult(data);  // Show choices and winner
});

socketClient.on('rps:new_round', (data) => {
    gameManager.onNewRound(data);  // Reset UI, enable buttons
});

// Player action
function submitChoice(choice) {
    socketClient.emit('rps:choose', {choice});
}
```

---

## 🎬 Next Steps

1. **Review** this file + code comments
2. **Run local tests** (see Testing Steps)
3. **Check console** for errors
4. **Deploy** to Render
5. **Live test** on production URL
6. **Monitor** error logs

---

**File sizes**:
- `rps_manager.py`: ~280 lines
- `socketio_events_rps.py`: ~250 lines
- `rps_new.js`: ~160 lines
- `room_rps.js`: ~380 lines
- `socket-client-rps.js`: ~100 lines

**Total LOC**: ~1,170 lines (clean, well-commented code)
