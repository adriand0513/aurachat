# auth.py - Authentication utilities for Isabella (no verification required)
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, ExpiredSignatureError, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import sqlite3
import os
import logging

from config import JWT_SECRET, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

# ── DB Path Standardization ─────────────────────────────────────────────────
DB_PATH = os.path.abspath(os.getenv("DB_PATH", "isabella.db"))
logger.debug(f"auth.py: Using DB at: {DB_PATH}")
logger.debug(f"auth.py: DB exists? {os.path.exists(DB_PATH)}")

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 scheme for JWT bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verify error: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_user_by_email(email: str) -> Optional[dict]:
    email = email.lower().strip()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT id, email, hashed_password FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticate user with email + password.
    No verification step required.
    """
    email = email.lower().strip()
    user = get_user_by_email(email)
    if not user:
        logger.info(f"Auth failed: No user found for '{email}'")
        return None

    if not verify_password(password, user["hashed_password"]):
        logger.info(f"Auth failed: Incorrect password for '{email}'")
        return None

    logger.info(f"Auth success for '{email}' (user id {user['id']})")
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise credentials_exception
    except Exception as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise credentials_exception

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if user is None:
            raise credentials_exception
        return dict(user)
    finally:
        conn.close()