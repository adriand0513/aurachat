# memory.py - Long-term Memory & Relationship System for Isabella
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_PATH = os.path.abspath(os.getenv("DB_PATH", "users.db"))

def init_db():
    """Initialize all memory-related tables with safe migration."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Raw chat history
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

    # Key long-term facts
    c.execute('''
        CREATE TABLE IF NOT EXISTS key_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            convo_id TEXT NOT NULL,
            fact TEXT NOT NULL,
            importance INTEGER DEFAULT 5,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_recalled DATETIME
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_facts_convo ON key_facts (convo_id)')

    # Relationship progression
    c.execute('''
        CREATE TABLE IF NOT EXISTS relationship_state (
            convo_id TEXT PRIMARY KEY,
            level INTEGER DEFAULT 1,
            pet_name TEXT,
            notes TEXT,
            last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Memory system initialized successfully. DB: {DB_PATH}")

# ── Basic History Functions ───────────────────────────────────────────────
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

# ── Key Facts ─────────────────────────────────────────────────────────────
def add_key_fact(convo_id: str, fact: str, importance: int = 7):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO key_facts (convo_id, fact, importance, last_recalled)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (convo_id, fact, importance))
    conn.commit()
    conn.close()

def get_relevant_facts(convo_id: str, limit: int = 8) -> List[str]:
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

# ── Relationship Progression ──────────────────────────────────────────────
def get_relationship_level(convo_id: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT level FROM relationship_state WHERE convo_id = ?', (convo_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 1

def get_pet_name(convo_id: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT pet_name FROM relationship_state WHERE convo_id = ?', (convo_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else "babe"

def update_relationship(convo_id: str, delta: int = 1, pet_name: Optional[str] = None, note: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    current = get_relationship_level(convo_id)
    new_level = max(1, min(10, current + delta))
    
    c.execute('''
        INSERT INTO relationship_state (convo_id, level, pet_name, notes, last_interaction)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(convo_id) DO UPDATE SET
            last_interaction = CURRENT_TIMESTAMP,
            level = ?,
            pet_name = COALESCE(?, pet_name),
            notes = COALESCE(notes || '\n' || ?, notes)
    ''', (convo_id, new_level, pet_name, note))
    
    conn.commit()
    conn.close()

# Initialize everything
init_db()
