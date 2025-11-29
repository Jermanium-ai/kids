# PlaySync - Deployment Guide

Quick deployment instructions for Render, Railway, and Heroku.

## Render (Recommended)

Render is free-tier friendly and handles Flask + Socket.IO well.

### Step 1: Prepare GitHub Repository

```bash
cd playsync
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/playsync.git
git push -u origin main
```

### Step 2: Create Render Service

1. Sign up at [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Select "Deploy an existing repository"
4. Search for `playsync` and connect
5. Fill in form:

| Field | Value |
|-------|-------|
| **Name** | playsync |
| **Environment** | Python 3 |
| **Region** | closest to users (e.g., us-east-1) |
| **Branch** | main |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -w 1 --bind 0.0.0.0:$PORT run:app` |
| **Plan** | Free (0.5 CPU, 512MB RAM) or Paid for better performance |

6. Click "Create Web Service"
7. Wait for build to complete (~3-5 min)
8. Copy the provided URL (e.g., `https://playsync-xxx.onrender.com`)

**Note:** The app uses threading-based async mode which works reliably with standard gunicorn sync worker and is compatible with all deployment platforms.

### Using `render.yaml` (optional)

If you'd like to store Render service configuration in the repo and use Infrastructure-as-Code, add a `render.yaml` (example included in repo) and connect the repo in the Render dashboard - Render will use that file to create the same service.


### Step 3: Add Gunicorn to requirements.txt

```
gunicorn==21.2.0
```

then push:

```bash
git add requirements.txt
git commit -m "Add gunicorn"
git push origin main
```

Render will auto-redeploy.

---

## Railway

Simple and modern deployment platform.

### Step 1: Connect GitHub

1. Sign up at [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Grant Railway access to your GitHub account
4. Select `playsync` repository

### Step 2: Configure Environment

Railway auto-detects Python and reads Procfile.

Optional environment variables (Settings → Variables):

```
SECRET_KEY=your-random-secret-string
FLASK_ENV=production
```

### Step 3: Deploy

1. Railway auto-builds and deploys when you push to GitHub
2. View deployment status in Railway dashboard
3. Get public URL under "Deployments"

---

## Heroku (Legacy)

### Step 1: Install Heroku CLI

**macOS:**
```bash
brew tap heroku/brew && brew install heroku
```

**Windows:**
- Download from [heroku.com/download](https://heroku.com/download)

**Linux:**
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

### Step 2: Login

```bash
heroku login
```

Opens browser for authentication.

### Step 3: Create App

```bash
heroku create playsync
```

or for custom domain:

```bash
heroku create your-custom-name
```

### Step 4: Deploy

```bash
git push heroku main
```

### Step 5: Scale

```bash
heroku ps:scale web=1
```

### Step 6: Monitor

```bash
# View logs
heroku logs --tail

# View app URL
heroku apps:info

# Set environment variables
heroku config:set SECRET_KEY=your-secret
```

---

## Post-Deployment Checklist

After deploying to any platform:

### 1. Test Functionality

- [ ] Visit root URL (should show landing page)
- [ ] Create room
- [ ] Generate QR code
- [ ] Test on mobile via QR scan
- [ ] Join room from second browser
- [ ] Start a game
- [ ] Play through to completion
- [ ] Check chat works

### 2. Monitor Performance

```bash
# Check for errors
# Render: Dashboard → Logs
# Railway: Dashboard → Logs
# Heroku: heroku logs --tail
```

Look for:
- Socket.IO connection errors
- Database errors (if using SQLAlchemy)
- Unhandled exceptions

### 3. Set Production Variables

For all platforms, set:

```
SECRET_KEY=<long-random-string>
FLASK_ENV=production
DEBUG=false
```

**Generate SECRET_KEY:**
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Enable HTTPS

All platforms automatically use HTTPS for deployed apps:
- ✅ Render: HTTPS by default
- ✅ Railway: HTTPS by default
- ✅ Heroku: HTTPS by default (with free SSL certificate)

Update Socket.IO config for HTTPS if needed:

```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    async_mode='threading',
    # Add for HTTPS
    # secure=True,
    # engineio_logger=True,
)
```

---

## Scaling for Production

### Single-Server Setup (Current)

- ✅ In-memory room storage
- ✅ Single worker with threading support
- ✅ Suitable for: ~100 concurrent rooms, ~200 concurrent users
- Deployment: Any platform

### Multi-Server Setup

For >100 concurrent rooms, need:

1. **Redis for session store**

Edit `app/__init__.py`:

```python
socketio = SocketIO(
    app,
    message_queue='redis://your-redis-url',
    cors_allowed_origins="*",
)
```

2. **Database for room persistence**

```python
# Use SQLAlchemy instead of in-memory
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Room(db.Model):
    room_id = db.Column(db.String(8), primary_key=True)
    # ... other fields
```

3. **Multiple workers**

Update Procfile:

```
web: gunicorn -w 1 --bind 0.0.0.0:$PORT run:app
```

4. **CDN for static files**

Deploy static/ to S3 or similar:

```python
# Example with AWS S3
from flask_s3 import FlaskS3
s3 = FlaskS3(app)

# Then use {{ url_for('static', filename='...') }}
```

**Cost estimate:**
- Render Pro: $7/month
- Railway usage-based: ~$10-20/month
- Redis add-on: ~$15/month
- S3 storage: ~$0.10/month (for small deployments)

---

## Custom Domain Setup

### Render

1. Go to Service → Settings
2. Add Custom Domain
3. Point DNS to Render nameservers

### Railway

1. Project → Settings → Custom Domain
2. Add your domain
3. CNAME record to Railway

### Heroku

```bash
heroku domains:add playsync.yourdomain.com
```

Then update DNS CNAME:
```
playsync.yourdomain.com CNAME playsync-xxx.herokuapp.com
```

---

## Troubleshooting Deployment

### App keeps crashing

Check logs for errors:

```bash
# Render
# Dashboard → Logs (in UI)

# Railway  
# Dashboard → Logs (in UI)

# Heroku
heroku logs --tail
```

Common issues:
- Missing `gunicorn` in requirements.txt
- Import errors (missing dependencies)
- Syntax errors in code

**Fix:**
```bash
git log --oneline  # Check last commit
git diff HEAD~1    # See what changed
pip install -r requirements.txt  # Test locally
python run.py      # Test locally
```

### Socket.IO connection fails

Browser shows "Failed to connect"

**Causes:**
- Server not running
- CORS misconfigured
- WebSocket protocol not supported
- Firewall blocking WebSocket

**Debug:**
1. Check deployment logs for errors
2. Verify CORS in browser console
3. Check Network tab → WS protocol
4. Contact platform support if WebSocket blocked

### Room data lost after deploy

**Normal behavior:** In-memory rooms cleared on restart

To persist data:
```python
# Use SQLAlchemy (see scaling section above)
```

---

## Free Tier Limits

| Platform | CPU | RAM | Bandwidth | Sleep | Cost |
|----------|-----|-----|-----------|-------|------|
| **Render** | 0.5 | 512MB | Unlimited | ❌ No (spins down if no traffic) | Free* |
| **Railway** | Metered | ~512MB | 100GB/mo | ❌ No | Free** |
| **Heroku** | Shared | 512MB | Unlimited | ✅ Yes (after 30 min idle) | Free |

\* Render spins down free instances after 15 minutes, cold start ~30 sec
\** Railway more generous free tier, great for hobby projects

**Recommendation:** Use Render or Railway free tier to start. Upgrade if needed.

---

## CI/CD Pipeline (Optional)

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Render
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

Then set `RENDER_DEPLOY_HOOK` in GitHub secrets (get from Render dashboard).

---

## Monitoring & Logging

### Application Performance

Use browser DevTools to check:
- Network: Socket.IO latency
- Performance: Page load time
- Memory: Client-side memory usage

### Server Logging

Example logging in `socketio_events.py`:

```python
import logging
logger = logging.getLogger(__name__)

@socketio.on('join_room_request')
def handle_join_room(data):
    logger.info(f"Player joined room: {data['room_id']}")
```

View logs in deployment platform dashboard.

---

## Support & Help

- **Render Issues**: docs.render.com
- **Railway Issues**: railway.app/docs
- **Heroku Issues**: devcenter.heroku.com
- **Flask Help**: flask.palletsprojects.com
- **Socket.IO Help**: socket.io/docs/

Good luck with deployment! 🚀
