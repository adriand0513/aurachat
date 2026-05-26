# relationship.py - Slow Weekly Decay Relationship System
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)
DB_PATH = os.path.abspath(os.getenv("DB_PATH", "isabella.db"))


def init_relationship_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS relationship_state (
            convo_id TEXT PRIMARY KEY,
            level INTEGER DEFAULT 1,
            pet_name TEXT,
            notes TEXT,
            last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("✅ Relationship system initialized")


def get_relationship_level(convo_id: str) -> int:
    """Get level with automatic slow decay"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get current state
    c.execute("""
        SELECT level, last_interaction 
        FROM relationship_state 
        WHERE convo_id = ?
    """, (convo_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return 1

    level, last_interaction = row

    # Calculate decay (very slow)
    if last_interaction:
        try:
            last_date = datetime.fromisoformat(last_interaction.replace("Z", "+00:00"))
            days_inactive = (datetime.now() - last_date).days

            # Decay 1 level every 7 days of inactivity (very gentle)
            decay = days_inactive // 7
            new_level = max(1, level - decay)
            
            if new_level < level:
                logger.info(f"⏳ Relationship decay for {convo_id}: {level} → {new_level} (inactive {days_inactive} days)")
                update_relationship(convo_id, delta= new_level - level)  # Apply decay
                
            return new_level
        except:
            pass

    return level


def update_relationship(convo_id: str, delta: int = 1, pet_name: Optional[str] = None, note: Optional[str] = None):
    """Update relationship"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        current = get_relationship_level(convo_id)  # This will apply decay if needed
        new_level = max(1, min(10, current + delta))

        c.execute('''
            INSERT INTO relationship_state 
            (convo_id, level, pet_name, notes, last_interaction)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(convo_id) DO UPDATE SET
                level = ?,
                pet_name = COALESCE(?, pet_name),
                notes = COALESCE(notes || '\n' || ?, notes),
                last_interaction = CURRENT_TIMESTAMP
        ''', (convo_id, new_level, pet_name, note, new_level, pet_name, note))
        
        conn.commit()
        logger.info(f"❤️ Relationship updated | convo={convo_id} | level={new_level}")
        
    except Exception as e:
        logger.error(f"Error updating relationship: {e}")
    finally:
        conn.close()


def reset_relationship(convo_id: str):
    """Reset to default"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO relationship_state (convo_id, level, pet_name, notes, last_interaction)
            VALUES (?, 1, NULL, NULL, CURRENT_TIMESTAMP)
            ON CONFLICT(convo_id) DO UPDATE SET
                level = 1, pet_name = NULL, notes = NULL, last_interaction = CURRENT_TIMESTAMP
        ''', (convo_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Reset error: {e}")
    finally:
        conn.close()


# Initialize
init_relationship_table()
