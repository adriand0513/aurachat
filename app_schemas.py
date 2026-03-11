# app_schemas.py - Pydantic models for Isabella chatbot API
from pydantic import BaseModel, EmailStr
from typing import List, Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: str  # isoformat


class MessageCreate(BaseModel):
    message: str


class ReplyResponse(BaseModel):
    replies: List[str]
    voice_note: Optional[str] = None


class TipRequest(BaseModel):
    tip_type: str