# relationship.py - Relationship Progression System for Isabella
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.abspath(os.getenv("DB_PATH", "users.db"))

def init_relationship_table():
    """Create relationship table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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

def get_relationship_level(convo_id: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT level FROM relationship_state WHERE convo_id = ?", (convo_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 1

def get_pet_name(convo_id: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pet_name FROM relationship_state WHERE convo_id = ?", (convo_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""

def update_relationship(convo_id: str, delta: int = 1, pet_name: Optional[str] = None, note: Optional[str] = None):
    """Update relationship level gradually."""
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

# Initialize on import
init_relationship_table()
