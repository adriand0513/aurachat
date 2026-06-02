# internal_state.py - Narrative Memory & Emotional Continuity System
import sqlite3
import json
from datetime import datetime, timedelta
from config import DB_PATH

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def init_internal_state():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Main relationship state
    c.execute('''
        CREATE TABLE IF NOT EXISTS internal_state (
            convo_id TEXT PRIMARY KEY,
            emotional_temperature INTEGER DEFAULT 5,   -- 1-10
            relationship_phase TEXT DEFAULT 'early_flirt',
            trust_level INTEGER DEFAULT 3,
            last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
            current_mood TEXT DEFAULT 'playful',
            notes TEXT
        )
    ''')
    
    # Narrative memory - Shared stories & important moments
    c.execute('''
        CREATE TABLE IF NOT EXISTS narrative_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            convo_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            moment_type TEXT,           -- 'user_shared', 'her_story', 'milestone', 'joke'
            description TEXT,
            emotional_tag TEXT,         -- 'laugh', 'vulnerable', 'flirty', 'close', etc.
            importance INTEGER DEFAULT 5
        )
    ''')
    
    conn.commit()
    conn.close()

def get_internal_state(convo_id: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM internal_state WHERE convo_id = ?", (convo_id,))
    row = c.fetchone()
    
    # Get recent narratives
    c.execute('''
        SELECT description, emotional_tag, timestamp 
        FROM narrative_memories 
        WHERE convo_id = ? 
        ORDER BY importance DESC, timestamp DESC LIMIT 8
    ''', (convo_id,))
    narratives = c.fetchall()
    
    conn.close()

    if row:
        return {
            "emotional_temperature": row[1],
            "relationship_phase": row[2],
            "trust_level": row[3],
            "last_interaction": row[4],
            "current_mood": row[5],
            "notes": row[6] or "",
            "recent_narratives": [{"desc": n[0], "tag": n[1], "time": n[2]} for n in narratives]
        }
    return None  # New user

def add_narrative_moment(convo_id: str, description: str, moment_type: str = "shared", 
                        emotional_tag: str = None, importance: int = 5):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO narrative_memories 
        (convo_id, moment_type, description, emotional_tag, importance)
        VALUES (?, ?, ?, ?, ?)
    ''', (convo_id, moment_type, description, emotional_tag, importance))
    conn.commit()
    conn.close()

def update_internal_state(convo_id: str, emotional_delta=0, new_phase=None, 
                         new_tone=None, new_mood=None, new_note=None):
    """Update emotional state after conversation"""
    current = get_internal_state(convo_id)
    
    new_temp = max(1, min(10, current["emotional_temperature"] + emotional_delta))
    phase = new_phase or current["relationship_phase"]
    tone = new_tone or current["last_emotional_tone"]
    mood = new_mood or current["mood"]

    # Add important memory if note provided
    memories = current["key_memories"]
    if new_note:
        memories.append({
            "timestamp": datetime.now().isoformat(),
            "note": new_note
        })
        # Keep only last 15 memories
        if len(memories) > 15:
            memories = memories[-15:]

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO internal_state 
        (convo_id, emotional_temperature, relationship_phase, last_emotional_tone, 
         trust_level, last_interaction, mood, key_memories, notes)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
        ON CONFLICT(convo_id) DO UPDATE SET
            emotional_temperature = ?,
            relationship_phase = ?,
            last_emotional_tone = ?,
            mood = ?,
            key_memories = ?,
            notes = COALESCE(notes || '\n' || ?, notes),
            last_interaction = CURRENT_TIMESTAMP
    ''', (convo_id, new_temp, phase, tone, current["trust_level"], 
          mood, json.dumps(memories), new_note or "",
          new_temp, phase, tone, mood, json.dumps(memories), new_note or ""))
    
    conn.commit()
    conn.close()
