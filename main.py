# main.py - Aurora Sparq (Natural Name System)
import os
import re
import random
import time
import logging
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from typing import Dict, List
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Aurora Sparq")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import memory with name support
from memory import (
    get_history,
    save_message,
    get_relevant_facts,
    get_relationship_level,
    get_pet_name,
    update_relationship,
    summarize_recent_chat,
    save_user_name,
    get_user_name
)

# Config
from config import (
    XAI_API_KEY, XAI_API_BASE, XAI_MODEL,
    XAI_TEMPERATURE, XAI_MAX_TOKENS,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
)

from prompt import get_system_prompt
from postprocess import clean_reply
from voice import generate_voice_note

# ── Guards ───────────────────────────────────────────────────────────────
last_reply_time = defaultdict(float)
REPLY_COOLDOWN_SECONDS = 6

convo_rate_limits = defaultdict(list)

def is_rate_limited(user_id: str, max_per_minute: int = 15):
    now = time.time()
    convo_rate_limits[user_id] = [t for t in convo_rate_limits[user_id] if now - t < 60]
    convo_rate_limits[user_id].append(now)
    return len(convo_rate_limits[user_id]) > max_per_minute

# ── Routes ───────────────────────────────────────────────────────────────
@app.get("/")
async def home():
    return RedirectResponse(url="/chat?v=0524")

@app.get("/chat")
async def chat_page():
    try:
        with open("static/chat.html", "r", encoding="utf-8") as f:
            content = f.read()
        response = HTMLResponse(content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Surrogate-Control"] = "no-store"
        response.headers["Vary"] = "Accept-Encoding, User-Agent"
        return response
    except FileNotFoundError:
        return HTMLResponse("<h1>chat.html not found</h1>", 404)

# ── GENERATE REPLY (with Natural Name Support) ───────────────────────────
@app.post("/api/reply")
async def generate_reply(body: Dict = Body(...)):
    user_id = body.get("user_id", "default").strip().lower()
    if not user_id:
        raise HTTPException(400, "user_id required")

    # Cooldown + Rate limit
    now = time.time()
    if now - last_reply_time[user_id] < REPLY_COOLDOWN_SECONDS:
        return {"replies": [], "voice_note": ""}
    last_reply_time[user_id] = now

    if is_rate_limited(user_id):
        return {"replies": [], "voice_note": ""}

    log_prefix = f"User {user_id}"
    context = get_nyc_context()

    # Get history and saved name
    history = get_history(user_id)
    if len(history) > 40:
        history = history[-40:]

    user_name = get_user_name(user_id)

    # ── Name Detection from Last Message ─────────────────────────────
    if not user_name and history:
        last_msg = history[-1]["content"].lower()
        name_triggers = ["my name is", "i'm ", "call me ", "name's ", "i am "]
        for trigger in name_triggers:
            if trigger in last_msg:
                # Extract potential name
                potential_name = last_msg.split(trigger)[-1].split(".")[0].split(",")[0].strip().title()
                if 3 <= len(potential_name) <= 20 and potential_name.isalpha():
                    save_user_name(user_id, potential_name)
                    user_name = potential_name
                    logger.info(f"New name saved: {potential_name}")
                    break

    # ── Build System Prompt ──────────────────────────────────────────
    relevant_facts = get_relevant_facts(user_id, limit=5)
    rel_level = get_relationship_level(user_id)
    pet_name = get_pet_name(user_id)

    system_prompt = get_system_prompt(
        user_name=user_name,
        current_time=context["time"],
        weather=context["weather"]
    )

    if relevant_facts:
        system_prompt += f"\n\nKey things you remember: {' | '.join(relevant_facts[:4])}"

    system_prompt += f"\nCurrent closeness: Level {rel_level}/10."
    if pet_name:
        system_prompt += f" You sometimes call them '{pet_name}'."

    if not user_name:
        system_prompt += "\nYou don't know their name yet. Ask for it warmly and naturally soon."

    # History for LLM
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

    try:
        resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=90)
        resp.raise_for_status()
        raw_reply = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"{log_prefix} XAI FAILURE: {e}")
        return {"replies": ["Sorry, I'm having trouble thinking right now..."], "voice_note": ""}

    reply = clean_reply(raw_reply)
    bubbles = split_into_bubbles(reply)

    # Voice note logic (your existing code)
    voice_note = ""
    emotional_keywords = ["miss", "love", "kiss", "horny", "sexy", "touch", "body", "want", "feel", "good", "night", "dream", "thinking", "smile", "heart", "crave"]
    has_emotion = any(kw in reply.lower() for kw in emotional_keywords)

    if has_emotion and random.random() < 0.375 and bubbles:
        try:
            voice_note = generate_voice_note(bubbles[-1])
        except Exception as e:
            logger.error(f"ElevenLabs error: {e}")

    # Save messages
    for bubble in bubbles:
        save_message(user_id, {"role": "assistant", "content": bubble, "voice_note": voice_note})

    if has_emotion and random.random() < 0.35:
        update_relationship(user_id, delta=1)

    if len(history) % 12 == 0 and len(history) > 10:
        summarize_recent_chat(user_id)

    return {"replies": bubbles, "voice_note": voice_note}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
