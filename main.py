# main.py - Isabella Chatbot Server (Open, Anonymous, Render-Ready)
import os
import re
import json
import random
import time
import logging
import csv
import sqlite3
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv
from typing import Dict, List
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
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

# Memory & Relationship
from memory import (
    get_history as get_memory_history,
    save_message as save_memory_message,
    get_relevant_facts,
    summarize_recent_chat
)
from relationship import (
    get_relationship_level,
    get_pet_name,
    update_relationship
)

logger.info(f"Starting Isabella server - {datetime.now().isoformat()}")
logger.info(f" Model: {XAI_MODEL}")
logger.info(f" Temperature: {XAI_TEMPERATURE}")
logger.info(f" Max tokens: {XAI_MAX_TOKENS}")
logger.info("---")

app = FastAPI(title="Isabella Chatbot")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(analytics_router)

# ── Private CSV Logging ─────────────────────────────────────────────────────
CSV_LOG_FILE = "isabella_private_logs.csv"

def init_csv_log():
    if not os.path.exists(CSV_LOG_FILE):
        with open(CSV_LOG_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "convo_id", "user_message", "isabella_reply", "emotion", "voice_note_generated"])
        logger.info("Created private CSV log file")

init_csv_log()

def log_to_csv(convo_id: str, user_message: str, isabella_reply: str, emotion: str, voice_note: bool):
    try:
        with open(CSV_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                convo_id,
                user_message[:500],
                isabella_reply[:1000],
                emotion,
                "Yes" if voice_note else "No"
            ])
    except Exception as e:
        logger.error(f"Failed to write to private CSV log: {e}")

# ── SQLite Analytics Database ───────────────────────────────────────────────
DB_PATH = "analytics.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
                    convo_id TEXT PRIMARY KEY,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    convo_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    emotion TEXT DEFAULT 'neutral'
                )''')
    try:
        c.execute("ALTER TABLE messages ADD COLUMN emotion TEXT DEFAULT 'neutral'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
    logger.info("Analytics database initialized successfully")

init_db()

# Emotion detection
EMOTION_MAP = {
    "flirty": ["sexy", "horny", "kiss", "touch", "want you", "miss you"],
    "playful": ["lol", "haha", "tease", "funny"],
    "warm": ["sweet", "cute", "smile", "happy"],
    "seductive": ["body", "curves", "crave", "feel"],
    "teasing": ["trouble", "naughty", "careful"],
    "neutral": []
}

def detect_emotion(text: str) -> str:
    if not text:
        return "neutral"
    text_lower = text.lower()
    for emotion, keywords in EMOTION_MAP.items():
        if any(kw in text_lower for kw in keywords):
            return emotion
    return "neutral"

# ── Memory & History Helpers ───────────────────────────────────────────────
def get_history(convo_id: str) -> List[Dict]:
    return get_memory_history(convo_id)

def save_message(convo_id: str, message: Dict):
    save_memory_message(convo_id, message)

# ── Rate limiting ───────────────────────────────────────────────────────────
convo_rate_limits = defaultdict(list)

def is_rate_limited(convo_id: str, max_per_minute: int = 20) -> bool:
    now = time.time()
    convo_rate_limits[convo_id] = [t for t in convo_rate_limits[convo_id] if now - t < 60]
    convo_rate_limits[convo_id].append(now)
    return len(convo_rate_limits[convo_id]) > max_per_minute

# ── NYC context ─────────────────────────────────────────────────────────────
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

# ── Split into bubbles ──────────────────────────────────────────────────────
def split_into_bubbles(text: str) -> List[str]:
    if not text.strip():
        return ["..."]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        paragraphs = []
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if current and random.random() < 0.45 and len(paragraphs) < 3:
                paragraphs.append(current.strip())
                current = sentence
            else:
                if current:
                    current += " " + sentence
                else:
                    current = sentence
        if current:
            paragraphs.append(current.strip())
    if len(paragraphs) == 1 and len(paragraphs[0]) > 160:
        sentences = re.split(r'(?<=[.!?])\s+', paragraphs[0])
        paragraphs = []
        current = ""
        for sentence in sentences:
            if len(current) > 95 and len(paragraphs) < 3:
                paragraphs.append(current.strip())
                current = sentence
            else:
                current += " " + sentence if current else sentence
        if current:
            paragraphs.append(current.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    return paragraphs if paragraphs else [text.strip()]

# ── Background Task with Delay ─────────────────────────────────────────────
async def delayed_reply_task(convo_id: str):
    try:
        logger.info(f"[Background] Starting delay for {convo_id}")
        await asyncio.sleep(6)
        thinking_time = random.uniform(8, 14)
        await asyncio.sleep(thinking_time)
        logger.info(f"[Background] Starting reply generation for {convo_id}")
        await generate_normal_reply(convo_id)
    except Exception as e:
        logger.error(f"[Background Task Error] {convo_id}: {e}", exc_info=True)

async def generate_normal_reply(convo_id: str):
    """Core reply generation with improved logging and error handling"""
    log_prefix = f"Reply {convo_id}"
    try:
        logger.info(f"{log_prefix} - Starting reply generation")

        context = get_nyc_context()
        history = get_history(convo_id)
        if len(history) > 40:
            history = history[-40:]

        relevant_facts = get_relevant_facts(convo_id, limit=5)
        rel_level = get_relationship_level(convo_id)
        pet_name = get_pet_name(convo_id)

        memory_summary = ""
        if relevant_facts:
            memory_summary = "Key things you remember about him: " + " | ".join(relevant_facts[:4])

        system_prompt = get_system_prompt(
            user_name=None,
            current_time=context["time"],
            weather=context["weather"]
        )

        if memory_summary:
            system_prompt += f"\n\n{memory_summary}"
        system_prompt += f"\nCurrent relationship closeness: Level {rel_level}/10."
        if pet_name:
            system_prompt += f" You sometimes call him '{pet_name}' naturally."
        else:
            system_prompt += " Avoid pet names unless he uses one first."

        recent_history = history[-22:]
        messages = [{"role": "system", "content": system_prompt}] + recent_history

        # Call Grok
        headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": XAI_MODEL,
            "messages": messages,
            "temperature": XAI_TEMPERATURE,
            "max_tokens": XAI_MAX_TOKENS,
        }

        logger.info(f"{log_prefix} - Calling xAI API")
        resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=75)
        resp.raise_for_status()
        raw_reply = resp.json()["choices"][0]["message"]["content"].strip()

        reply = clean_reply(raw_reply)
        bubbles = split_into_bubbles(reply)

        voice_note = ""
        emotional_keywords = ["miss", "love", "kiss", "horny", "sexy", "touch", "body", "want", "feel", "good", "night", "dream", "thinking", "smile", "heart", "crave"]
        has_emotion = any(kw in reply.lower() for kw in emotional_keywords)

        if has_emotion and random.random() < 0.75 and bubbles:
            try:
                voice_note = generate_voice_note(bubbles[-1])
            except Exception as e:
                logger.error(f"{log_prefix} ElevenLabs FAILED: {e}")

        # Save messages
        for bubble in bubbles:
            save_message(convo_id, {"role": "assistant", "content": bubble})

        # Occasional memory & relationship updates
        if len(history) % 12 == 0 and len(history) > 10:
            summarize_recent_chat(convo_id)

        if has_emotion and random.random() < 0.35:
            update_relationship(convo_id, delta=1)

        # CSV log
        last_user = ""
        if history:
            for msg in reversed(history):
                if msg["role"] == "user":
                    last_user = msg["content"]
                    break

        log_to_csv(
            convo_id=convo_id,
            user_message=last_user,
            isabella_reply=" | ".join(bubbles),
            emotion=detect_emotion(" ".join(bubbles)),
            voice_note=bool(voice_note)
        )

        logger.info(f"{log_prefix} - SUCCESS: Sent {len(bubbles)} bubbles")

    except Exception as e:
        logger.error(f"{log_prefix} - FAILED: {e}", exc_info=True)

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
            content = f.read()
        response = HTMLResponse(content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except FileNotFoundError:
        return HTMLResponse("<h1>Error: chat.html not found</h1>", status_code=500)

@app.post("/api/send")
async def send_message(body: Dict[str, str] = Body(...), background_tasks: BackgroundTasks = None):
    convo_id = body.get("convo_id")
    message = body.get("message", "").strip()
    if not convo_id or not message:
        raise HTTPException(400, "convo_id and message required")
    if is_rate_limited(convo_id):
        raise HTTPException(429, "Slow down... let's not rush this 😏")

    save_message(convo_id, {"role": "user", "content": message})

    # Start delayed reply in background
    if background_tasks:
        background_tasks.add_task(delayed_reply_task, convo_id)

    return {"success": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")
