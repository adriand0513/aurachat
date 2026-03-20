# main.py - Isabella Chatbot Server (Simplified - No Verification)
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

# ── Early debug: Confirm DB path and contents ───────────────────────────────
DB_PATH = os.getenv("DB_PATH", "users.db")
print("Server startup - Current working directory:", os.getcwd())
print("Intended DB path:", os.path.abspath(DB_PATH))
print("DB file exists?", os.path.exists(DB_PATH))
print("DB file size:", os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else "missing bytes")

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print("Tables the server sees:", tables)
    conn.close()
except Exception as e:
    print("WARNING: Server cannot open DB at startup:", str(e))

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
logger.info(f" cwd: {os.getcwd()}")
logger.info(f" .env exists: {os.path.exists('.env')}")
logger.info(f" xAI key: {'YES' if XAI_API_KEY else 'MISSING'}")
logger.info(f" Model: {XAI_MODEL}")
logger.info(f" ElevenLabs Voice: {ELEVENLABS_VOICE_ID or 'NOT SET'}")
logger.info("---")

app = FastAPI(title="Aurachat Chatbot")
app.mount("/static", StaticFiles(directory="static"), name="static")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
	CORSMiddleware,
    allow_origins=[ 
    	"https://aurachat-5765.onrender.com",
        "https://aurachat.onrender.com",
        "https://aurachat.it.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.info(f"Registration attempt for email: {email}")

    try:
        hashed_pw = get_password_hash(user.password)
        user_id = create_user(email, hashed_pw)  # No phone required
        logger.info(f"User created with ID: {user_id}")
        return {"detail": "Registration successful! You can now log in."}
    except sqlite3.IntegrityError:
        logger.info(f"Duplicate email registration attempt: {email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    except ValueError as e:
        logger.error(f"Registration value error for {email}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during registration for {email}")
        raise HTTPException(status_code=500, detail="Internal server error during registration")


@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_db = authenticate_user(form_data.username, form_data.password)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_db["id"])},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"]
    }

# ── Age confirmation endpoint ──
@app.post("/api/confirm-age")
async def confirm_age(
    confirmed: bool = Body(embed=True),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    
    if not confirmed:
        raise HTTPException(status_code=403, detail="You must confirm you are 18+ to use this service.")
    
    set_age_confirmed(user_id)
    return {"success": True, "message": "Age confirmed. You can now chat."}

# ── Get full chat history ───────────────────────────────────────────────────
@app.get("/api/history")
async def get_chat_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    history = get_history(user_id)
    return {"messages": history}

# ── Record pic sent after payment & return URL ──────────────────────────────
@app.post("/api/record-pic-sent")
async def record_pic_sent(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    if not can_send_pic(user_id):
        raise HTTPException(403, "Pic limit reached - refunding payment (TEST MODE)")

    pic_num = random.randint(1, 9)
    filename = f"tease{pic_num}.jpg"

    try:
        increment_pic_count(user_id, filename)
        logger.info(f"Pic successfully delivered to user {user_id}: {filename}")
        return {"pic_url": f"/static/exclusive_pics/{filename}", "success": True}
    except Exception as e:
        logger.error(f"Pic delivery failed for user {user_id}: {str(e)}")
        raise HTTPException(500, f"Failed to deliver pic: {str(e)}")

# ── Refund if pic delivery failed ───────────────────────────────────────────
@app.post("/api/refund-failed-delivery")
async def refund_failed_delivery(
    session_id: str = Body(embed=True),
    current_user: dict = Depends(get_current_user)
):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        if not session.payment_intent:
            logger.warning(f"No payment intent in session {session_id}")
            return {"success": False, "reason": "No chargeable payment"}

        intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        
        if intent.status == 'succeeded':
            refund = stripe.Refund.create(payment_intent=intent.id)
            logger.info(f"Full refund issued for failed delivery - session {session_id}, refund ID: {refund.id}")
            return {"success": True, "refunded": True, "refund_id": refund.id}
        
        elif intent.status in ['requires_capture', 'requires_confirmation']:
            stripe.PaymentIntent.cancel(intent.id, cancellation_reason="failed_delivery")
            logger.info(f"Cancelled uncaptured intent for session {session_id}")
            return {"success": True, "refunded": False, "cancelled": True}
        
        else:
            logger.warning(f"Intent {intent.id} in non-refundable state: {intent.status}")
            return {"success": False, "reason": f"Payment in state {intent.status}"}

    except stripe.error.StripeError as e:
        logger.error(f"Stripe refund/cancel error for session {session_id}: {str(e)}")
        raise HTTPException(500, f"Refund error: {str(e)}")
    except Exception as e:
        logger.error(f"Refund endpoint error for session {session_id}: {str(e)}")
        raise HTTPException(500, "Refund processing failed")

# ── Get current pic limit status ────────────────────────────────────────────
@app.get("/api/can-send-pic")
async def can_send_pic_check(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    can = can_send_pic(user_id)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT pic_count_this_month FROM user_pics WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        count = row[0] if row else 0
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_pics (
                    user_id INTEGER PRIMARY KEY,
                    pic_count_this_month INTEGER DEFAULT 0,
                    month_year TEXT DEFAULT (strftime('%Y-%m', 'now')),
                    seen_pics TEXT DEFAULT '',
                    last_pic_timestamp DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            count = 0
        else:
            raise
    finally:
        conn.close()

    return {
        "can_send": can,
        "current_count": count
    }

# ── Protected Chat Endpoints ────────────────────────────────────────────────
@app.post("/api/send")
async def send_user_message(
    body: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    
    if not is_age_confirmed(user_id):
        raise HTTPException(status_code=403, detail="You must confirm you are 18+ before sending messages.")
    
    user_msg = body.message.strip()
    if not user_msg:
        raise HTTPException(400, "Message required")

    if is_rate_limited(user_id):
        raise HTTPException(429, "Slow down a bit babe... let's not rush this 😏")

    save_message(user_id, {"role": "user", "content": user_msg})
    return {"success": True}


@app.post("/api/reply", response_model=ReplyResponse)
async def generate_reply(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    if not is_age_confirmed(user_id):
        return JSONResponse(
            {"replies": ["You must confirm you are 18+ before we can chat."], "voice_note": ""},
            status_code=403
        )

    if is_rate_limited(user_id):
        return JSONResponse(
            {"replies": ["Slow down a bit babe... let's not rush this 😏"], "voice_note": ""},
            status_code=429
        )

    log_prefix = f"User {user_id}"
    context = get_nyc_context()
    logger.info(f"{log_prefix} Generating reply | NYC: {context['time']} | Weather: {context['weather']}")

    history = get_history(user_id)
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

    try:
        resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=35)
        resp.raise_for_status()
        raw_reply = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"{log_prefix} xAI failed: {str(e)}")
        fallback = "Sorry, got a little lost in my head for a sec... what were we saying? 😅"
        save_message(user_id, {"role": "assistant", "content": fallback})
        return {"replies": [fallback], "voice_note": ""}

    reply = clean_reply(raw_reply)
    bubbles = split_into_bubbles(reply)

    voice_note = ""
    emotional_keywords = [
        "miss", "love", "kiss", "horny", "sexy", "touch", "body", "want",
        "feel", "good", "night", "dream", "thinking", "smile", "heart", "crave"
    ]
    has_emotion = any(kw in reply.lower() for kw in emotional_keywords)

    if has_emotion and random.random() < 0.75 and bubbles:
        last_bubble = bubbles[-1]
        voice_note = generate_voice_note(last_bubble)
        logger.info(f"{log_prefix} Voice note generated for last bubble")
        # Optional: bubbles[-1] = ""  # if you want audio-only last bubble

    for bubble in bubbles:
        save_message(user_id, {"role": "assistant", "content": bubble})

    return {"replies": bubbles, "voice_note": voice_note}


# Global or DB-backed dict for last teaser per user
last_teaser_times = {}

TEASER_MESSAGES = [
    "Just thinking about last night... you still on my mind 😈",
    "Caught myself smiling thinking of you in the middle of my day 👀",
    "Busy running around but had to say hi... what are you up to? 💋",
    "Mmm wish I was with you right now instead of doing this boring thing...",
    "Saw something that reminded me of you... can't wait for tonight 🔥",
    "You popped into my head again... bad boy 😏",
    "Missing that voice of yours... talk later? 💕",
    "Day's dragging without our little chats... hurry up evening 😘",
    "Thinking naughty thoughts about you... behave until tonight 😉",
    "Just got out of the shower and thought of you...",
]

async def send_daily_teaser():
    while True:
        now = datetime.now(ZoneInfo("America/New_York"))
        is_gap_time = (now.hour >= 9 and now.hour < 18)

        if is_gap_time:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                SELECT DISTINCT user_id FROM chat_history 
                WHERE timestamp > datetime('now', '-2 days')
            """)
            active_users = [row[0] for row in c.fetchall()]
            conn.close()

            for user_id in active_users:
                last_sent = last_teaser_times.get(user_id)
                if last_sent is None or (now - last_sent) > timedelta(hours=18):
                    teaser = random.choice(TEASER_MESSAGES)
                    save_message(user_id, {"role": "assistant", "content": teaser})
                    last_teaser_times[user_id] = now
                    logger.info(f"Sent teaser to user {user_id}: {teaser}")

        await asyncio.sleep(600)

# Start background teaser task
loop = asyncio.get_event_loop()
loop.create_task(send_daily_teaser())

# ── Analytics ───────────────────────────────────────────────────────────────
@app.get("/analytics")
async def analytics(authorization: str = Header(None)):
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(401, "Unauthorized")
    return JSONResponse(get_user_stats())

# ── Stripe Tip / Pic Payment ────────────────────────────────────────────────
@app.post("/api/create-checkout-session")
async def create_checkout_session(
    request: TipRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    tip_type = request.tip_type

    if not can_send_pic(user_id):
        raise HTTPException(403, "You've reached the maximum of 5 exclusive pics this month")

    price_map = {
        "pic_tease": "price_1T1f1cF49k4gEmVBLQ7Mu5xd",  # ← your real Price ID
    }

    if tip_type not in price_map:
        raise HTTPException(400, "Invalid tip type")

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_map[tip_type], "quantity": 1}],
            mode="payment",
            success_url=f"{os.getenv('PUBLIC_BASE_URL', 'https://aurachat.it.com')}/chat?payment=success",
            cancel_url=f"{os.getenv('PUBLIC_BASE_URL', 'https://aurachat.it.com')}/chat?payment=cancel",
            metadata={
                "user_id": user_id,
                "tip_type": tip_type
            }
        )
        logger.info(f"Stripe session created for user {user_id}: {checkout_session.id}")
        return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(500, f"Stripe error: {str(e)}")
    except Exception as e:
        logger.error(f"Payment setup failed: {e}")
        raise HTTPException(500, "Payment setup failed")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")