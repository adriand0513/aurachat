# memory.py - Anonymous Conversation Memory for Isabella Chatbot (Render-Ready)
import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict

# ── DB Path Standardization ─────────────────────────────────────────────────
DB_PATH = os.path.abspath(os.getenv("DB_PATH", "users.db"))
print(f"memory.py: Using DB at: {DB_PATH}")
print(f"memory.py: DB exists? {os.path.exists(DB_PATH)}")

def init_db():
    """Create anonymous conversation tables if they don't exist."""
    print("=== init_db() STARTED ===")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Main chat history table (per conversation_id)
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            convo_id TEXT NOT NULL,
            role TEXT NOT NULL,           -- 'user' or 'assistant'
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Index for fast lookup by convo_id
    c.execute('CREATE INDEX IF NOT EXISTS idx_convo_id ON chat_history (convo_id)')
    
    conn.commit()
    conn.close()
    print("=== init_db() FINISHED SUCCESSFULLY ===")
    print(f"Database location: {DB_PATH}")

def get_history(convo_id: str) -> List[Dict]:
    """Retrieve all messages for a given conversation ID, sorted by time."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT role, content, timestamp 
        FROM chat_history 
        WHERE convo_id = ? 
        ORDER BY timestamp ASC
    ''', (convo_id,))
    rows = c.fetchall()
    conn.close()
    
    return [
        {"role": row[0], "content": row[1], "timestamp": row[2]}
        for row in rows
    ]

def save_message(convo_id: str, message: Dict):
    """Save a single message (user or assistant) to the conversation."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO chat_history (convo_id, role, content)
            VALUES (?, ?, ?)
        ''', (convo_id, message["role"], message["content"]))
        conn.commit()
    except Exception as e:
        print(f"Error saving message: {e}")
    finally:
        conn.close()

# ── Optional: Cleanup old conversations (can be called periodically) ─────────
def cleanup_old_conversations(days_old: int = 30):
    """Delete conversations older than X days to keep DB small."""
    cutoff = datetime.now() - timedelta(days=days_old)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()
    print(f"Cleaned up conversations older than {days_old} days")

# Call this once at startup
init_db()