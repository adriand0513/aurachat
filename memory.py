# memory.py - Bulletproof Simple Convo ID Version
import sqlite3
import os
from datetime import datetime
from typing import List, Dict

DB_PATH = os.path.abspath(os.getenv("DB_PATH", "users.db"))

def init_db():
    """Initialize with extremely safe migrations"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table with all columns
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            convo_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            voice_note TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Force add missing columns
    try:
        c.execute("ALTER TABLE chat_history ADD COLUMN convo_id TEXT")
        print("✅ Added convo_id column")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE chat_history ADD COLUMN voice_note TEXT")
        print("✅ Added voice_note column")
    except sqlite3.OperationalError:
        pass

    # Create index
    c.execute('CREATE INDEX IF NOT EXISTS idx_convo_id ON chat_history (convo_id)')

    conn.commit()
    conn.close()
    print(f"✅ Memory system ready → {DB_PATH}")


def get_history(convo_id: str, limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT role, content, voice_note, timestamp
        FROM chat_history
        WHERE convo_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
    ''', (convo_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "voice_note": r[2], "timestamp": r[3]} for r in rows]


def save_message(convo_id: str, message: Dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_history (convo_id, role, content, voice_note)
        VALUES (?, ?, ?, ?)
    ''', (convo_id, message["role"], message["content"], message.get("voice_note")))
    conn.commit()
    conn.close()


# Initialize
init_db()
