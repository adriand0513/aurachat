# config.py
from dotenv import load_dotenv
import os

load_dotenv()  # moved up so it's always called first

# ── Database ────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "users.db")

# ── ElevenLabs ──────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# ── xAI ─────────────────────────────────────────────────────────────────────
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_API_BASE = os.getenv("XAI_API_BASE", "https://api.x.ai/v1/chat/completions")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-4.20")
XAI_TEMPERATURE = float(os.getenv("XAI_TEMPERATURE", "0.84"))
XAI_MAX_TOKENS = int(os.getenv("XAI_MAX_TOKENS", "1024"))

# ── Auth / JWT / Email ──────────────────────────────────────────────────────
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-this-in-production-please")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Email verification (Resend recommended)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://aurachat.it.com")

# ── Critical checks ─────────────────────────────────────────────────────────
missing = []
if not XAI_API_KEY:
    missing.append("XAI_API_KEY")
if not JWT_SECRET:
    missing.append("JWT_SECRET")
# Optional but strongly recommended for production
if not RESEND_API_KEY:
    print("WARNING: RESEND_API_KEY missing → email verification will not send emails")
if not PUBLIC_BASE_URL.startswith(("http://", "https://")):
    print("WARNING: PUBLIC_BASE_URL should start with http:// or https://")

if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}. "
                     "Login and chat will fail without these.")

print("Config loaded successfully.")
print(f"JWT_SECRET present: {bool(JWT_SECRET)}")
print(f"RESEND_API_KEY present: {bool(RESEND_API_KEY)}")
print(f"PUBLIC_BASE_URL: {PUBLIC_BASE_URL}")
