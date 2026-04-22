# memory.py - Long-term Memory & Relationship System for Isabella
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_PATH = os.path.abspath(os.getenv("DB_PATH", "users.db"))

def init_db():
    """Initialize all memory-related tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Raw chat history (your original table)
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            convo_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_convo_id ON chat_history (convo_id)')

    # Key long-term facts / memories (immaculate recall)
    c.execute('''
        CREATE TABLE IF NOT EXISTS key_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            convo_id TEXT NOT NULL,
            fact TEXT NOT NULL,
            importance INTEGER DEFAULT 5,   -- 1-10 scale
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_recalled DATETIME
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_facts_convo ON key_facts (convo_id)')

    # Relationship progression
    c.execute('''
        CREATE TABLE IF NOT EXISTS relationship_state (
            convo_id TEXT PRIMARY KEY,
            level INTEGER DEFAULT 1,           -- 1 = new, 10 = very close
            last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
            pet_name TEXT,
            shared_moments TEXT,               -- JSON list of highlights
            notes TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Memory system initialized. DB: {DB_PATH}")

# ── Basic History Functions (your original) ───────────────────────────────
def get_history(convo_id: str, limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT role, content, timestamp
        FROM chat_history
        WHERE convo_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
    ''', (convo_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]

def save_message(convo_id: str, message: Dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_history (convo_id, role, content)
        VALUES (?, ?, ?)
    ''', (convo_id, message["role"], message["content"]))
    conn.commit()
    conn.close()

# ── Key Facts (for immaculate recall) ─────────────────────────────────────
def add_key_fact(convo_id: str, fact: str, importance: int = 7):
    """Add or update an important memory."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO key_facts (convo_id, fact, importance, last_recalled)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (convo_id, fact, importance))
    conn.commit()
    conn.close()

def get_relevant_facts(convo_id: str, limit: int = 8) -> List[str]:
    """Retrieve the most important recent facts for this user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT fact 
        FROM key_facts 
        WHERE convo_id = ?
        ORDER BY importance DESC, last_recalled DESC 
        LIMIT ?
    ''', (convo_id, limit))
    facts = [row[0] for row in c.fetchall()]
    conn.close()
    return facts

# ── Relationship Progression ───────────────────────────────────────────────
def get_relationship_level(convo_id: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT level FROM relationship_state WHERE convo_id = ?', (convo_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 1

def update_relationship(convo_id: str, new_level: Optional[int] = None, pet_name: Optional[str] = None, note: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO relationship_state (convo_id, level, pet_name, notes, last_interaction)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(convo_id) DO UPDATE SET
            last_interaction = CURRENT_TIMESTAMP,
            level = COALESCE(?, level),
            pet_name = COALESCE(?, pet_name),
            notes = COALESCE(notes || '\n' || ?, notes)
    ''', (convo_id, new_level or 1, pet_name, note, new_level, pet_name, note))
    conn.commit()
    conn.close()

# ── Memory Summarizer (call this occasionally) ─────────────────────────────
def summarize_recent_chat(convo_id: str):
    """Simple summarizer — can be expanded later with Grok if needed."""
    history = get_history(convo_id, limit=30)
    if len(history) < 8:
        return

    # Very basic extraction (you can make this smarter later)
    facts = []
    for msg in history[-15:]:
        content = msg["content"].lower()
        if any(word in content for word in ["like", "love", "hate", "favorite", "always", "never"]):
            facts.append(msg["content"][:120])

    for fact in facts[:5]:
        add_key_fact(convo_id, fact, importance=6)

# Initialize DB on import
init_db()
