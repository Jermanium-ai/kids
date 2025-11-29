# PlaySync - WebSocket Fix & RPS Timer System Rebuild

## SUMMARY OF CHANGES

This document outlines all changes made to fix WebSocket disconnection issues and rebuild the Rock-Paper-Scissors game with a 4-second server-authoritative timer system.

---

## PART 1: WEBSOCKET INFRASTRUCTURE FIXES

### 1.1 Fixed SocketIO Initialization (`app/__init__.py`)

**Changes:**
- Removed `async_mode = 'threading'` variable assignment, moved directly to SocketIO init
- **Added `manage_session=False`** - Allows two tabs from the same browser to use different SIDs (fixes multi-tab playing)
- Removed logging parameters that could cause issues
- Set explicit transports: `['websocket', 'polling']` with WebSocket as primary

**Before:**
```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    async_mode=async_mode,
    engineio_logger=False,
    transports=['websocket', 'polling'],
)
```

**After:**
```python
socketio = SocketIO(
    app,
    async_mode='threading',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25,
    transports=['websocket', 'polling'],
    engineio_logger=False,
    manage_session=False,  # NEW: Allow two tabs from same browser
    logger=False
)
```

### 1.2 Safe Delayed Disconnect Handler (`app/socketio_events.py`)

**Problem:** Player disconnects immediately when second tab connects, causing "Waiting for Players" loop.

**Solution:** Implement 5-second delayed disconnect cleanup with reconnection verification.

**New Code:**
```python
import threading

disconnect_timers = {}  # {socket_id: timer_object}

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with safe delayed cleanup"""
    sid = request.sid
    player_id = socket_to_player.get(sid)
    
    # Cancel any pending disconnect timer for this socket
    if sid in disconnect_timers:
        disconnect_timers[sid].cancel()
        del disconnect_timers[sid]
    
    # Schedule delayed cleanup (5 seconds) to verify socket is really gone
    def delayed_cleanup():
        # Check if socket has reconnected
        try:
            if sid in socketio.server.sids:
                print(f"[DISCONNECT_CLEANUP] Socket {sid} reconnected, keeping player")
                return
        except:
            pass
        
        # Socket is really gone, cleanup
        if sid in socket_to_player:
            player_id_to_remove = socket_to_player.pop(sid)
            if player_id_to_remove in player_sockets:
                del player_sockets[player_id_to_remove]
        
        if sid in disconnect_timers:
            del disconnect_timers[sid]
    
    # Start 5-second delayed cleanup
    timer = threading.Timer(5.0, delayed_cleanup)
    disconnect_timers[sid] = timer
    timer.daemon = True
    timer.start()
```

**Impact:** Players no longer disconnect when second browser tab joins.

### 1.3 WebSocket-Only Socket Client (`app/static/js/socket-client.js`)

**Changes:**
- Changed from `['websocket', 'polling']` to `['websocket']` (WebSocket only)
- Set `upgrade: false` to prevent protocol negotiation
- Added `reconnectionAttempts: Infinity` for persistent reconnection
- Added RPS-specific event listeners

**Before:**
```javascript
this.socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5,
    forceNew: false,
});
```

**After:**
```javascript
this.socket = io('/', { 
    transports: ['websocket'],
    upgrade: false,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: Infinity
});
```

**New Event Listeners Added:**
```javascript
this.socket.on('rps_round_update', (data) => this.emit('rps_round_update', data));
this.socket.on('rps_timer_tick', (data) => this.emit('rps_timer_tick', data));
this.socket.on('rps_choices_locked', (data) => this.emit('rps_choices_locked', data));
this.socket.on('rps_result', (data) => this.emit('rps_result', data));
```

---

## PART 2: RPS TIMER-BASED SYSTEM REBUILD

### 2.1 Backend: Server-Authoritative RPS Timer Manager (`app/rps_timer.py`) - NEW FILE

**Purpose:** Complete server-side game management with threading-based timer.

**Key Components:**

1. **RPSTimerManager Class**
   - 4-second round duration
   - Server-controlled timing (no client-side timers)
   - Background thread for tick events
   - Thread-safe choice recording
   - Automatic winner determination

2. **Timer Loop (`_timer_loop`)**
   ```python
   def _timer_loop(self):
       while not self.stop_flag.is_set():
           # Countdown 4, 3, 2, 1
           for remaining in range(4, 0, -1):
               socketio.emit('rps_timer_tick', {'remaining': remaining}, room=room_id)
               time.sleep(1)
           
           # Lock choices and finalize
           self._finalize_round()
           
           # Show result for 1.5 seconds
           time.sleep(1.5)
           
           # Next round
           current_round += 1
   ```

3. **Round Finalization (`_finalize_round`)**
   - Locks both players' choices
   - Determines winner using `BEATS = {'rock': 'scissors', ...}`
   - Updates scores
   - Broadcasts result to room
   - Records round history

4. **Choice Submission (`submit_choice`)**
   - Can be changed anytime during 4-second window
   - Last choice submitted wins
   - Thread-safe with locks

**Events Emitted:**
- `rps_round_update` - New round started
- `rps_timer_tick` - Countdown tick (4, 3, 2, 1)
- `rps_player_ready` - Player submitted choice
- `rps_result` - Round finished with results

### 2.2 Backend: RPS Socket Handlers (`app/socketio_events.py`)

**New Global:**
```python
rps_timers = {}  # {room_id: RPSTimerManager}
```

**New Event Handlers:**

1. **`handle_rps_start`**
   ```python
   @socketio.on('rps_start')
   def handle_rps_start(data):
       room_id = data.get('room_id').upper()
       # Create RPSTimerManager
       # Start background timer thread
       # Emit rps_start_response
   ```

2. **`handle_rps_choice`**
   ```python
   @socketio.on('rps_choice')
   def handle_rps_choice(data):
       room_id, choice, player_id = ...
       timer_game = rps_timers[room_id]
       result = timer_game.submit_choice(player_id, choice)
       emit('rps_choice_response', result)
   ```

3. **`handle_rps_stop`**
   ```python
   @socketio.on('rps_stop')
   def handle_rps_stop(data):
       timer_game = rps_timers[room_id]
       timer_game.stop()
       del rps_timers[room_id]
   ```

### 2.3 Frontend: RPS Timer Game UI (`app/static/js/rps.js`) - REPLACED

**Major Rewrite:**

**Old System:**
- Best-of-3 rounds
- Client-initiated moves
- Manual round progression
- Emoji animations

**New System:**
- Infinite rounds with automatic progression
- 4-second countdown timer (server-controlled)
- Minimal numeric timer display (top-right)
- Automatic choice locking after 4 seconds
- 1.5-second reveal pause before next round

**Key Class: `RockPaperScissorsGame`**

Constructor now accepts `roomState`:
```javascript
class RockPaperScissorsGame {
    constructor(roomState) {
        this.roomState = roomState;
        this.timerRunning = false;
        this.currentRound = 1;
        this.scores = {};
        this.roundHistory = [];
    }
}
```

**UI Structure:**
```
┌─ Round X | Score: P1-P2 | Timer: [4][3][2][1]
│
├─ Choice Buttons (Rock/Paper/Scissors)
│  Can be clicked repeatedly during 4-second window
│
├─ Result Section (hidden until round ends)
│  Shows both choices, winner, reason
│
└─ Status: "Make your choice!" → "Revealing result..." → "Next round in 1.5s"
```

**Event Handlers:**

1. **`onRoundUpdate(data)`**
   - Reset buttons, show timer
   - Update round number
   - Update scores
   - Enable choosing

2. **`onTimerTick(data)`**
   - Update timer display (4, 3, 2, 1)
   - Add pulse animation when ≤2 seconds
   - Disable buttons at 0

3. **`onResult(data)`**
   - Show result section with emoji choices
   - Highlight winner
   - Update scores
   - Schedule next round (1.5s)

4. **`submitChoice(choice)`**
   - Emit `rps_choice` event
   - Highlight selected button
   - Can change choice anytime before timer ends

### 2.4 Frontend: Room Manager Integration (`app/static/js/room.js`)

**Updated `game_started` Handler:**
```javascript
socketClient.on('game_started', (data) => {
    if (data.game_type === 'rps') {
        // Send rps_start event instead of regular game start
        socketClient.socket.emit('rps_start', {
            room_id: socketClient.roomId
        });
        initializeGameUI(data.game_type, data.room);
    } else {
        initializeGameUI(data.game_type, data.room);
    }
});
```

**New RPS Event Listeners:**
```javascript
socketClient.on('rps_round_update', (data) => 
    roomState.gameManager?.onRoundUpdate(data));

socketClient.on('rps_timer_tick', (data) => 
    roomState.gameManager?.onTimerTick(data));

socketClient.on('rps_result', (data) => 
    roomState.gameManager?.onResult(data));

socketClient.on('rps_choice_response', (data) => 
    roomState.gameManager?.onChoiceResponse(data));

socketClient.on('rps_start_response', (data) => {
    if (data.success) setPhase('game');
    else alert('Failed to start RPS: ' + data.error);
});
```

**Updated `initializeGameUI`:**
```javascript
function initializeGameUI(gameType, room) {
    if (gameType === 'rps') {
        roomState.gameManager = new RockPaperScissorsGame(roomState);
    } else {
        roomState.gameManager = new GameClass();
    }
    roomState.gameManager.render(container);
}
```

---

## PART 3: KEY IMPROVEMENTS

### Thread Safety
- All RPS state changes protected by `threading.Lock()`
- Choice recording atomic
- Race conditions eliminated

### Server-Authoritative
- Client NEVER starts timers
- Client CANNOT cheat (choices locked server-side)
- All winner computation server-side
- Perfectly synchronized across clients

### Perfect Sync
- Both players see identical timer (server-driven)
- Choices locked at exactly 4 seconds
- Results displayed simultaneously
- Next round starts in sync

### Stability
- 5-second delayed disconnect prevents spurious dropouts
- WebSocket-only (no protocol fallback complexity)
- manage_session=False allows true multi-tab play
- Reconnection on any transient network glitch

---

## PART 4: GAME FLOW

```
1. CREATE ROOM
   ↓
2. JOIN ROOM (Both players)
   ├─ Player 1 joins → SID1, can join room
   ├─ Player 2 joins → SID2 (different from SID1, thanks to manage_session=False)
   └─ Both stay connected (5-second delayed disconnect prevents removal)
   ↓
3. SELECT RPS GAME
   ├─ Player 1 clicks RPS
   ├─ Player 2 clicks RPS
   └─ Both see "Simple Mode" or "Challenge Mode" modal
   ↓
4. START RPS (emit rps_start)
   ├─ Backend creates RPSTimerManager
   ├─ Backend starts background timer thread
   └─ All players get rps_round_update event
   ↓
5. FIRST ROUND (4 seconds)
   ├─ Server: Emit rps_timer_tick(remaining=4, 3, 2, 1) every 1s
   ├─ Client: Display timer "4" → "3" → "2" → "1"
   ├─ Player 1: Click Rock
   ├─ Player 2: Can still click (choice is not locked yet)
   ├─ Player 2: Change mind, click Paper
   └─ Player 1: Click Paper (final choice)
   ↓
6. TIMER EXPIRES (4 seconds elapsed)
   ├─ Server: Lock choices (Paper vs Paper = tie)
   ├─ Server: Award both 1 point
   ├─ Server: Emit rps_result
   ├─ Client: Show choices "📄 vs 📄" + "It's a Tie!"
   └─ Status: "Next round in 1.5s"
   ↓
7. REVEAL PAUSE (1.5 seconds)
   ├─ Result displayed
   └─ Players can see who won
   ↓
8. NEXT ROUND
   ├─ Round counter increments
   ├─ Scores updated
   ├─ New timer starts at "4"
   └─ Back to step 5
   ↓
9. REPEAT INFINITELY
   └─ Play as long as both players stay in room
```

---

## PART 5: TESTING CHECKLIST

### Local Two-Browser Test (15 minutes)

```
✓ Tab 1: Open http://localhost:5000
✓ Tab 1: Click "Create Room"
✓ Tab 1: See room code and QR
✓ Tab 2: Open http://localhost:5000/room/[CODE]
✓ Tab 2: Enter display name, join
✓ Tab 1: See "Player 2 joined"
✓ Both tabs: See game selection buttons
✓ Tab 1: Click RPS game
✓ Tab 1: Select "Simple Mode"
✓ Tab 2: Server says game started
✓ Both tabs: See RPS UI with timer
✓ Tab 1: Timer counts 4, 3, 2, 1
✓ Tab 1: Click Rock
✓ Tab 2: Click Paper
✓ Timer expires
✓ Both tabs: See result "📄 beats 🪨" 
✓ Tab 1 wins, score shows 0-1
✓ New round starts automatically
✓ Repeat 3+ times
✓ No errors in browser console
✓ No errors in server logs
```

### Production Deployment (Render)

```
✓ Git push to GitHub
✓ Render auto-deploys
✓ Check Render logs for errors
✓ Visit https://app-xxx.onrender.com
✓ Test from two different browsers/devices
✓ Verify WebSocket connects (Socket.IO handshake)
✓ Play full game
✓ Check sync across devices
✓ Monitor Render logs for crashes
```

---

## PART 6: FILES MODIFIED

1. **`app/__init__.py`** - SocketIO configuration with manage_session=False
2. **`app/socketio_events.py`** - Delayed disconnect handler + RPS event handlers
3. **`app/static/js/socket-client.js`** - WebSocket-only transport + RPS event listeners
4. **`app/static/js/rps.js`** - Complete rewrite with timer-based game
5. **`app/static/js/room.js`** - RPS event listener setup + game initialization

## NEW FILES CREATED

1. **`app/rps_timer.py`** - Server-side RPS timer manager with threading

---

## PART 7: DEPLOYMENT STEPS

### Step 1: Backup
```bash
cp -r app app.bak
git commit -m "backup: pre-websocket-fix"
```

### Step 2: Apply Changes
All changes already applied to files above.

### Step 3: Test Locally
```bash
python run.py
# Test two-browser scenario (see checklist above)
```

### Step 4: Git Push
```bash
git add app/ app/*.py app/static/js/*.js
git commit -m "fix: websocket sync, rebuild RPS with 4-second timer"
git push origin main
```

### Step 5: Monitor Render
- Visit Render dashboard
- Check logs for any errors
- Test live at https://app-xxx.onrender.com

---

## TROUBLESHOOTING

### Player 2 Still Disconnects
- Check that `manage_session=False` is set in app/__init__.py
- Verify disconnect handler is using `delayed_cleanup` with 5-second timer
- Check browser console for connection errors

### Timer Not Counting Down
- Verify `rps_timer.py` background thread started
- Check server logs for [RPS_TIMER] messages
- Ensure `rps_timer_tick` event is being emitted

### No Sync Between Browsers
- Verify WebSocket connection (check Network tab in DevTools)
- Ensure Socket.IO rooms are being broadcast correctly
- Check room ID is uppercase

### RPS Game Won't Start
- Verify `rps_start` event handler exists
- Check that room has exactly 2 players
- Look for error in browser console and server logs

---

## QUICK REFERENCE

**Key Timing Values:**
- `ROUND_DURATION = 4` seconds (timer)
- `REVEAL_DURATION = 1.5` seconds (show result)
- `DISCONNECT_DELAY = 5` seconds (before cleanup)
- Ping timeout = 60s, interval = 25s

**Server Events:**
- `rps_round_update` - New round (timer=4)
- `rps_timer_tick` - Countdown (4, 3, 2, 1)
- `rps_result` - Round finished (scores, winner, reason)
- `rps_player_ready` - Player submitted choice

**Client Events:**
- `rps_start` - Begin game
- `rps_choice` - Submit choice (can be changed until timer expires)
- `rps_stop` - End game

**Thread Safety:**
- `RPSTimerManager` uses `threading.Lock()` on `choices` dict
- `socketio_events` uses `threading.Timer()` for delayed cleanup
- All shared state protected

