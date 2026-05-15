# main.py - DEBUG VERSION
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Aurora Sparq")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return RedirectResponse(url="/chat")

@app.get("/chat")
async def chat_page():
    path = "static/chat.html"
    logger.info(f"Serving chat page. File exists? {os.path.exists(path)}")
    
    if not os.path.exists(path):
        files = os.listdir("static") if os.path.exists("static") else ["No static folder!"]
        return HTMLResponse(f"""
            <h1>❌ chat.html NOT FOUND</h1>
            <p>Expected path: <code>{path}</code></p>
            <p>Files found in /static:</p>
            <ul>{''.join(f'<li>{f}</li>' for f in files)}</ul>
            <hr>
            <a href="/debug">Go to /debug</a>
        """, status_code=404)

    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/debug")
async def debug():
    return {
        "static_folder_exists": os.path.exists("static"),
        "files_in_static": os.listdir("static") if os.path.exists("static") else [],
        "chat_html_exists": os.path.exists("static/chat.html")
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
