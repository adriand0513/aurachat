# analytics.py - Analytics routes and logic
import sqlite3
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

DB_PATH = "analytics.db"
ANALYTICS_PASSWORD = "your_secure_password_here"   # ← CHANGE THIS BEFORE DEPLOYING

def init_db():
    """Create tables if they don't exist + migration"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Conversations table
        c.execute('''CREATE TABLE IF NOT EXISTS conversations (
                        convo_id TEXT PRIMARY KEY,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        message_count INTEGER DEFAULT 0
                    )''')
        
        # Messages table
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        convo_id TEXT,
                        role TEXT,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        emotion TEXT DEFAULT 'neutral',
                        FOREIGN KEY(convo_id) REFERENCES conversations(convo_id)
                    )''')
        
        # Migration: Add emotion column if missing
        try:
            c.execute("ALTER TABLE messages ADD COLUMN emotion TEXT DEFAULT 'neutral'")
            logger.info("Added 'emotion' column to messages table")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
        logger.info("Analytics database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

# Run initialization when module loads
init_db()

def get_analytics_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT COUNT(*) as total_convos FROM conversations")
        total_convos = c.fetchone()["total_convos"] or 0

        c.execute("SELECT COUNT(*) as total_messages FROM messages")
        total_messages = c.fetchone()["total_messages"] or 0

        c.execute("SELECT COUNT(DISTINCT convo_id) as active_today FROM messages WHERE date(timestamp) = date('now')")
        active_today = c.fetchone()["active_today"] or 0

        # Hourly
        c.execute("SELECT strftime('%H', timestamp) as hour, COUNT(*) as count FROM messages GROUP BY hour")
        hourly_data = {row["hour"]: row["count"] for row in c.fetchall()}

        # Daily (last 14 days)
        c.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM messages WHERE timestamp >= date('now', '-14 days') GROUP BY day")
        daily_data = {row["day"]: row["count"] for row in c.fetchall()}

        # Top emotions
        c.execute("""
            SELECT emotion, COUNT(*) as count 
            FROM messages 
            WHERE role = 'assistant' 
            GROUP BY emotion 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_emotions = {row["emotion"]: row["count"] for row in c.fetchall()}

        conn.close()

        return {
            "summary": {
                "total_conversations": total_convos,
                "total_messages": total_messages,
                "active_today": active_today
            },
            "hourly_activity": hourly_data,
            "daily_activity": daily_data,
            "top_emotions": top_emotions
        }

    except Exception as e:
        logger.error(f"Analytics data error: {e}")
        return {"error": str(e)}

@router.get("/analytics")
async def analytics_page(request: Request):
    password = request.query_params.get("pw")
    if password != ANALYTICS_PASSWORD:
        return HTMLResponse("<h1>Access Denied</h1><p>Invalid password.</p>", status_code=403)

    try:
        with open("static/analytics.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Error: analytics.html not found</h1>", status_code=500)
    except Exception as e:
        logger.error(f"Analytics page error: {e}")
        return HTMLResponse("<h1>Error loading analytics page</h1>", status_code=500)
