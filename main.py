# main.py - Isabella Chatbot Server (Open, Anonymous, Render-Ready)
import os
import re
import json
import asyncio
import random
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# ── Config imports ───────────────────────────────────────────────────────────
from config import (
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    XAI_API_KEY, XAI_API_BASE, XAI_MODEL,
    XAI_TEMPERATURE, XAI_MAX_TOKENS
)
from prompt import get_system_prompt
from postprocess import clean_reply
from voice import generate_voice_note
from analytics import router as analytics_router

logger.info(f"Starting Isabella server - {datetime.now().isoformat()}")
logger.info(f" cwd: {os.getcwd()}")
logger.info(f" .env exists: {os.path.exists('.env')}")
logger.info(f" xAI key: {'YES' if XAI_API_KEY else 'MISSING'}")
logger.info(f" Model: {XAI_MODEL}")
logger.info(f" ElevenLabs Voice: {ELEVENLABS_VOICE_ID or 'NOT SET'}")
logger.info("---")

app = FastAPI(title="Isabella Chatbot")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(analytics_router)

# ── Anonymous Memory (simple in-memory for MVP) ─────────────────────────────
conversations = {}  # convo_id -> list of messages

def get_history(convo_id: str) -> List[Dict]:
    return conversations.get(convo_id, [])

def save_message(convo_id: str, message: Dict):
    if convo_id not in conversations:
        conversations[convo_id] = []
    conversations[convo_id].append(message)

# ── Rate limiting (per conversation_id) ──────────────────────────────────────
convo_rate_limits = defaultdict(list)

def is_rate_limited(convo_id: str, max_per_minute: int = 15) -> bool:
    now = time.time()
    convo_rate_limits[convo_id] = [t for t in convo_rate_limits[convo_id] if now - t < 60]
    convo_rate_limits[convo_id].append(now)
    return len(convo_rate_limits[convo_id]) > max_per_minute

# ── NYC weather/time context ────────────────────────────────────────────────
def get_nyc_context() -> Dict[str, str]:
    nyc_tz = ZoneInfo("America/New_York")
    now_nyc = datetime.now(nyc_tz)
    time_str = now_nyc.strftime("%I:%M %p on %A, %B %d")
    try:
        r = requests.get("https://wttr.in/NYC?format=%c+%t+%w", timeout=5)
        if r.status_code == 200:
            parts = r.text.strip().split()
            weather = f"{parts[0]} {parts[1]}, wind {parts[2]}" if len(parts) >= 3 else r.text.strip()
        else:
            weather = "cool and clear"
    except:
        weather = "chilly evening"
    return {"time": time_str, "weather": weather}

def split_into_bubbles(text: str) -> List[str]:
    if not text.strip():
        return ["..."]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    bubbles = []
    for paragraph in paragraphs:
        if len(paragraph) <= 120:
            bubbles.append(paragraph)
            continue
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) <= 100:
                current += sentence + " "
            else:
                if current:
                    bubbles.append(current.strip())
                current = sentence + " "
        if current:
            bubbles.append(current.strip())
    bubbles = [b.strip() for b in bubbles if b.strip()]
    return bubbles if bubbles else [text.strip()]

# ── Routes ──────────────────────────────────────────────────────────────────
@app.get("/")
async def home():
    try:
        with open("static/home.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Error: home.html not found</h1>", status_code=500)

@app.get("/chat")
async def chat_page():
    try:
        with open("static/chat.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Error: chat.html not found</h1>", status_code=500)

# ── Open Chat Endpoints (Anonymous) ─────────────────────────────────────────
@app.post("/api/send")
async def send_message(body: Dict[str, str] = Body(...)):
    convo_id = body.get("convo_id")
    message = body.get("message", "").strip()
    if not convo_id or not message:
        raise HTTPException(400, "convo_id and message required")
    if is_rate_limited(convo_id):
        raise HTTPException(429, "Slow down... let's not rush this 😏")
    save_message(convo_id, {"role": "user", "content": message})
    return {"success": True}

@app.post("/api/reply")
async def generate_reply(body: Dict[str, str] = Body(...)):
    convo_id = body.get("convo_id")
    if not convo_id:
        raise HTTPException(400, "convo_id required")

    if is_rate_limited(convo_id):
        return JSONResponse({"replies": [], "voice_note": ""}, status_code=200)

    log_prefix = f"Convo {convo_id}"
    context = get_nyc_context()

    logger.info(f"{log_prefix} Generating reply | NYC: {context['time']} | Weather: {context['weather']}")

    history = get_history(convo_id)
    if len(history) > 30:
        history = history[-30:]

    user_name: Optional[str] = None
    system_prompt = get_system_prompt(
        user_name=user_name,
        current_time=context["time"],
        weather=context["weather"]
    )

    messages = [{"role": "system", "content": system_prompt}] + history[-20:]

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": XAI_MODEL,
        "messages": messages,
        "temperature": XAI_TEMPERATURE,
        "max_tokens": XAI_MAX_TOKENS,
    }

    # ── STRENGTHENED XAI FAIL-SAFE ───────────────────────────────────────────
    try:
        resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=35)
        resp.raise_for_status()
        raw_reply = resp.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        # CRITICAL: Log everything in detail, send NOTHING to the user
        logger.error(f"{log_prefix} XAI FAILURE: {str(e)}")
        logger.error(f"{log_prefix} Exception type: {type(e).__name__}")
        
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"{log_prefix} XAI status code: {e.response.status_code}")
            logger.error(f"{log_prefix} XAI response body: {e.response.text[:800]}")
        else:
            logger.error(f"{log_prefix} No response from XAI (timeout or connection error)")

        # Return empty payload → frontend shows nothing
        return JSONResponse({"replies": [], "voice_note": ""}, status_code=200)

    # ── Normal successful path ───────────────────────────────────────────────
    reply = clean_reply(raw_reply)
    bubbles = split_into_bubbles(reply)
    voice_note = ""

    # ── STRENGTHENED ELEVENLABS FAIL-SAFE ───────────────────────────────────
    emotional_keywords = ["miss", "love", "kiss", "horny", "sexy", "touch", "body", "want", "feel", "good", "night", "dream", "thinking", "smile", "heart", "crave"]
    has_emotion = any(kw in reply.lower() for kw in emotional_keywords)

    if has_emotion and random.random() < 0.75 and bubbles:
        try:
            last_bubble = bubbles[-1]
            voice_note = generate_voice_note(last_bubble)
            if voice_note:
                logger.info(f"{log_prefix} Voice note generated successfully")
            else:
                logger.warning(f"{log_prefix} Voice note generation returned empty")
        except Exception as e:
            # 100% silent fail - no leak to user, only log
            logger.error(f"{log_prefix} ElevenLabs FAILURE (likely out of tokens or API error): {str(e)}")
            voice_note = ""   # Ensure nothing is sent

    for bubble in bubbles:
        save_message(convo_id, {"role": "assistant", "content": bubble})

    return {"replies": bubbles, "voice_note": voice_note}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")
