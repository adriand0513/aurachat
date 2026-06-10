# auth.py - Clean PostgreSQL Version
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import psycopg2
import logging
from config import JWT_SECRET, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, DATABASE_URL

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def ensure_users_table():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Create table with all columns
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscription_tier TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expires_at TIMESTAMP
            )
        ''')
        
        # Add missing columns safely
        cur.execute('''
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS subscription_tier TEXT DEFAULT 'free',
            ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
            ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
            ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'inactive',
            ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP;
        ''')
        
        conn.commit()
        logger.info("✅ Users table fully ensured with subscription columns")
    except Exception as e:
        logger.error(f"Table migration error: {e}")
    finally:
        cur.close()
        conn.close()


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verify error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def register_user(email: str, password: str, full_name: str):
    email = email.lower().strip()
    ensure_users_table()
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        hashed = get_password_hash(password)
        cur.execute('''
            INSERT INTO users (email, hashed_password, full_name)
            VALUES (%s, %s, %s)
        ''', (email, hashed, full_name))
        conn.commit()
        logger.info(f"✅ Registered: {email}")
        return True
    except psycopg2.errors.UniqueViolation:
        logger.warning(f"Email already exists: {email}")
        return False
    except Exception as e:
        logger.error(f"Register error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def authenticate_user(email: str, password: str):
    email = email.lower().strip()
    ensure_users_table()
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, email, hashed_password, full_name 
            FROM users WHERE email = %s
        """, (email,))
        user = cur.fetchone()
        
        if not user:
            logger.info(f"Login failed: User not found - {email}")
            return None

        if not verify_password(password, user[2]):
            logger.info(f"Login failed: Wrong password for {email}")
            return None

        logger.info(f"✅ Login successful: {email}")
        return {
            "id": user[0],
            "email": user[1],
            "full_name": user[3]
        }
    finally:
        cur.close()
        conn.close()


def update_user_subscription(user_id: int, tier: str, stripe_subscription_id: str = None, status: str = "active"):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE users 
            SET subscription_tier = %s,
                stripe_subscription_id = %s,
                subscription_status = %s,
                subscription_expires_at = CURRENT_TIMESTAMP + INTERVAL '1 month'
            WHERE id = %s
        ''', (tier, stripe_subscription_id, status, user_id))
        conn.commit()
        logger.info(f"✅ Subscription updated for user {user_id} to {tier}")
        return True
    except Exception as e:
        logger.error(f"Subscription update error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise credentials_exception

    ensure_users_table()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, email, full_name, subscription_tier 
            FROM users WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()
        if user is None:
            raise credentials_exception
        return {
            "id": user[0],
            "email": user[1],
            "full_name": user[2],
            "subscription_tier": user[3] if len(user) > 3 else "free"
        }
    finally:
        cur.close()
        conn.close()


# Ensure table on import
ensure_users_table()
