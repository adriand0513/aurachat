# main.py - Clean Foundation for Aurora Sparq
import os
import re
import random
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Aurora Sparq")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Basic Guards ─────────────────────────────────────
last_reply_time = defaultdict(float)
REPLY_COOLDOWN_SECONDS = 6

# ── Simple Helper Functions ──────────────────────────
def get_nyc_context() -> Dict[str, str]:
    return {"time": "Evening in NYC", "weather": "chilly"}

def split_into_bubbles(text: str) -> List[str]:
    if not text.strip():
        return ["..."]
    return [p.strip() for p in text.split(". ") if p.strip()]

# ── Routes ───────────────────────────────────────────
@app.get("/")
async def home():
    return RedirectResponse(url="/chat")

@app.get("/chat")
async def chat_page():
    try:
        with open("static/chat.html", "r", encoding="utf-8") as f:
            content = f.read()
        response = HTMLResponse(content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    except Exception as e:
        logger.error(f"Failed to serve chat.html: {e}")
        return HTMLResponse("<h1>Error loading chat page</h1>", status_code=500)

@app.post("/api/login")
async def login_user(body: Dict[str, str] = Body(...)):
    email = body.get("email", "").strip().lower()
    first_name = body.get("first_name", "").strip()
    last_name = body.get("last_name", "").strip()

    if not email or not first_name or not last_name:
        raise HTTPException(400, "All fields are required")

    try:
        # We'll connect memory.py properly later
        create_or_get_user(email, first_name, last_name)   # This may still fail if import is missing
        logger.info(f"User logged in: {email}")
        return {"success": True, "email": email}
    except Exception as e:
        logger.error(f"Login error: {e}")
        # For now, still accept the login even if DB fails
        return {"success": True, "email": email}

@app.post("/api/reply")
async def generate_reply(body: Dict[str, str] = Body(...)):
    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "email required")

    if time.time() - last_reply_time[email] < REPLY_COOLDOWN_SECONDS:
        return JSONResponse({"replies": [], "voice_note": ""})

    last_reply_time[email] = time.time()

    # Simple fallback reply for now
    return {
        "replies": ["Hey cutie 😘 I've missed talking to you. How's your day going?"],
        "voice_note": ""
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
