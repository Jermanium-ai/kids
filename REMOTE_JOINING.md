# Remote Connection Troubleshooting

## Issue: "Room Not Found" When Joining from Another Device

### Root Causes

1. **Socket.IO Connection Failure (502/400 errors)**
   - Server not accessible from remote device
   - CORS misconfigured
   - WebSocket protocol blocked
   - Polling fallback not working

2. **Room Expired**
   - Room created >24 hours ago
   - Room deleted after last player left
   - Server restarted and room storage corrupted

3. **Network Issues**
   - Device on different network
   - Firewall blocking connection
   - Incorrect URL in QR code

### Fixes Applied (v2)

✅ **Enhanced Socket.IO Configuration**
```python
# In app/__init__.py
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    transports=['websocket', 'polling'],  # ← Both fallbacks now enabled
    reconnection: true,
    reconnectionAttempts: 5,
)
```

✅ **Improved Client Connection**
```javascript
// In socket-client.js
this.socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5,
});
```

✅ **Better Error Messages**
- Console logs now show exactly what's happening
- Join failures display detailed error messages
- Connection state verified before joining

✅ **Connection Resilience**
- Auto-reconnect if connection drops
- Retry logic if Socket not ready
- Fallback from WebSocket to polling

## How to Test Remote Joining

### Setup

1. **Start the server locally**
   ```bash
   python run.py
   ```

2. **Get your local IP**
   ```bash
   # On Windows PowerShell
   (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -eq "Ethernet" -or $_.InterfaceAlias -eq "Wi-Fi"}).IPAddress
   ```
   Example: `192.168.1.100`

3. **Create a room on desktop**
   - Open `http://192.168.1.100:5000` (or your IP)
   - Click "Create Room"
   - Note the room ID (e.g., `RH8DMZ2V`)

### Test 1: Same Network (Mobile)

1. **On mobile device (same WiFi)**
   - Open `http://192.168.1.100:5000` (replace IP)
   - Click "Join Room"
   - Enter the room ID
   - Expected: ✅ Join succeeds, you see Player 2 slot

**If fails:**
- Check mobile and desktop are on same WiFi
- Try refreshing the page
- Check mobile browser console for errors (F12)

### Test 2: Different Network (Simulated)

1. **On desktop, open DevTools** (F12)
2. **Go to Network tab**
3. **Throttle connection**: Set to "Slow 3G" or "Offline"
4. **Try to join a room**
5. **Expected**: Either join succeeds after a delay, or clear error message

**If fails:**
- Check console for connection errors
- Check if polling is being used as fallback
- Verify CORS headers are present

### Test 3: Render Deployment

1. **Deploy to Render** (git push)
2. **Get your Render app URL** (e.g., `https://kids-1-13um.onrender.com`)
3. **Create room on desktop**
4. **Join on mobile via shared link or QR code**

**If fails:**
- Check Render logs for Socket.IO errors
- Verify the URL in QR code matches Render domain
- Check that `rooms_data.json` persists between requests

## Common Error Messages

### "Connected to server: 9u4Pp5ulxW0e-JDAAAB" but then "Disconnected from server"

**Problem**: WebSocket connection starts but fails

**Solutions**:
1. Check if WebSocket port is open (usually same as HTTP port on deployment)
2. Try forcing polling: Add `?transport=polling` to debug
3. Check server logs for connection errors

### "Failed to load resource: the server responded with a status of 502"

**Problem**: Reverse proxy/load balancer issues

**Solutions**:
1. On Render: Contact support, may need to enable HTTP/2
2. Ensure gunicorn is running with threading (not eventlet)
3. Check that Flask app isn't crashing

### "Failed to load resource: the server responded with a status of 400"

**Problem**: Invalid request to Socket.IO server

**Solutions**:
1. Check the room ID is exactly correct (8 uppercase letters)
2. Verify CORS headers: Server should return `Access-Control-Allow-*`
3. Try a fresh reload (Ctrl+Shift+R)

## Debugging Steps

### Step 1: Check Console Logs

```javascript
// In browser console (F12 → Console tab)
socketClient.socket.connected         // Should be true
socketClient.socket.transport         // Should be 'websocket' or 'polling'
socketClient.roomId                   // Should match room ID
```

### Step 2: Check Network Requests

```
1. Open DevTools (F12)
2. Go to Network tab
3. Filter by "socket.io"
4. Look for:
   - ✅ Green 200 responses = good
   - ❌ Red 502/400/404 = bad
   - 101 status = WebSocket upgrade successful
```

### Step 3: Check Server Logs

```bash
# Local development
# Watch terminal for messages like:
#   "Socket connected, joining room..."
#   "Joined room as: Player X"

# On Render
# Dashboard → Logs tab
# Filter for "Socket" or "join_room"
```

### Step 4: Check Room Persistence

```bash
# On local development
ls -la rooms_data.json
cat rooms_data.json | python -m json.tool

# On Render
# Rooms are stored but not visible in UI
# Verify by checking deployment logs during room creation
```

## Mobile Testing Tips

### iOS Safari

- Requires HTTPS on live deployments
- Local testing on same network works with HTTP
- Use Safari DevTools: Settings → Advanced → Show Develop menu

### Android Chrome

- Enable DevTools: Menu → More → Developer mode
- Open DevTools on connected PC: `chrome://inspect`
- Use Chrome Remote Debugging

### Common Mobile Issues

1. **Page keeps refreshing**
   - Check if browser is in low-power mode
   - Disable battery optimization for browser
   - Try a different browser

2. **QR code doesn't scan**
   - Ensure camera has permission
   - Try using QR code app instead of camera
   - Manually enter room ID instead

3. **Slow connection**
   - On 3G, polling may be slower than WebSocket
   - Normal - app still works just slightly delayed
   - Upgrade to 4G/5G for best experience

## Performance Metrics

### Expected Response Times

| Connection | WebSocket | Polling |
|-----------|-----------|---------|
| Local | <10ms | <50ms |
| Same network | <50ms | <100ms |
| Remote (Render) | <200ms | <500ms |
| 3G | <500ms | <1000ms |

### If Slower Than Expected

1. Check if WebSocket is being used (Network tab → WS protocol)
2. If stuck on polling, WebSocket may be blocked
3. Contact ISP or hosting provider if all tests pass locally

## Advanced: Force Polling

If WebSocket is persistently blocked, you can force polling:

```javascript
// In socket-client.js, modify connection:
this.socket = io({
    transports: ['polling'],  // Only polling
    reconnection: true,
    reconnectionDelayMax: 5000,
});
```

This trades latency for reliability but app still works.

## Still Not Working?

### Checklist

- [ ] Server running and accessible (`curl http://ip:5000`)
- [ ] Room ID is exactly correct (case-sensitive)
- [ ] Device is on same network (for local testing)
- [ ] Browser console has no errors
- [ ] Network tab shows Socket.IO requests
- [ ] Room hasn't expired (>24 hours old)
- [ ] Server logs show connection attempts
- [ ] Tried clearing browser cache (Ctrl+Shift+Delete)

### Create a Debug Report

If still stuck, provide:
1. Browser: Chrome / Safari / Firefox
2. Device: Desktop / Mobile (iOS / Android)
3. Network: WiFi / 4G / LAN
4. Error message from console
5. Server log output
6. `rooms_data.json` content (if accessible)

### Get Help

- Check `DEPLOYMENT.md` → Troubleshooting section
- Check Flask-SocketIO docs: https://flask-socketio.readthedocs.io
- Open GitHub issue with debug report
