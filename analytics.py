# analytics.py - Clean Dashboard Route
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

DB_PATH = "analytics.db"
ANALYTICS_PASSWORD = "your_secure_password_here"   # ← CHANGE THIS

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

        c.execute("SELECT strftime('%H', timestamp) as hour, COUNT(*) as count FROM messages GROUP BY hour")
        hourly = {row["hour"]: row["count"] for row in c.fetchall()}

        c.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM messages WHERE timestamp >= date('now', '-14 days') GROUP BY day")
        daily = {row["day"]: row["count"] for row in c.fetchall()}

        c.execute("SELECT emotion, COUNT(*) as count FROM messages WHERE role = 'assistant' GROUP BY emotion ORDER BY count DESC LIMIT 5")
        emotions = {row["emotion"]: row["count"] for row in c.fetchall()}

        conn.close()

        return {
            "summary": {
                "total_conversations": total_convos,
                "total_messages": total_messages,
                "active_today": active_today
            },
            "hourly_activity": hourly,
            "daily_activity": daily,
            "top_emotions": emotions
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
    except Exception as e:
        logger.error(f"Failed to serve analytics.html: {e}")
        return HTMLResponse("<h1>Error loading dashboard</h1>", status_code=500)

# Optional: Separate JSON endpoint for debugging
@router.get("/analytics/data")
async def analytics_data(request: Request):
    password = request.query_params.get("pw")
    if password != ANALYTICS_PASSWORD:
        return JSONResponse({"detail": "Invalid password"}, status_code=403)
    return JSONResponse(get_analytics_data())
