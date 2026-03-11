# memory.py - Database operations for Isabella chatbot
import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

# ── DB Path Standardization ─────────────────────────────────────────────────
DB_PATH = os.path.abspath(os.getenv("DB_PATH", "users.db"))
print(f"memory.py: Using DB at: {DB_PATH}")
print(f"memory.py: DB exists? {os.path.exists(DB_PATH)}")

def init_db():
    """Create all necessary tables if they don't exist."""
    print("=== init_db() STARTED ===")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("Creating users table...")
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            hashed_password TEXT NOT NULL,
            phone TEXT UNIQUE,                       -- E.164 format, e.g. +19725551234
            is_phone_verified INTEGER DEFAULT 0,     -- 0 = not verified, 1 = verified
            phone_verified_at DATETIME,              -- timestamp of successful verification
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            age_confirmed BOOLEAN DEFAULT FALSE,
            flagged INTEGER DEFAULT 0
        )
    """)

    print("Creating chat_history table...")
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    print("Creating analytics table...")
    c.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            turns INTEGER DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    print("Creating user_pics table...")
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_pics (
            user_id INTEGER PRIMARY KEY,
            pic_count_this_month INTEGER DEFAULT 0,
            month_year TEXT DEFAULT (strftime('%Y-%m', 'now')),
            seen_pics TEXT DEFAULT '',
            last_pic_timestamp DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    print("Creating violations table...")
    c.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            context TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print(f"=== init_db() FINISHED SUCCESSFULLY ===")
    print(f"Database location: {DB_PATH}")

def create_user(email: Optional[str], hashed_password: str, phone: Optional[str] = None) -> int:
    """Create new user (used during phone verification if no account exists)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT INTO users (email, hashed_password, phone) 
            VALUES (?, ?, ?)
            """,
            (email.lower().strip() if email else None, hashed_password, phone)
        )
        conn.commit()
        user_id = c.lastrowid
        print(f"New user created: email={email or 'None'}, phone={phone or 'None'} (ID: {user_id})")
        return user_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE constraint failed: users.email" in str(e) and email:
            c.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),))
            existing = c.fetchone()
            if existing:
                print(f"Duplicate email {email} → returning existing ID {existing[0]}")
                return existing[0]
        elif "UNIQUE constraint failed: users.phone" in str(e) and phone:
            c.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            existing = c.fetchone()
            if existing:
                print(f"Duplicate phone {phone} → returning existing ID {existing[0]}")
                return existing[0]
        raise ValueError("Conflict creating user (duplicate email or phone)")
    finally:
        conn.close()

def get_user_by_phone(phone: str) -> Optional[dict]:
    """Fetch user by phone number."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, email, hashed_password, is_phone_verified, phone_verified_at 
        FROM users 
        WHERE phone = ?
    """, (phone,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_history(user_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT role, content 
        FROM chat_history 
        WHERE user_id = ? 
        ORDER BY timestamp ASC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def save_message(user_id: int, message: Dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, message["role"], message["content"])
        )
        c.execute("""
            INSERT INTO analytics (user_id, turns) 
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET turns = turns + 1
        """, (user_id,))
        conn.commit()
    finally:
        conn.close()

def can_send_pic(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    current_month = datetime.now().strftime('%Y-%m')

    try:
        c.execute("SELECT pic_count_this_month, month_year FROM user_pics WHERE user_id = ?", (user_id,))
        row = c.fetchone()

        if row is None:
            c.execute(
                "INSERT INTO user_pics (user_id, pic_count_this_month, month_year, seen_pics) "
                "VALUES (?, 0, ?, '')",
                (user_id, current_month)
            )
            conn.commit()
            return True

        count, month_year = row

        if month_year != current_month:
            c.execute(
                "UPDATE user_pics SET pic_count_this_month = 0, month_year = ?, seen_pics = '' "
                "WHERE user_id = ?",
                (current_month, user_id)
            )
            conn.commit()
            count = 0

        return count < 5
    finally:
        conn.close()

def increment_pic_count(user_id: int, sent_pic_filename: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT seen_pics FROM user_pics WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        seen_pics = row[0] if row else ''
        seen_list = [f for f in seen_pics.split(',') if f]
        if sent_pic_filename not in seen_list:
            seen_list.append(sent_pic_filename)
        new_seen = ','.join(seen_list)

        c.execute("""
            UPDATE user_pics 
            SET pic_count_this_month = pic_count_this_month + 1,
                seen_pics = ?,
                last_pic_timestamp = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (new_seen, user_id))
        conn.commit()
    finally:
        conn.close()

def get_user_stats() -> Dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            SELECT user_id, COUNT(*) as sessions, SUM(turns) as total_messages 
            FROM analytics 
            GROUP BY user_id
        """)
        rows = c.fetchall()
        total_messages = sum(r[2] or 0 for r in rows)
        unique_users = len(rows)
        users_list = [{"id": r[0], "messages": r[2] or 0} for r in rows]
        return {
            "unique_users": unique_users,
            "total_messages": total_messages,
            "users": users_list,
            "timestamp": datetime.now().isoformat()
        }
    finally:
        conn.close()

def is_age_confirmed(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT age_confirmed FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else False

def set_age_confirmed(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET age_confirmed = TRUE WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_phone_verified(user_id: int) -> bool:
    """Check if user's phone has been verified via OTP."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_phone_verified FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else False

def set_phone_verified(user_id: int, phone: str):
    """Mark user as phone-verified and store/update the phone number."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("""
        UPDATE users 
        SET phone = ?, 
            is_phone_verified = 1, 
            phone_verified_at = ?
        WHERE id = ?
    """, (phone, now, user_id))
    conn.commit()
    conn.close()
    print(f"Phone verified for user {user_id}: {phone}")

def flag_violation(user_id: int, message: str, history_context: str = ""):
    """Log a violation with full context for review."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO violations (user_id, message, context, timestamp) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, message, history_context)
        )
        c.execute("UPDATE users SET flagged = flagged + 1 WHERE id = ?", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Error logging violation: {e}")
    finally:
        conn.close()

def get_violation_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT flagged FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0