# analytics.py - Enhanced with Archetype Tracking
import sqlite3
import json
import time
from datetime import datetime
from collections import defaultdict
from config import DB_PATH

def log_event(event_type: str, convo_id: str = None, user_id: int = None, 
              metadata: dict = None, duration_ms: int = None):
    """Log any analytics event"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO analytics_events 
        (event_type, convo_id, user_id, metadata, duration_ms)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        event_type,
        convo_id,
        user_id,
        json.dumps(metadata) if metadata else None,
        duration_ms
    ))
    conn.commit()
    conn.close()


def get_live_stats():
    """Get real-time stats including archetype distribution"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Active conversations (last 5 minutes)
    c.execute('''
        SELECT COUNT(DISTINCT convo_id) 
        FROM analytics_events 
        WHERE timestamp > datetime('now', '-5 minutes')
        AND event_type = 'message_sent'
    ''')
    active_convos = c.fetchone()[0] or 0

    # Messages per minute
    c.execute('''
        SELECT COUNT(*) 
        FROM analytics_events 
        WHERE timestamp > datetime('now', '-1 minute')
        AND event_type IN ('message_sent', 'message_received')
    ''')
    messages_per_min = c.fetchone()[0] or 0

    # Average response time
    c.execute('''
        SELECT AVG(duration_ms) 
        FROM analytics_events 
        WHERE event_type = 'response_generated' 
        AND duration_ms IS NOT NULL
        AND timestamp > datetime('now', '-30 minutes')
    ''')
    avg_response = round(c.fetchone()[0] or 0)

    # Recent Archetypes
    c.execute('''
        SELECT metadata 
        FROM analytics_events 
        WHERE event_type = 'archetype_detected'
        ORDER BY timestamp DESC 
        LIMIT 50
    ''')
    archetype_data = []
    archetype_count = defaultdict(int)
    
    for row in c.fetchall():
        if row[0]:
            try:
                meta = json.loads(row[0])
                arch = meta.get("archetype")
                if arch and arch != "unknown":
                    archetype_count[arch] += 1
                    archetype_data.append(meta)
            except:
                pass

    conn.close()

    return {
        "active_sessions": active_convos,
        "messages_per_minute": messages_per_min,
        "avg_response_time_ms": avg_response,
        "total_archetypes_detected": len(archetype_data),
        "top_archetypes": dict(sorted(archetype_count.items(), key=lambda x: x[1], reverse=True)[:8]),
        "timestamp": datetime.now().isoformat()
    }


def get_archetype_distribution():
    """Get overall archetype statistics"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT metadata 
        FROM analytics_events 
        WHERE event_type = 'archetype_detected'
    ''')
    counts = defaultdict(int)
    for row in c.fetchall():
        if row[0]:
            try:
                data = json.loads(row[0])
                arch = data.get("archetype")
                if arch:
                    counts[arch] += 1
            except:
                pass
    conn.close()
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
