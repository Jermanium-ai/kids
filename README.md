# PlaySync - Real-Time Multiplayer Gaming Platform

A production-ready, mobile-first web application for ephemeral two-player games. Create or join rooms, no login required. Built with Flask, Flask-SocketIO, and modern frontend tech.

## Features

- 🎮 **5 Playable Games**
  - Rock Paper Scissors (best of series)
  - Tic Tac Toe (turn-based strategy)
  - Reaction Time Duel (first to tap wins)
  - Quick Math Duel (first correct answer wins)
  - Would You Rather (compare preferences)

- 🔗 **Ephemeral Rooms**
  - Create rooms in one click
  - Share via link or QR code
  - **Persistent storage** - rooms survive app restarts on Render
  - Auto-expire after 24 hours of inactivity
  - Max 2 players per room

- ✨ **Modern UX**
  - Mobile-first responsive design
  - Teal theme with glassmorphism effects
  - Smooth animations with anime.js
  - Real-time sync via Socket.IO

- 🛡️ **Anti-Cheat Measures**
  - Server-side validation for all moves
  - Early tap detection in reaction games
  - Rate limiting to prevent spam
  - Secret reveal mechanics for fair play

- 💬 **Chat**
  - Ephemeral room-specific chat
  - No persistent message storage
  - Lightweight and real-time

- ♿ **Accessibility**
  - WCAG compliant contrast ratios
  - Large touch targets (48px minimum)
  - Keyboard-friendly controls
  - Optional haptic feedback

## Project Structure

```
PlaySync/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes.py            # Web routes (landing, room pages)
│   ├── socketio_events.py   # Socket.IO event handlers
│   ├── room_manager.py      # In-memory room & player management
│   ├── game_logic.py        # Game logic for each game type
│   ├── utils.py             # QR code, avatar, utility functions
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Tailwind + custom animations
│   │   ├── js/
│   │   │   ├── socket-client.js     # Socket.IO client wrapper
│   │   │   ├── landing.js           # Landing page logic
│   │   │   ├── room.js              # Room orchestration (main controller)
│   │   │   ├── rps.js               # RPS game UI
│   │   │   ├── tictactoe.js         # Tic Tac Toe game UI
│   │   │   ├── reaction.js          # Reaction game UI
│   │   │   ├── quickmath.js         # Quick Math game UI
│   │   │   └── would-you-rather.js  # Would You Rather game UI
│   │   └── images/          # (optional) game thumbnails, icons
│   └── templates/
│       ├── index.html           # Landing page
│       ├── room.html            # Game room (main page)
│       ├── room_not_found.html  # 404 error
│       └── room_expired.html    # 410 expiry page
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── Procfile                 # Heroku/Render deployment config
├── .env.example             # Environment variable template
└── README.md                # This file
```

## Installation

### Local Development

**Prerequisites:**
- Python 3.8+
- pip

**Steps:**

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/playsync.git
   cd playsync
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file** (optional)
   ```bash
   cp .env.example .env
   ```

5. **Run the application**
   ```bash
  # On Linux / macOS (use your venv's python)
  python run.py
   ```
   or
   ```bash
  # On Windows, use threading for dev (default):
  # PowerShell
  python run.py

  # Or manually set the env var:
  # Windows powershell
  $env:ASYNC_MODE='threading'; python run.py

  # You can also run in production-like mode with gunicorn (Linux/Render):
  gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 run:app
   ```

6. **Access the app**
   - Open [http://localhost:5000](http://localhost:5000) in your browser
   - Test on mobile by visiting `http://<your-local-ip>:5000` on your phone

## Deployment

### Render (Recommended)

1. **Push to GitHub** (if not already)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Connect to Render**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Environment:** Python
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn -w 1 run:app`
     - **Add Environment Variables:** None required for basic setup
   - Click "Create Web Service"

### Railway

1. **Connect repository**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub"
   - Select your repository

2. **Railway auto-detects Python**
   - Procfile is automatically used
   - Service is deployed

### Heroku (Legacy)

1. **Install Heroku CLI**
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku
   
   # Windows: Download from heroku.com/download
   ```

2. **Deploy**
   ```bash
   heroku login
   heroku create playsync
   git push heroku main
   heroku ps:scale web=1
   ```

3. **Monitor logs**
   ```bash
   heroku logs --tail
   ```

## Architecture

### Backend (Flask)

- **Room Manager** (`room_manager.py`)
  - Tracks all active rooms in memory
  - Manages player lifecycle (join, leave, disconnect)
  - Auto-expires inactive rooms
  - Thread-safe operations

- **Game Logic** (`game_logic.py`)
  - Base `GameManager` class for game implementations
  - Concrete managers for each game type
  - Server-side validation and state management
  - Extensible factory pattern for adding new games

- **Socket.IO Events** (`socketio_events.py`)
  - Handles real-time communication
  - Authoritative server validation
  - Prevents cheating via move validation
  - Broadcasts game state to clients

### Frontend

- **Socket.IO Client** (`socket-client.js`)
  - Wrapper around Socket.IO library
  - Event delegation pattern
  - Automatic reconnection handling

- **Room Controller** (`room.js`)
  - Orchestrates UI phase transitions (waiting → game_selection → game → results)
  - Coordinates between Socket.IO and game UIs
  - Manages player display and chat

- **Game UIs** (modular)
  - Each game is a separate class (e.g., `RockPaperScissorsGame`)
  - Implements `render()`, `onMoveResponse()`, `onGameEnded()` interface
  - Isolated game logic and UI state

## Adding New Games

### Step 1: Create game logic backend

Edit `app/game_logic.py`:

```python
class YourGameManager(GameManager):
    def __init__(self, room):
        super().__init__(room)
        # Initialize game state
    
    def start(self):
        # Setup game, initialize state_data
        self.room.current_game.state_data = { ... }
    
    def process_move(self, player_id, move_data):
        # Validate move, update state
        return {'valid': True/False, 'message': str}
    
    def is_game_complete(self):
        return bool  # True if game should end
    
    def get_results(self):
        return {'winner': player_id, ...}  # Game results
```

Add factory entry in `create_game_manager()`:
```python
elif game_type == GameType.YOUR_GAME or game_type == 'your_game':
    return YourGameManager(room)
```

### Step 2: Create game UI frontend

Create `app/static/js/your-game.js`:

```javascript
class YourGameUI {
    constructor() {
        // Initialize UI state
    }

    render(container, gameData) {
        // Render game UI
        container.innerHTML = `...`;
        // Attach event listeners
    }

    onMoveResponse(data) {
        // Handle move validation response
    }

    onMoveMade(data) {
        // Update UI when opponent moves
    }

    onGameEnded(results) {
        // Display game results
    }
}

window.YourGameUI = YourGameUI;
```

### Step 3: Wire up in room.html

1. Add script tag to `app/templates/room.html`:
   ```html
   <script src="{{ url_for('static', filename='js/your-game.js') }}"></script>
   ```

2. Register in `room.js`:
   ```javascript
   const gameClasses = {
       // ... existing games
       'your_game': YourGameUI
   };
   ```

3. Add to game selection UI (room.html, phase-game-selection):
   ```html
   <button class="game-select-btn bg-gradient-to-r from-color1-600 to-color2-600 p-4 rounded-xl" data-game="your_game">
       <div class="font-semibold">Your Game Name</div>
       <div class="text-sm">Description</div>
   </button>
   ```

### Step 4: Add enum entry

Update `app/room_manager.py`:

```python
class GameType(Enum):
    # ... existing
    YOUR_GAME = "your_game"
```

## Server-Side Validation

All game moves are validated server-side. Example:

```python
# Client submits move
socketClient.submitMove({ choice: "rock" })

# Server validates in game_logic.py
def process_move(self, player_id, move_data):
    choice = move_data.get('choice', '').lower()
    if choice not in self.VALID_MOVES:
        return {'valid': False, 'message': 'Invalid move'}
    # ... process
```

**Anti-Cheat Examples:**

- **Early tap detection** (Reaction game): Disqualify if tap before delay
- **Rate limiting**: Basic checks in socket handlers
- **Move validation**: Only accept valid moves for current game state
- **Secret reveals**: Accept choices, only reveal after both players submit

## Environment Variables

Create a `.env` file (or set in deployment platform):

```env
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=use-a-long-random-string-here
PORT=5000
ROOM_INACTIVITY_TIMEOUT=1200
DEBUG=False
```

## Performance Considerations

- **Room Storage**: In-memory only (no database required)
  - Rooms auto-expire after 20 minutes inactivity
  - Use SQLAlchemy for persistent logging (optional, see below)

- **Socket.IO Scaling**
  - Single eventlet worker suitable for ~100 concurrent rooms
  - For production scale: use Redis adapter and multiple workers
  - Example with Redis:
    ```python
    socketio = SocketIO(
        app,
        message_queue='redis://localhost:6379/0'
    )
    ```

- **Frontend Optimization**
  - Static assets served via CDN (Tailwind, anime.js from CDN)
  - Critical CSS inlined
  - JS modules loaded on-demand per game

## Optional: Persistent Session Logging

To store game results in SQLite:

1. **Install SQLAlchemy**:
   ```bash
   pip install Flask-SQLAlchemy
   ```

2. **Create models in `app/__init__.py`**:
   ```python
   from flask_sqlalchemy import SQLAlchemy
   db = SQLAlchemy()
   
   class GameSession(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       room_id = db.Column(db.String(8), index=True)
       game_type = db.Column(db.String(50))
       winner = db.Column(db.String(36))
       players = db.Column(db.JSON)
       created_at = db.Column(db.DateTime, default=datetime.utcnow)
   ```

3. **Log results in `socketio_events.py`**:
   ```python
   @socketio.on('game_ended')
   def log_game(data):
       session = GameSession(
           room_id=room_id,
           game_type=data.game_type,
           winner=data.results['winner'],
           players=...,
       )
       db.session.add(session)
       db.session.commit()
   ```

**Tradeoff**: Adds database complexity; omitted by default for minimal setup.

## Testing

### Manual Multi-Client Testing

1. **Two browsers locally**:
   - Browser 1: `http://localhost:5000`
   - Browser 2: `http://localhost:5000`
   - Create room in Browser 1, join in Browser 2

2. **Local + Mobile**:
   - Desktop: `http://localhost:5000`
   - Mobile: `http://<your-local-ip>:5000`
   - Scan QR code on desktop to join on phone

3. **Two devices**:
   - Share the deployed URL
   - One creates room, other joins via link or QR

### Automated Tests (Future)

```python
# tests/test_game_logic.py
import pytest
from app.game_logic import RockPaperScissorsManager

def test_rps_move_validation():
    # Test move validation
    pass

def test_rps_winner_determination():
    # Test winner logic
    pass
```

## Troubleshooting

### Socket.IO Connection Fails

**Problem**: "Failed to connect" message

**Solutions**:
- Check browser console for errors
- Ensure server is running on correct port
- Check firewall/proxy settings
- Verify CORS is enabled (already done in code)

### Room Expires Immediately

**Problem**: Room not found after creating

**Solutions**:
- Check `ROOM_INACTIVITY_TIMEOUT` setting (default 1200 = 20 min)
- Verify socket stays connected during test
- Check server logs for room cleanup messages

### Games Don't Sync

**Problem**: Players see different game states

**Solutions**:
- Verify both players joined room successfully
- Check Socket.IO rooms are correct (room_id matches)
- Ensure Socket.IO events are emitted with correct room parameter
- Check browser console for emit errors

## Browser Support

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support (iOS 13+)
- Opera: Full support

**Minimum requirements**:
- ES6 JavaScript support
- WebSocket support (for Socket.IO)
- CSS Grid and Flexbox

## Security Considerations

### Already Implemented

- ✅ No persistent user accounts (privacy-first)
- ✅ Server-side move validation (anti-cheat)
- ✅ HTTPS recommended in production
- ✅ CORS configured appropriately
- ✅ Socket.IO authentication via join_room event

### Recommendations for Production

- 🔒 Use environment variables for secrets (never hardcode)
- 🔒 Enable HTTPS on deployment (Render/Railway do this)
- 🔒 Set `secure: true` in Socket.IO config for HTTPS
- 🔒 Add rate limiting: `python-ratelimit` package
- 🔒 Monitor for abuse: track room creation per IP
- 🔒 Add CSRRF protection if adding mutations

Example rate limiting:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@main_bp.route('/api/create-room', methods=['POST'])
@limiter.limit("5 per minute")
def create_room_api():
    # ...
```

## Performance Optimization (Advanced)

### Reduce Bundle Size

```html
<!-- Instead of full Tailwind, use purged version -->
<link rel="stylesheet" href="https://cdn.tailwindcss.com?purge=true">
```

### Lazy Load Heavy Scripts

```javascript
// Load Three.js only if needed
function loadThreeJs() {
    if (!window.THREE) {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/three/build/three.min.js';
        document.head.appendChild(script);
    }
}
```

### Backend Optimization

```python
# Use gevent for even better concurrency
pip install gevent gevent-websocket

# Then run with gevent worker
gunicorn --worker-class gevent -w 4 run:app
```

## License

MIT License - feel free to use, modify, and distribute.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Future Enhancements

- [ ] Leaderboards (with cooldown expiry)
- [ ] Game statistics dashboard
- [ ] Custom game creation UI
- [ ] Voice chat integration
- [ ] Spectator mode (3rd player can watch)
- [ ] Themed backgrounds (Dark/Light/Custom)
- [ ] Reaction game stats (avg reaction time)
- [ ] Mobile app (React Native wrapper)

---

**Questions?** Open an issue on GitHub or check the code comments for more details.

**Built with ❤️ for real-time gaming.**
