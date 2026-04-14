# analytics.py - Simple Dashboard Route
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

ANALYTICS_PASSWORD = "your_secure_password_here"   # CHANGE THIS

@router.get("/analytics")
async def analytics_page(request: Request):
    password = request.query_params.get("pw")
    if password != ANALYTICS_PASSWORD:
        return HTMLResponse("<h1>Access Denied</h1><p>Invalid password.</p>", status_code=403)

    try:
        with open("static/analytics.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>analytics.html not found in static folder</h1>", status_code=500)
    except Exception as e:
        logger.error(f"Failed to serve analytics.html: {e}")
        return HTMLResponse("<h1>Error loading dashboard</h1>", status_code=500)
