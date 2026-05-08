"""
AgriNet AI — JWT Auth Middleware
Supports Supabase JWT + custom JWT fallback.
"""

import time
import secrets
import functools
from typing import Optional

import jwt
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.config import get_settings

settings = get_settings()
_security = HTTPBearer(auto_error=False)


def _verify_custom_jwt(token: str) -> Optional[dict]:
    """Verify a custom-signed JWT (fallback when Supabase isn't configured)."""
    try:
        payload = jwt.decode(token, settings.app_secret, algorithms=["HS256"])
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except jwt.InvalidTokenError:
        return None


def _verify_supabase_jwt(token: str) -> Optional[dict]:
    """Verify a Supabase access token using Supabase admin API."""
    try:
        from backend.db.supabase_client import get_supabase
        sb = get_supabase()
        if not sb:
            return None
        user = sb.auth.get_user(token)
        if user and user.user:
            u = user.user
            meta = u.user_metadata or {}
            return {
                "user_id": u.id,
                "email": u.email,
                "name": meta.get("name", u.email.split("@")[0] if u.email else "Farmer"),
                "language": meta.get("language", "en"),
            }
    except Exception:
        pass
    return None


def create_custom_jwt(user: dict) -> str:
    """Create a custom JWT for SQLite fallback mode."""
    payload = {
        "user_id": user["id"],
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "language": user.get("language", "en"),
        "exp": time.time() + 86400,
        "iat": time.time(),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.app_secret, algorithm="HS256")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> dict:
    """FastAPI dependency — extracts & verifies the Bearer token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization required")

    token = credentials.credentials

    # Try Supabase first
    if settings.has_supabase:
        payload = _verify_supabase_jwt(token)
        if payload:
            return payload

    # Fallback to custom JWT
    payload = _verify_custom_jwt(token)
    if payload:
        return payload

    raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> Optional[dict]:
    """Like get_current_user but doesn't raise — returns None for unauthenticated."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
