# PlaySync - Quick Start Guide

Get PlaySync running in 5 minutes locally or 10 minutes on a cloud platform.

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.8+ 
- pip (comes with Python)
- A modern web browser

### Installation (3 steps)

```bash
# 1. Clone/Download PlaySync
git clone https://github.com/yourusername/playsync.git
cd playsync

# 2. Set up Python environment
python -m venv venv

# Activate virtual environment:
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies and run
pip install -r requirements.txt
python run.py
```

Server runs on: **http://localhost:5000**

### Test It

1. Open browser tab 1: `http://localhost:5000`
2. Click "Create Room"
3. Open browser tab 2: `http://localhost:5000`
4. Click "Join Room", enter the room code
5. Pick a game and play!

---

## 🌐 Deploy to Cloud (10 minutes)

### Option 1: Render (Recommended)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial PlaySync"
   git push origin main
   ```

2. **Deploy on Render**
   - Visit [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Set:
     - Build: `pip install -r requirements.txt`
     - Start: `gunicorn -w 1 run:app`
   - Click "Create"
   - Wait ~3 minutes for deployment

3. **Share the URL** that Render provides

### Option 2: Railway

1. **Push to GitHub** (same as Render step 1)

2. **Deploy on Railway**
   - Visit [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub"
   - Select repo → Railway auto-deploys
   - Copy the provided URL

3. **Share the URL**

### Option 3: Heroku

1. **Install Heroku CLI** from [heroku.com/download](https://heroku.com/download)

2. **Deploy**
   ```bash
   heroku login
   heroku create playsync
   git push heroku main
   heroku ps:scale web=1
   ```

3. **Get your URL**
   ```bash
   heroku apps:info
   ```

---

## 📱 Access on Mobile

### Local Network
- On phone/tablet, visit: `http://<your-computer-ip>:5000`
- Find your IP: run `ipconfig` (Windows) or `ifconfig` (Mac/Linux)

### Cloud (Render/Railway/Heroku)
- Simply visit the provided URL from your phone
- Scan QR codes to join rooms

---

## 🎮 First Game

1. **Player 1** (Browser A):
   - Click "Create Room"
   - Copy link or scan QR code

2. **Player 2** (Browser B / Phone):
   - Paste link or scan QR code to join

3. **Both players**:
   - Select "Rock Paper Scissors"
   - Make your choice
   - See results instantly

Try all 5 games!

---

## 🛠️ Configuration

### Change Room Timeout

Edit `.env` (or create from `.env.example`):
```env
ROOM_INACTIVITY_TIMEOUT=1200  # 20 minutes (default)
```

Set to `60` for testing (rooms expire after 1 minute).

### Change Secret Key (Production Only)

```bash
# Generate random secret
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env or deployment platform
SECRET_KEY=<generated-string>
```

---

## 📚 Documentation

- **README.md** - Full docs, architecture, extension guide
- **DEPLOYMENT.md** - Detailed deployment instructions
- **TESTING.md** - Manual test plan
- **PROJECT_SUMMARY.md** - What's included and how it works

---

## 🎯 Common Tasks

### Add a New Game

1. **Add backend logic** in `app/game_logic.py`:
   ```python
   class MyGameManager(GameManager):
       def start(self): ...
       def process_move(self, player_id, move): ...
       def get_results(self): ...
   ```

2. **Add game enum** in `app/room_manager.py`:
   ```python
   class GameType(Enum):
       MY_GAME = "my_game"
   ```

3. **Add frontend UI** in `app/static/js/my-game.js`:
   ```javascript
   class MyGameUI {
       render(container, gameData) { ... }
       onGameEnded(results) { ... }
   }
   ```

4. **Add to game selection** in `app/templates/room.html` and `static/js/room.js`

### Change Colors

Edit `app/static/css/style.css`:
```css
:root {
    --teal-500: #YOUR_COLOR_HERE;
    --teal-600: #YOUR_COLOR_HERE;
}
```

### Debug Issues

```bash
# Check logs (Render/Railway/Heroku)
# Dashboard → Logs (in UI)

# Or locally
python run.py  # Shows errors in terminal
```

---

## ✅ Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Make sure `python run.py` is running |
| Room not found after 20 min | Rooms auto-expire (set `ROOM_INACTIVITY_TIMEOUT`) |
| QR code not loading | Check internet connection, reload page |
| Second player can't join | Create new room, refresh page |
| Heroku app crashes | Check: `heroku logs --tail` |
| Render deployment failed | Check build logs in dashboard |

---

## 🚢 Deploy to Production

**All platforms support:**
- ✅ HTTPS (automatic)
- ✅ Custom domains
- ✅ Free tier (limited)
- ✅ Auto-scaling
- ✅ Environment variables

**Upgrade when needed** for better performance/storage.

---

## 📞 Support

- **GitHub Issues**: Post questions/bugs
- **Check Docs**: README.md has detailed info
- **Test Locally**: Run `python run.py` to debug
- **Code Comments**: All code is well-documented

---

## 🎉 You're Ready!

Pick a deployment method above and launch PlaySync for your friends!

Questions? Check:
1. README.md (full documentation)
2. DEPLOYMENT.md (platform-specific help)
3. TESTING.md (how to test locally)
4. Inline code comments

**Happy gaming! 🎮**

---

## Quick Command Reference

```bash
# Local development
python -m venv venv          # Create environment
source venv/bin/activate     # Activate (Linux/Mac)
venv\Scripts\activate        # Activate (Windows)
pip install -r requirements.txt
python run.py                # Run server

# Git
git init
git add .
git commit -m "Message"
git push origin main         # Push to GitHub

# Heroku
heroku login
heroku create app-name
git push heroku main
heroku ps:scale web=1
heroku logs --tail
```

---

**Next Step**: Pick deployment option or start playing locally!
