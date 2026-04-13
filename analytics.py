# analytics.py - Analytics routes and logic
import sqlite3
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse

router = APIRouter()

DB_PATH = "analytics.db"
ANALYTICS_PASSWORD = "your_secure_password_here"   # ← CHANGE THIS BEFORE DEPLOYING

def get_analytics_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Summary
        c.execute("SELECT COUNT(*) as total_convos FROM conversations")
        total_convos = c.fetchone()["total_convos"]

        c.execute("SELECT COUNT(*) as total_messages FROM messages")
        total_messages = c.fetchone()["total_messages"]

        c.execute("SELECT COUNT(DISTINCT convo_id) as active_today FROM messages WHERE date(timestamp) = date('now')")
        active_today = c.fetchone()["active_today"]

        # Hourly activity
        c.execute("SELECT strftime('%H', timestamp) as hour, COUNT(*) as count FROM messages GROUP BY hour")
        hourly_data = {row["hour"]: row["count"] for row in c.fetchall()}

        # Daily activity (last 14 days)
        c.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM messages WHERE timestamp >= date('now', '-14 days') GROUP BY day")
        daily_data = {row["day"]: row["count"] for row in c.fetchall()}

        # Top 5 emotions
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
        print(f"Analytics data error: {e}")
        return {"error": str(e)}

@router.get("/analytics")
async def analytics_page(request: Request):
    password = request.query_params.get("pw")
    if password != ANALYTICS_PASSWORD:
        return HTMLResponse("<h1>Access Denied</h1><p>Invalid password.</p>", status_code=403)

    data = get_analytics_data()
    if "error" in data:
        return JSONResponse({"error": data["error"]}, status_code=500)

    return JSONResponse(data)
