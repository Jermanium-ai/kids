# PlaySync - Manual Test Plan

This document outlines how to manually test PlaySync functionality.

## Pre-Test Setup

1. Start the server:
   ```bash
   python run.py
   ```
   Server should run on `http://localhost:5000`

2. Open two browsers (or one browser + one incognito/private window):
   - Browser A: `http://localhost:5000` (Player 1)
   - Browser B: `http://localhost:5000` (Player 2)

## Test Scenarios

### 1. Room Creation & QR Code

**Steps:**
1. In Browser A, click "Create Room"
2. Browser A redirected to `/room/<ROOM_ID>`
3. Verify room code displays in top bar
4. Verify QR code is visible and downloadable
5. Verify "Copy" button works (copies room URL)

**Expected Results:**
- ✅ Room ID is 8 characters (uppercase alphanumeric)
- ✅ QR code is valid (scan with phone to get room URL)
- ✅ Room URL can be copied to clipboard

---

### 2. Player Join & Display

**Steps:**
1. Browser A already in room (from test 1)
2. Take room code (e.g., `ABC12345`)
3. In Browser B, click "Join Room"
4. Enter room code and press Join
5. Check both browsers display both players

**Expected Results:**
- ✅ Browser B redirects to same room URL
- ✅ Both browsers show 2 player slots filled
- ✅ Each player has unique display name, avatar color
- ✅ Player 1 shows "You" label in Browser A
- ✅ Players now see "Choose a Game" screen

---

### 3. Game Selection

**Steps:**
1. Both browsers now show game selection menu
2. In Browser A, click "Rock Paper Scissors"
3. Check game starts on both browsers

**Expected Results:**
- ✅ Game UI appears on both browsers
- ✅ Game title shows "Rock Paper Scissors"
- ✅ Each player can select rock/paper/scissors
- ✅ Chat section appears at bottom

---

### 4. Rock Paper Scissors - Full Round

**Steps:**
1. Browser A selects "Rock"
2. Browser B selects "Paper"
3. Both browsers reveal results
4. Wait for display update

**Expected Results:**
- ✅ Browser A shows: You selected Rock, Opponent selected Paper → You Lost
- ✅ Browser B shows: You selected Paper, Opponent selected Rock → You Won
- ✅ Scores update accordingly (Browser B: 1, Browser A: 0)
- ✅ New round starts automatically

---

### 5. Tic Tac Toe - Move Validation

**Steps:**
1. Go back to game selection, choose "Tic Tac Toe"
2. Browser A (X) clicks center square
3. Browser B (O) tries to click same square (should fail)
4. Browser B clicks different square
5. Continue game until win/draw

**Expected Results:**
- ✅ Browser A can place X on empty square
- ✅ Browser B cannot place O on occupied square (error message)
- ✅ Turn alternates between A ↔ B
- ✅ Win/draw detected correctly

---

### 6. Reaction Time Duel

**Steps:**
1. Choose "Reaction Time Duel" from game selection
2. Both players ready (wait for "NOW!" prompt)
3. Click TAP as fast as possible after green state
4. Check results

**Expected Results:**
- ✅ Screen shows ready state (takes 1-3 seconds)
- ✅ Both browsers show "NOW!" and turn green
- ✅ TAP button enabled only after delay
- ✅ Results show reaction times (milliseconds)
- ✅ Fastest time wins

---

### 7. Quick Math Duel

**Steps:**
1. Choose "Quick Math Duel"
2. Math question appears (e.g., "45 * 23")
3. One player submits correct answer first
4. Check results

**Expected Results:**
- ✅ Same question on both browsers
- ✅ First correct answer wins immediately
- ✅ Results show correct answer
- ✅ Loser sees "Wrong answer" if they entered incorrect

---

### 8. Would You Rather

**Steps:**
1. Choose "Would You Rather"
2. Two choice buttons appear (e.g., "Fly" vs "Invisible")
3. Each player selects one choice
4. Next round appears
5. After 3 rounds, game ends

**Expected Results:**
- ✅ Same question on both browsers
- ✅ Choices track for comparison
- ✅ Game shows round counter (1 of 3)
- ✅ After 3 rounds, results screen shows "Game Complete!"

---

### 9. Chat

**Steps:**
1. During any game, use chat section at bottom
2. Browser A: type "Hello Player 2!" and send
3. Check Browser B receives message with timestamp
4. Browser B replies

**Expected Results:**
- ✅ Messages appear with player name and color
- ✅ Messages are ephemeral (not persisted)
- ✅ Chat scrolls automatically
- ✅ Max 50 messages stored in UI

---

### 10. Rematch & Switch Game

**Steps:**
1. Game ends (any game)
2. Results screen appears with buttons
3. Click "Rematch" → same game starts again
4. Or click "Switch Game" → game selection menu

**Expected Results:**
- ✅ Rematch resets scores and starts fresh
- ✅ Switch Game keeps scores but shows selection menu
- ✅ Both players must see same state

---

### 11. Player Leave & Room Cleanup

**Steps:**
1. Browser B clicks "Leave" button (confirm dialog)
2. Check Browser A state

**Expected Results:**
- ✅ Browser B redirects to landing page
- ✅ Browser A shows single player
- ✅ If no game active, Browser A goes back to waiting
- ✅ Room still valid for rejoining or new player

---

### 12. Room Expiry

**Steps:**
1. Create room in Browser A
2. Wait 20+ minutes without activity (or modify `ROOM_INACTIVITY_TIMEOUT` to 60 seconds for testing)
3. Refresh room page

**Expected Results:**
- ✅ Room not found error OR expiry page
- ✅ Player redirected with appropriate message

---

### 13. QR Code Functionality

**Steps:**
1. Create room, copy QR code
2. On mobile phone, scan QR code with camera/QR scanner
3. Link opens in browser
4. Mobile joins room successfully

**Expected Results:**
- ✅ QR code is valid and scannable
- ✅ Mobile redirected to correct room URL
- ✅ Mobile player joins successfully

---

### 14. Mobile Responsiveness

**Steps:**
1. On desktop, open room on mobile viewport (Chrome dev tools)
2. Or use actual phone to access `http://<laptop-ip>:5000`
3. Test layout, button sizes, visibility

**Expected Results:**
- ✅ Layout stacks vertically on mobile
- ✅ Buttons are large enough to tap (48px minimum)
- ✅ Text is readable
- ✅ Game boards/cards scale appropriately
- ✅ No horizontal scroll needed

---

### 15. Error Handling

**Steps:**
1. Try to join non-existent room (e.g., `INVALID1`)
2. Try to join full room (create room A, B joins, C tries to join)
3. Close browser tab abruptly during game

**Expected Results:**
- ✅ Non-existent room shows error page
- ✅ Full room shows "Room is full" error
- ✅ Abrupt disconnect shows reconnection attempt (or graceful cleanup)

---

## Browser Console Checks

During tests, check browser console (F12) for:

- ❌ No JavaScript errors
- ❌ No CORS errors
- ✅ Socket.IO connection messages
- ✅ Event emit/receive logs
- No warnings about deprecated APIs

---

## Performance Checks

- **Fast page loads**: Landing page < 1s, room page < 1s
- **Smooth animations**: No jank or lag
- **Real-time sync**: Moves appear instantly on both clients
- **Memory**: Browser doesn't consume excessive memory over time

---

## Deployment Test Checklist

Before deploying to production:

- [ ] All manual tests pass locally
- [ ] No console errors in browser
- [ ] QR code generation works
- [ ] Chat ephemeral messages disappear properly
- [ ] Room cleanup works (test with short timeout)
- [ ] All 5 games are playable
- [ ] Mobile responsive layout works
- [ ] Haptic feedback on supported devices

---

## Known Limitations & TODOs

- [ ] Spectator mode (3rd player watching)
- [ ] Persistent leaderboards
- [ ] Custom player avatars (currently procedurally generated)
- [ ] Voice/video chat
- [ ] Game statistics per player
- [ ] Themed backgrounds (currently single dark theme)

---

## Quick Test Commands

```bash
# Run with short room timeout (for testing cleanup)
export ROOM_INACTIVITY_TIMEOUT=60  # 60 seconds instead of 1200
python run.py

# Test with multiple tabs (same browser)
# Tab 1: http://localhost:5000 (create room)
# Tab 2: http://localhost:5000 (join same room)

# Test on mobile (replace with your machine's IP)
# Phone: http://192.168.1.100:5000
```

---

**Total Test Time**: ~30 minutes for full coverage

**Happy Testing! 🎮**
