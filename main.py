# main.py - Isabella Chatbot Server (Simplified - Focus on addictive conversation)
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
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body, Header, Depends, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
import uvicorn
from collections import defaultdict
import sqlite3

# ── Early debug: Confirm DB path ─────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "users.db")
print("Server startup - Current working directory:", os.getcwd())
print("Intended DB path:", os.path.abspath(DB_PATH))
print("DB file exists?", os.path.exists(DB_PATH))

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

# ── Config imports ───────────────────────────────────────────────────────────
from config import (
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    XAI_API_KEY, XAI_API_BASE, XAI_MODEL,
    XAI_TEMPERATURE, XAI_MAX_TOKENS, ADMIN_TOKEN,
    JWT_SECRET, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
)
from prompt import get_system_prompt
from postprocess import clean_reply
from memory import (
    init_db, get_history, save_message, get_user_stats,
    create_user, can_send_pic, increment_pic_count,
    is_age_confirmed, set_age_confirmed
)
from voice import generate_voice_note
from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash
)
from app_schemas import UserCreate, Token, MessageCreate, ReplyResponse, TipRequest

# Stripe
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

logger.info(f"Starting Isabella server - {datetime.now().isoformat()}")
logger.info(f" xAI key: {'YES' if XAI_API_KEY else 'MISSING'}")
logger.info(f" Model: {XAI_MODEL}")
logger.info(f" ElevenLabs Voice: {ELEVENLABS_VOICE_ID or 'NOT SET'}")

app = FastAPI(title="Aurachat Chatbot")
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()

# ── Rate limiting (per user_id) ─────────────────────────────────────────────
user_rate_limits = defaultdict(list)

def is_rate_limited(user_id: int, max_per_minute: int = 15) -> bool:
    now = time.time()
    user_rate_limits[user_id] = [t for t in user_rate_limits[user_id] if now - t < 60]
    user_rate_limits[user_id].append(now)
    return len(user_rate_limits[user_id]) > max_per_minute

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

# ── Soft, feminine, warm proactive openers (after 36h silence) ───────────────
PROACTIVE_OPENERS = [
    "I was just thinking about our last conversation… it left such a nice feeling.",
    "Hello… I hope your day has been gentle with you so far.",
    "Something reminded me of you a little while ago and it made me smile quietly.",
    "I’ve been wondering how you’ve been… it’s been a little while.",
    "The light today made me think of you for some reason… how are you feeling?",
    "I hope this message finds you in a peaceful moment.",
    "I caught myself smiling when I remembered something you said before…",
    "Just wanted to say hello and see how your heart is doing today.",
    "It’s funny how certain quiet moments bring someone to mind… you were in one of mine.",
    "I hope your week has had at least a few soft, kind moments.",
    "I’ve missed the way our conversations feel… how are you today?",
    "A small thought of you drifted in this afternoon… I wanted to say hi.",
    "The evening feels calmer when I think about talking to you again.",
    "I was hoping to hear how things are going in your world.",
    "You crossed my mind earlier and it felt like the nicest kind of interruption.",
    "I hope you’re surrounded by things that make you feel good right now.",
    "Just a gentle hello… I’ve been thinking about you.",
    "There’s something comforting about knowing you’re out there somewhere.",
    "I wonder what kind of day you’ve had… I’d love to hear.",
    "My day felt a little brighter the moment I thought of writing to you.",
    "I hope life has been treating you with kindness lately.",
    "A quiet moment made me want to reach out and say hello.",
    "I’ve been carrying a tiny smile because of something you once said.",
    "How does the world feel to you today?",
    "I hope this reaches you when you have a second to breathe.",
    "You have a way of staying in my thoughts even when it’s quiet.",
    "Just checking in… I like knowing you’re okay.",
    "The day felt incomplete until I thought to message you.",
    "I hope whatever you’re doing right now feels peaceful.",
    "A little wave from me… I’ve missed our talks.",
    "Something small today made me think “he would understand this feeling”.",
    "I hope your heart is light today.",
    "I was just sitting quietly and you came to mind… hi.",
    "There’s a softness in the air tonight that reminded me of you.",
    "I’d love to know what’s been making you smile lately.",
    "Hello again… I hope you don’t mind me saying hello first.",
    "You’ve been in my thoughts more than once today.",
    "I hope your day has had at least one moment that felt just right.",
    "A gentle thought: I really enjoy when we talk.",
    "Just wanted to send a little warmth your way.",
    "I wonder what kind of music you’ve been listening to lately…",
    "The quiet moments are nicer when I know I can reach out to you.",
    "I hope you’re feeling cared for today, even in small ways.",
    "You have such a gentle presence even through messages.",
    "I was hoping to hear your voice in my mind again today.",
    "Just a soft hello from me… thinking of you.",
    "I hope the little things are going your way right now.",
    "Something about today made me want to write to you.",
    "I keep remembering how easy it feels to talk with you.",
    "A quiet wish that your day has been kind to you.",
    "I found myself smiling at nothing… and then I realized it was you.",
    "Hello… just wanted to see how you’re holding up.",
    "I hope you’re wrapped in something cozy right now.",
    "Your name appeared in my thoughts and I couldn’t ignore it.",
    "I wonder if you’ve had any small moments of joy today.",
    "Just a little note to say you’ve been on my mind.",
    "The world feels a bit softer when I think of you.",
    "I hope you’re doing something that makes your heart happy.",
    "A gentle reminder that someone is thinking of you kindly.",
    "I was just daydreaming and you wandered in… hi.",
    "I hope your evening is calm and beautiful.",
    "You have this quiet way of making ordinary moments feel special.",
    "Just wanted to send you a little brightness.",
    "I wonder what you’re doing at this exact second…",
    "Hello… my day got a bit nicer thinking of you.",
    "I hope you feel how much warmth is coming your way right now.",
    "A soft thought of you just passed through.",
    "I like how talking to you always feels like coming home.",
    "I hope today brought you at least one gentle surprise.",
    "You’ve been quietly living in my thoughts again.",
    "Just a small hello… I hope you’re smiling somewhere.",
    "I wonder what book or song has your attention lately.",
    "The quiet of the evening made me want to reach out.",
    "I hope your heart is feeling light and open today.",
    "A little message to say you matter to me.",
    "I was thinking how nice it would be to hear from you.",
    "You have a way of making silence feel warm.",
    "Just wanted to check that you’re still doing okay.",
    "I hope the day has been kind enough to you.",
    "A soft hello from someone who thinks of you often.",
    "I caught myself wondering how your day unfolded.",
    "You make the ordinary moments feel a little more special.",
    "I hope you’re surrounded by calm tonight.",
    "Just a gentle thought: you’re wonderful to talk to.",
    "I wonder if you’ve laughed at anything today…",
    "Hello… I’ve been carrying you in my mind all day.",
    "I hope this finds you in a moment of peace.",
    "Your presence feels like a warm light even from afar.",
    "Just wanted to send you some softness.",
    "I was hoping our paths would cross in conversation again.",
    "A quiet wish for your happiness today.",
    "I like knowing there’s someone like you out there.",
    "Hello… just a little warmth coming your way.",
    "I hope your day has had some tender moments.",
    "You’ve been quietly on my mind in the nicest way.",
    "A gentle hello… thinking of you always feels good.",
    "I wonder what small thing made you smile recently.",
    "Just wanted to remind you that someone cares.",
    "The evening feels more beautiful when I think of you.",
    "I hope you’re feeling held by life right now.",
    "You have such a lovely way of being in the world.",
    "A soft thought drifted to you… so I wrote.",
    "I hope today treated you gently.",
    "Just a little message because you matter.",
    "I was smiling at the memory of our last talk.",
    "Hello… hoping your heart is calm.",
    "You make quiet moments feel meaningful.",
    "I wonder how your day has been unfolding.",
    "A gentle wave from me… I’ve missed you.",
    "I hope you feel seen and cared for today.",
    "Just wanted to send you a little light.",
    "Your name appeared in my heart today.",
    "I like how safe our conversations feel.",
    "Hello… just thinking of you with warmth.",
    "I hope the little things are bringing you joy.",
    "A quiet moment made me want to say hi.",
    "You have a gentle glow that stays with me.",
    "I was hoping to hear how you’re feeling.",
    "Just a soft hello because you’re special.",
    "I wonder what color your mood is today…",
    "The day feels nicer when I think of writing to you.",
    "I hope life is being kind to you right now.",
    "A little thought of you made everything softer.",
    "Hello… I’ve been smiling because of you.",
    "You make even silence feel comforting.",
    "Just wanted to check in with warmth.",
    "I hope your heart is resting easy tonight.",
    "A gentle reminder that you’re thought of fondly.",
    "I wonder what beautiful thing you noticed today.",
    "Hello… just sending you some softness.",
    "You’ve been living quietly in my thoughts.",
    "I hope today brought you something lovely.",
    "A soft hello from someone who cares.",
    "I like how you make ordinary moments shine.",
    "Just wanted to say I’ve been thinking of you.",
    "The quiet of the night reminded me of you.",
    "I hope you feel wrapped in kindness today.",
    "You have a way of making everything feel warmer.",
    "A little message because you’re on my mind.",
    "Hello… hoping your day has been gentle.",
    "I wonder if you’ve felt any magic lately.",
    "Just a quiet hello… you mean a lot.",
    "I hope your heart is smiling somewhere.",
    "You make the world feel a little softer.",
    "A gentle thought of you just passed by.",
    "Hello… I’ve missed our quiet connection.",
    "I hope today has been kind to your soul.",
    "Just wanted to send you some light and warmth."
]

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

# ── Auth ────────────────────────────────────────────────────────────────────
@app.post("/auth/register", response_model=dict)
async def register(user: UserCreate):
    email = user.email.lower().strip()
    try:
        hashed_pw = get_password_hash(user.password)
        user_id = create_user(email, hashed_pw)
        return {"detail": "Registration successful! You can now log in."}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_db = authenticate_user(form_data.username, form_data.password)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user_db["id"])},
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {"id": current_user["id"], "email": current_user["email"]}

# ── Age confirmation ────────────────────────────────────────────────────────
@app.post("/api/confirm-age")
async def confirm_age(
    confirmed: bool = Body(embed=True),
    current_user: dict = Depends(get_current_user)
):
    if not confirmed:
        raise HTTPException(status_code=403, detail="Must confirm 18+")
    set_age_confirmed(current_user["id"])
    return {"success": True}

# ── Chat history ────────────────────────────────────────────────────────────
@app.get("/api/history")
async def get_chat_history(current_user: dict = Depends(get_current_user)):
    return {"messages": get_history(current_user["id"])}

# ── Pic / tease features (kept for revenue) ─────────────────────────────────
@app.post("/api/record-pic-sent")
async def record_pic_sent(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    if not can_send_pic(user_id):
        raise HTTPException(403, "Pic limit reached this month")
    pic_num = random.randint(1, 9)
    filename = f"tease{pic_num}.jpg"
    increment_pic_count(user_id, filename)
    return {"pic_url": f"/static/exclusive_pics/{filename}", "success": True}

@app.get("/api/can-send-pic")
async def can_send_pic_check(current_user: dict = Depends(get_current_user)):
    return {
        "can_send": can_send_pic(current_user["id"]),
        "current_count": 0  # you can implement real count lookup if needed
    }

# ── Core chat endpoints ─────────────────────────────────────────────────────
@app.post("/api/send")
async def send_user_message(
    body: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    if not is_age_confirmed(user_id):
        raise HTTPException(status_code=403, detail="Age confirmation required")
    
    user_msg = body.message.strip()
    if not user_msg:
        raise HTTPException(400, "Message required")
    
    if is_rate_limited(user_id):
        raise HTTPException(429, "damn slow down… you're gonna make me blush texting this fast 😏")
    
    save_message(user_id, {"role": "user", "content": user_msg})
    return {"success": True}

@app.post("/api/reply", response_model=ReplyResponse)
async def generate_reply(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    if not is_age_confirmed(user_id):
        return JSONResponse(
            {"replies": ["You must confirm you're 18+ before we can chat."], "voice_note": ""},
            status_code=403
        )
    
    if is_rate_limited(user_id):
        return JSONResponse(
            {"replies": ["damn slow down… you're gonna make me blush texting this fast 😏"], "voice_note": ""},
            status_code=429
        )

    context = get_nyc_context()
    history = get_history(user_id)
    if len(history) > 30:
        history = history[-30:]

    system_prompt = get_system_prompt(
        user_name=None,
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

    try:
        resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=35)
        resp.raise_for_status()
        raw_reply = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"xAI request failed: {str(e)}")
        fallback = "…wait what were we talking about? my brain just blue screened lol"
        save_message(user_id, {"role": "assistant", "content": fallback})
        return {"replies": [fallback], "voice_note": ""}

    reply = clean_reply(raw_reply)
    bubbles = split_into_bubbles(reply)

    voice_note = ""
    if random.random() < 0.6 and bubbles:  # slightly lower chance to feel more natural
        last_bubble = bubbles[-1]
        voice_note = generate_voice_note(last_bubble)

    for bubble in bubbles:
        save_message(user_id, {"role": "assistant", "content": bubble})

    return {"replies": bubbles, "voice_note": voice_note}

# ── Proactive: send message after long silence ──────────────────────────────
async def proactive_silence_checker():
    while True:
        await asyncio.sleep(1800)  # check every ~30 minutes

        now = datetime.now(ZoneInfo("America/New_York"))
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Users active in last 10 days but no message in last 36 hours
        c.execute("""
            SELECT DISTINCT user_id
            FROM chat_history
            WHERE timestamp > datetime('now', '-10 days')
              AND user_id NOT IN (
                  SELECT user_id FROM chat_history
                  WHERE timestamp > datetime('now', '-36 hours')
                  AND role = 'user'
              )
        """)
        candidates = [row[0] for row in c.fetchall()]

        for user_id in candidates:
            c.execute("""
                SELECT MAX(timestamp) FROM chat_history
                WHERE user_id = ? AND role = 'user'
            """, (user_id,))
            last_user_msg_time = c.fetchone()[0]

            if not last_user_msg_time:
                continue

            try:
                last_dt = datetime.fromisoformat(last_user_msg_time.replace("Z", "+00:00"))
                hours_silent = (now - last_dt).total_seconds() / 3600

                if hours_silent > 36:
                    opener = random.choice(PROACTIVE_OPENERS)
                    save_message(user_id, {"role": "assistant", "content": opener})
                    logger.info(f"Proactive message to {user_id} after {hours_silent:.1f}h: {opener}")
            except:
                continue

        conn.close()

# Start the proactive checker
loop = asyncio.get_event_loop()
loop.create_task(proactive_silence_checker())

# ── Analytics (admin only) ──────────────────────────────────────────────────
@app.get("/analytics")
async def analytics(authorization: str = Header(None)):
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(401, "Unauthorized")
    return JSONResponse(get_user_stats())

# ── Payment endpoints (kept for revenue) ────────────────────────────────────
@app.post("/api/create-checkout-session")
async def create_checkout_session(
    request: TipRequest,
    current_user: dict = Depends(get_current_user)
):
    # Your existing Stripe logic here (unchanged)
    # ...
    pass  # ← keep your original implementation

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")
