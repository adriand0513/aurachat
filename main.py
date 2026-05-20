# main.py - Clean & Stable Isabella Chatbot
import os
import logging
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Isabella Chatbot")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Debug on startup
logger.info(f"Server started at {datetime.now()}")
logger.info(f"Current dir: {os.getcwd()}")
if os.path.exists("static"):
    logger.info(f"Static contents: {os.listdir('static')}")

# ====================== ROUTES ======================

@app.get("/")
async def home():
    try:
        with open("static/chat.html", "r", encoding="utf-8") as f:
            content = f.read()
        response = HTMLResponse(content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response
    except FileNotFoundError:
        return HTMLResponse("<h1 style='color:white;text-align:center;margin-top:100px;'>chat.html not found in static folder</h1>", 404)
    except Exception as e:
        logger.error(f"Homepage error: {e}")
        return HTMLResponse("<h1>Server Error</h1>", 500)


@app.post("/api/reply")
async def generate_reply(body: dict = Body(...)):
    convo_id = body.get("convo_id")
    user_message = body.get("message", "").strip()

    logger.info(f"Received message from {convo_id}: {user_message[:100]}")

    if not convo_id:
        raise HTTPException(400, "convo_id required")

    try:
        # Simple reliable reply for now (we can add Grok back later)
        reply = f"I hear you... {user_message}. Tell me more about that."

        return {
            "replies": [reply],
            "voice_note": ""
        }

    except Exception as e:
        logger.error(f"Error in generate_reply: {e}")
        return {"replies": ["Sorry, I'm having trouble responding right now..."], "voice_note": ""}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
