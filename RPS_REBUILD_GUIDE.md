# RPS Game System Rebuild - Complete Integration Guide

## 🎯 Overview

This is a **complete rebuild of the RPS game system** with:
- ✅ Server-authoritative 4-second timer (no "best of N")
- ✅ Fixed `currentGame` undefined crash
- ✅ Minimal, modern UI with timer in top-right
- ✅ Proper round management with 1.5s reveal pause
- ✅ Thread-safe background timer on server
- ✅ Client never controls timing (server authoritative)

---

## 📁 Files Created/Modified

### NEW FILES TO DEPLOY

```
app/
  ├── rps_manager.py                    (NEW - Server-side RPS manager)
  └── socketio_events_rps.py            (NEW - Socket.IO handlers for RPS)

app/static/js/
  ├── rps_new.js                        (NEW - RPS game UI class)
  ├── socket-client-rps.js              (NEW - Socket client wrapper)
  └── room_rps.js                       (NEW - Room manager with RPS fix)

app/static/css/
  └── rps_timer.css                     (NEW - Timer and game styles)
```

### FILES TO KEEP UNCHANGED

```
app/static/js/
  ├── landing.js                        (Existing - Keep)
  ├── socket-client.js                  (Existing - Will use new version)
  ├── room.js                           (Existing - Will use new version)
  ├── rps.js                            (Existing - Will replace)
  └── [other games]                     (Keep for now)

app/
  ├── socketio_events.py                (Existing - Will merge new handlers)
  ├── game_logic.py                     (Existing - Keep for non-RPS games)
  ├── room_manager.py                   (Existing - Keep)
  └── [other files]                     (Keep)
```

---

## 🔧 INTEGRATION STEPS

### Step 1: Update app/__init__.py

Add imports at the top:

```python
from app.rps_manager import RockPaperScissorsManager
```

The rest stays the same.

---

### Step 2: Update app/socketio_events.py

Replace the entire file with `socketio_events_rps.py` content, OR merge by:

1. **Keep existing imports and setup** from current socketio_events.py
2. **Replace RPS-specific handlers** with handlers from socketio_events_rps.py:
   - `handle_start_game()` - Updated to detect RPS and use new manager
   - `handle_rps_choose()` - NEW handler for RPS choice submission
   - `handle_game_move()` - Keep for non-RPS games

**Recommended**: Copy entire `socketio_events_rps.py` to replace `socketio_events.py`

---

### Step 3: Add rps_manager.py

Copy `app/rps_manager.py` as-is to the app folder.

---

### Step 4: Update Frontend Files

### In `app/static/js/`:

1. **socket-client.js** → Replace with `socket-client-rps.js`
   - Adds `rpsChoose()` method
   - Keeps all existing methods

2. **room.js** → Replace with `room_rps.js`
   - **CRITICAL FIX**: Ensures `roomState.currentGame` is set BEFORE initializing game UI
   - Adds RPS-specific event listeners (tick, new_round, reveal_result)
   - All other game types continue to work

3. **rps.js** → Replace with `rps_new.js`
   - Complete rewrite for timer-based system
   - No more "best of N" logic
   - Minimal timer display in top-right

### In `app/static/css/`:

4. Add `rps_timer.css` - New CSS file for timer and button styles

---

### Step 5: Update HTML Template

In `app/templates/room.html`, add these includes in the `<head>` or before `</body>`:

```html
<!-- RPS New Timer System CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/rps_timer.css') }}">

<!-- Socket Client -->
<script src="{{ url_for('static', filename='js/socket-client-rps.js') }}"></script>

<!-- Game Classes (in order) -->
<script src="{{ url_for('static', filename='js/rps_new.js') }}"></script>
<script src="{{ url_for('static', filename='js/tictactoe.js') }}"></script>
<script src="{{ url_for('static', filename='js/reaction.js') }}"></script>
<script src="{{ url_for('static', filename='js/quickmath.js') }}"></script>
<script src="{{ url_for('static', filename='js/would-you-rather.js') }}"></script>

<!-- Room Manager (must be last) -->
<script src="{{ url_for('static', filename='js/room_rps.js') }}"></script>

<!-- Optional: Logger -->
<script>
    window.logger = {
        info: (msg) => console.log('[LOG]', msg),
        warn: (msg) => console.warn('[WARN]', msg),
        error: (msg) => console.error('[ERROR]', msg)
    };
</script>
```

---

## 🚀 HOW IT WORKS

### Server Side (Python)

1. **Player 1 and 2 join room** → Go to game_selection phase
2. **Select RPS game** → `start_game_request` emitted
3. **Server creates RockPaperScissorsManager** → Calls `.start()`
4. **Manager starts background timer thread** that:
   - Emits `rps:tick` with remaining seconds (4, 3, 2, 1)
   - Detects 4s expiry
   - Calls `_finalize_and_next_round()` which:
     - Locks choices
     - Computes winner
     - Emits `rps:reveal_result`
     - Schedules next round in 1.5s

### Client Side (JavaScript)

1. **Listen for `rps:tick`** → Update timer display
2. **Listen for `rps:new_round`** → Reset UI, enable buttons
3. **Listen for `rps:reveal_result`** → Show choices, highlight winner
4. **Player clicks choice** → Emit `rps:choose` to server
5. **Loop back to step 1** for next round

### Key Fixes

- ✅ **currentGame undefined**: `room_rps.js` sets `roomState.currentGame` BEFORE creating game manager
- ✅ **Best of N removed**: Timer-based system, no round counting
- ✅ **Timer authority**: Server emits ticks, clients never control timing
- ✅ **Round synchronization**: Both players see same choices via `reveal_result` event

---

## 🧪 TESTING CHECKLIST

### Local Testing (Before Deployment)

- [ ] Start server: `python run.py`
- [ ] Open 2 browser windows to http://localhost:5000
- [ ] Window 1: Create room
- [ ] Window 2: Join room via link
- [ ] Both select RPS → Simple mode
- [ ] **Verify**:
  - [ ] Timer counts down (4, 3, 2, 1)
  - [ ] Can click choices during countdown
  - [ ] Choices can be changed during countdown
  - [ ] Timer reaches 0 and freezes
  - [ ] Both choices shown side-by-side
  - [ ] Winner highlighted
  - [ ] After 1.5s, new round starts automatically
  - [ ] Play 3+ rounds with no errors
  - [ ] No "currentGame undefined" errors in console
  - [ ] Scores accumulate across rounds

### Console Debugging

- [ ] Check browser console for `[LOG]` messages
- [ ] No `[ERROR]` messages
- [ ] Verify RPS events are received

---

## 🐛 TROUBLESHOOTING

### Timer Not Counting Down

**Problem**: Timer shows "4" but doesn't count

**Solution**: 
- Check server is emitting `rps:tick` events
- Verify socket connection is active
- Check `onTick()` method is being called

### "currentGame undefined" Error

**Problem**: Game crashes when starting RPS

**Solution**:
- Ensure `room_rps.js` is loaded (not old `room.js`)
- Check `roomState.currentGame` is set before `initializeGameUI()`
- See line in room_rps.js: `roomState.currentGame = data.game_type;` (BEFORE initialization)

### Choices Not Registering

**Problem**: Click choice but nothing happens

**Solution**:
- Verify `rps_new.js` is loaded (not old `rps.js`)
- Check `timerRunning` flag is true
- Verify `rps:choose_response` is received from server
- Check server logs for choice recording

### Next Round Never Starts

**Problem**: After reveal, no new round begins

**Solution**:
- Check server is emitting `rps:new_round` event after 1.5s delay
- Verify `onNewRound()` is calling `startRound()`
- Check background thread is still running (no exceptions)

---

## 📊 ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Client)                    │
│                                                         │
│  room_rps.js                                           │
│  ├─ Listens for 'game_started'                         │
│  ├─ Creates RockPaperScissorsGame instance            │
│  └─ Relays socket events to game manager              │
│                                                         │
│  rps_new.js (RockPaperScissorsGame class)             │
│  ├─ render() - Shows buttons, timer                   │
│  ├─ onTick(remaining) - Update timer text             │
│  ├─ submitChoice() - Emit rps:choose                  │
│  ├─ revealResult() - Show result                      │
│  └─ onNewRound() - Reset for next round               │
│                                                         │
└──────────────────────────────────────────────────────────┘
                          ↕ Socket.IO
                  (4 events: tick, new_round,
                   reveal_result, choose)
                          ↕
┌──────────────────────────────────────────────────────────┐
│              Server (Flask-SocketIO)                     │
│                                                          │
│  socketio_events_rps.py                                 │
│  ├─ handle_start_game() - Create RPS manager           │
│  └─ handle_rps_choose() - Record choice                │
│                                                          │
│  rps_manager.py (RockPaperScissorsManager class)        │
│  ├─ start() - Begin first round                        │
│  ├─ _start_timer_loop() - Background thread            │
│  │  └─ Emits tick, detects expiry, finalizes          │
│  ├─ record_choice() - Store choice                     │
│  └─ _finalize_and_next_round() - Compute winner       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] All files copied to correct locations
- [ ] No file name conflicts with old RPS system
- [ ] HTML template updated with new script includes
- [ ] CSS file included in HTML template
- [ ] No import errors when starting server

### Testing

- [ ] Local testing passes all checks
- [ ] Console is clean (no errors)
- [ ] Scores accumulate correctly
- [ ] Multiple rounds work
- [ ] Two clients in sync

### Deployment to Render

- [ ] Push to GitHub
- [ ] Render auto-deploys
- [ ] Test link/QR joining
- [ ] Test RPS gameplay
- [ ] Monitor logs for errors

---

## 🎁 DELIVERABLES SUMMARY

### Code Quality
- ✅ Production-ready Python with thread safety
- ✅ Clean JavaScript with error handling
- ✅ Minimal CSS (no bloat)
- ✅ Comprehensive logging

### Functionality
- ✅ Server-authoritative timer (no client cheating)
- ✅ 4-second countdown + 1.5s reveal pause
- ✅ Automatic next round (no user interaction)
- ✅ Changed choices during countdown (last choice counts)
- ✅ Proper winner computation
- ✅ Score accumulation across rounds

### Fixes
- ✅ `currentGame` undefined crash - FIXED
- ✅ "Best of N" logic - REMOVED
- ✅ Old round flow - CLEANED UP
- ✅ Client-side timer control - REMOVED

---

## 🚀 GO LIVE

Once integration is complete:

1. Run local tests (all pass)
2. Commit and push to GitHub
3. Render auto-deploys
4. Test on live URL
5. Monitor error logs
6. Celebrate! 🎉

---

**Questions?** See detailed code comments in each file.

**Need rollback?** Keep old `rps.js`, `room.js`, `socket-client.js` backed up.
