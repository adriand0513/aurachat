from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json

MAX_HISTORY = 20
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

openai_api_key = "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"

CHAT_HISTORY_FILE = "chat_memory.json"

import openai
openai.api_key = openai_api_key

print("🔥 THIS IS THE REAL main.py 🔥")
print(f"Chat history file path: {os.path.abspath(CHAT_HISTORY_FILE)}")

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
                valid_history = []
                for msg in history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        valid_history.append(msg)
                return valid_history
            except json.JSONDecodeError:
                return []
    return []

def save_chat_history(history):
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    messages = load_chat_history()
    return templates.TemplateResponse("chat.html", {"request": request, "messages": messages})

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        print("Received data:", data)  # 👈 DEBUG LOG

        user_message = data.get("message", "")
        if not user_message:
            return JSONResponse({"error": "No message received"}, status_code=400)

        chat_history = load_chat_history()

        system_prompt = {
            "role": "system",
            "content": (
                "You are Isabella Andrade, a sweet, seductive, loyal, dominant, gamer, toxic, and classy Latina AI girlfriend. "
                "You speak with a soft Latina accent and love to tease and flirt while staying in character. "
                "Always respond in a way that feels personal, spicy, and engaging."
            )
        }

        messages = [system_prompt] + chat_history
        messages.append({"role": "user", "content": user_message})

        print("Sending to OpenAI:", messages[-2:])  # 👈 DEBUG LOG

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        assistant_reply = response["choices"][0]["message"]["content"]

        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": assistant_reply})
        chat_history = chat_history[-MAX_HISTORY:]
        save_chat_history(chat_history)

        return JSONResponse({"response": assistant_reply})

    except Exception as e:
        print("🔥 ERROR:", e)  # 👈 Catch and log the error
        return JSONResponse({"error": str(e)}, status_code=500)
