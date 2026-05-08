"""
AgriNet AI — Auth Routes
Handles signup, login, profile — with Supabase + SQLite fallback.
"""

import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from backend.db.supabase_client import create_user, authenticate_user, get_user_by_id
from backend.auth import create_custom_jwt, get_current_user
from backend.config import get_settings
from fastapi import Depends

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: str = ""
    language: str = "en"

    @field_validator("name")
    @classmethod
    def name_valid(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v[:100]

    @field_validator("email")
    @classmethod
    def email_valid(cls, v):
        v = v.strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("language")
    @classmethod
    def lang_valid(cls, v):
        return v[:5] if v in ("en", "hi", "mr", "ta", "te", "kn", "gu") else "en"


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup", status_code=201)
async def signup(body: SignupRequest):
    user = create_user(body.name, body.email, body.password, body.phone, body.language)
    if user is None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # If Supabase gave us an access_token use it, otherwise mint a custom JWT
    token = user.pop("access_token", None) or create_custom_jwt(user)
    return {"token": token, "user": user}


@router.post("/login")
async def login(body: LoginRequest):
    email = body.email.strip().lower()
    user = authenticate_user(email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = user.pop("access_token", None) or create_custom_jwt(user)
    return {"token": token, "user": user}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    uid = current_user.get("user_id") or current_user.get("id")
    user = get_user_by_id(uid)
    if not user:
        # Return info from token itself
        return {"user": current_user}
    return {"user": user}
