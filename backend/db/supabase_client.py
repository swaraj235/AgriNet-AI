"""
AgriNet AI — Supabase Client
Provides a singleton Supabase client + fallback SQLite for when keys aren't set.
"""

import os
import sqlite3
import time
import hashlib
import secrets
from functools import lru_cache
from typing import Optional

from backend.config import get_settings

settings = get_settings()

# ── Supabase ──────────────────────────────────────────────────────────────────
_supabase_client = None

def get_supabase():
    """Return Supabase client if configured, else None."""
    global _supabase_client
    if _supabase_client is None and settings.has_supabase:
        try:
            from supabase import create_client
            _supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key or settings.supabase_anon_key,
            )
        except Exception as e:
            print(f"[Supabase] Init failed: {e}. Using SQLite fallback.")
    return _supabase_client


# ── SQLite Fallback ───────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../agrinet.db")

def _get_sqlite():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_sqlite():
    """Create tables for SQLite fallback mode."""
    conn = _get_sqlite()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL UNIQUE,
            phone       TEXT DEFAULT '',
            password    TEXT NOT NULL,
            language    TEXT DEFAULT 'en',
            region      TEXT DEFAULT '',
            lat         REAL,
            lon         REAL,
            created_at  REAL NOT NULL,
            last_login  REAL
        );

        CREATE TABLE IF NOT EXISTS crop_queries (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            soil_type    TEXT,
            water_level  TEXT,
            land_size    TEXT,
            temperature  REAL,
            humidity     REAL,
            ph           REAL,
            rainfall     REAL,
            result_crop  TEXT,
            result_score REAL,
            location     TEXT,
            queried_at   REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transport_pools (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            farmer_count INTEGER,
            base_cost    REAL,
            pooled_cost  REAL,
            savings      REAL,
            route        TEXT,
            created_at   REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS weather_cache (
            cache_key    TEXT PRIMARY KEY,
            data         TEXT NOT NULL,
            cached_at    REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            messages     TEXT NOT NULL,
            created_at   REAL NOT NULL,
            updated_at   REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_crop_user ON crop_queries(user_id);
    """)
    conn.commit()
    conn.close()


# ── Unified DB API ────────────────────────────────────────────────────────────

import json
import bcrypt

def create_user(name: str, email: str, password: str, phone: str = "", language: str = "en") -> Optional[dict]:
    """Create user. Returns user dict or None if email exists."""
    sb = get_supabase()
    uid = secrets.token_hex(16)
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now = time.time()

    if sb:
        try:
            # Use Supabase Auth
            auth_resp = sb.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"name": name, "phone": phone, "language": language}
            })
            uid = auth_resp.user.id
            sb.table("profiles").insert({
                "id": uid, "name": name, "email": email,
                "phone": phone, "language": language, "created_at": now
            }).execute()
            return {"id": uid, "name": name, "email": email, "language": language, "region": ""}
        except Exception as e:
            print(f"[Supabase] create_user error: {e}")
            return None
    else:
        conn = _get_sqlite()
        try:
            conn.execute(
                "INSERT INTO users (id,name,email,phone,password,language,created_at) VALUES (?,?,?,?,?,?,?)",
                (uid, name.strip(), email.strip().lower(), phone, hashed, language, now)
            )
            conn.commit()
            return {"id": uid, "name": name.strip(), "email": email.strip().lower(), "language": language, "region": ""}
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate user. Returns user dict or None."""
    sb = get_supabase()

    if sb:
        try:
            auth_resp = sb.auth.sign_in_with_password({"email": email, "password": password})
            uid = auth_resp.user.id
            meta = auth_resp.user.user_metadata or {}
            return {
                "id": uid,
                "name": meta.get("name", email.split("@")[0]),
                "email": email,
                "language": meta.get("language", "en"),
                "region": meta.get("region", ""),
                "access_token": auth_resp.session.access_token,
            }
        except Exception:
            return None
    else:
        conn = _get_sqlite()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
            if not row:
                return None
            if bcrypt.checkpw(password.encode(), row["password"].encode()):
                conn.execute("UPDATE users SET last_login=? WHERE id=?", (time.time(), row["id"]))
                conn.commit()
                return {"id": row["id"], "name": row["name"], "email": row["email"],
                        "language": row["language"], "region": row["region"]}
            return None
        finally:
            conn.close()


def get_user_by_id(user_id: str) -> Optional[dict]:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("profiles").select("*").eq("id", user_id).single().execute()
            return res.data
        except Exception:
            return None
    else:
        conn = _get_sqlite()
        try:
            row = conn.execute("SELECT id,name,email,language,region FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def log_crop_query(user_id: str, data: dict):
    sb = get_supabase()
    record = {"id": secrets.token_hex(8), "user_id": user_id, **data, "queried_at": time.time()}
    if sb:
        try:
            sb.table("crop_queries").insert(record).execute()
        except Exception as e:
            print(f"[Supabase] log_crop_query: {e}")
    else:
        conn = _get_sqlite()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO crop_queries
                   (id,user_id,soil_type,water_level,land_size,result_crop,result_score,queried_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (record["id"], user_id, data.get("soil_type"), data.get("water_level"),
                 data.get("land_size"), data.get("result_crop"), data.get("result_score"), record["queried_at"])
            )
            conn.commit()
        finally:
            conn.close()


def get_weather_cache(cache_key: str, ttl_seconds: int = 600) -> Optional[dict]:
    """Return cached weather data if fresh, else None."""
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("weather_cache").select("*").eq("cache_key", cache_key).single().execute()
            if res.data and (time.time() - res.data["cached_at"]) < ttl_seconds:
                return json.loads(res.data["data"])
        except Exception:
            pass
        return None
    else:
        conn = _get_sqlite()
        try:
            row = conn.execute("SELECT * FROM weather_cache WHERE cache_key=?", (cache_key,)).fetchone()
            if row and (time.time() - row["cached_at"]) < ttl_seconds:
                return json.loads(row["data"])
        finally:
            conn.close()
        return None


def set_weather_cache(cache_key: str, data: dict):
    """Store weather data in cache."""
    sb = get_supabase()
    payload = {"cache_key": cache_key, "data": json.dumps(data), "cached_at": time.time()}
    if sb:
        try:
            sb.table("weather_cache").upsert(payload).execute()
        except Exception:
            pass
    else:
        conn = _get_sqlite()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO weather_cache (cache_key,data,cached_at) VALUES (?,?,?)",
                (cache_key, payload["data"], payload["cached_at"])
            )
            conn.commit()
        finally:
            conn.close()
