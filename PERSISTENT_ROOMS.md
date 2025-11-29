# Persistent Room Storage

## Overview

PlaySync now uses **file-based persistent storage** to keep rooms alive across app restarts. This is essential for Render's free tier, which spins down and restarts the app periodically.

## How It Works

1. **Room Creation**: When you create a room, it's saved to `rooms_data.json`
2. **QR Code Share**: The QR code links to the room ID
3. **Scan/Share**: When someone scans the QR or uses the link, the app checks persistent storage
4. **App Restart**: Even if Render restarts the app, the room is recovered from storage
5. **Expiration**: Rooms expire after 24 hours of no activity

## Technical Details

### Files

- `app/room_storage.py` - Handles all file I/O and persistence
- `app/room_manager.py` - Modified to use persistent storage
- `rooms_data.json` - Auto-created JSON file storing room data

### Storage Format

```json
{
  "ROOM123": {
    "room_id": "ROOM123",
    "created_at": "2025-11-29T15:30:00.123456",
    "max_players": 2,
    "players": {},
    "status": "active",
    "expires_at": "2025-11-30T15:30:00.123456"
  }
}
```

### Room Lifecycle

1. **Created** - Room added to storage when created
2. **Active** - Room is usable while within 24h window
3. **Expired** - Room auto-cleaned up after 24h inactivity
4. **Deleted** - Room removed when last player leaves

## Environment Variables

You can customize the storage file location:

```bash
export ROOM_STORAGE_FILE=/path/to/rooms_data.json
```

Default: `rooms_data.json` in app root

## Local Development

The persistent storage works exactly the same locally:

```bash
# Start the app
python run.py

# Create a room and note the ID
# Exit the app (Ctrl+C)

# Restart the app
python run.py

# Your room still exists! Use the same ID to join
```

## Render Deployment

The `rooms_data.json` file is **not** in `.gitignore` by default, so it will be stored:

- **On first deploy**: Empty (no rooms yet)
- **After users create rooms**: File persists across restarts
- **After 24 hours**: Old rooms auto-expire

⚠️ **Note**: If Render clears the filesystem (complete redeploy), rooms will be lost. This is expected behavior for free-tier deployments.

## Production Scaling

For production with >100 concurrent rooms, replace file storage with:

1. **PostgreSQL/MySQL** - Full room persistence
2. **Redis** - Fast room lookup and caching
3. **AWS S3** - Backup room data

See `DEPLOYMENT.md` → "Scaling for Production" for details.

## Testing

```python
from app import room_storage
from app.room_manager import room_manager

# Create a room
room_id = room_manager.create_room()

# List all rooms
all_rooms = room_storage.get_all_rooms()

# Get specific room
room_data = room_storage.get_room(room_id)

# Manual cleanup
room_storage.clear_expired_rooms()
```

## Troubleshooting

### "Room Not Found" on second browser

**Problem**: Room created in browser 1, but browser 2 can't find it

**Solution**: 
- Check that `rooms_data.json` exists in the app root
- Make sure the room ID is exactly correct (8 uppercase characters)
- Wait a few seconds for the file to be written

### "Room disappeared" after restart

**Problem**: Room was there yesterday but gone today

**Solution**: Rooms expire after 24 hours. Create a new one!

### Storage file grows too large

**Problem**: `rooms_data.json` keeps growing

**Solution**: 
- Expired rooms are auto-cleaned (see `clear_expired_rooms()`)
- Or manually delete `rooms_data.json` to start fresh
- For production, use a proper database

## FAQ

**Q: Can I backup my rooms?**  
A: Yes! Just backup `rooms_data.json`

**Q: Will rooms persist if Render redeploys?**  
A: Only if the filesystem isn't cleared. For guaranteed persistence, use a database.

**Q: Does this work offline?**  
A: Only if you run the app yourself. Render requires internet.

**Q: Can I use this with multiple server instances?**  
A: Not recommended. Use Redis/Database for multi-instance setups.
