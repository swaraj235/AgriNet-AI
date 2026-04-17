"""
AgriNet AI — Database Layer (SQLite + bcrypt)
Handles schema creation, user management, and query logging.
"""

import sqlite3
import bcrypt
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agrinet.db')


def get_db():
    """Get a fresh database connection with row_factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            phone       TEXT    DEFAULT '',
            password    TEXT    NOT NULL,
            language    TEXT    DEFAULT 'en',
            region      TEXT    DEFAULT '',
            created_at  REAL    NOT NULL,
            last_login  REAL
        );

        CREATE TABLE IF NOT EXISTS crop_queries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            soil_type   TEXT    NOT NULL,
            water_level TEXT    NOT NULL,
            land_size   TEXT    NOT NULL,
            result_crop TEXT,
            result_score REAL,
            queried_at  REAL    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS transport_pools (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            farmer_count    INTEGER NOT NULL,
            base_cost       REAL    NOT NULL,
            pooled_cost     REAL    NOT NULL,
            savings         REAL    NOT NULL,
            created_at      REAL    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_crop_queries_user ON crop_queries(user_id);
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ===== User Operations =====

def create_user(name, email, password, phone='', language='en', region=''):
    """Create a new user with bcrypt-hashed password. Returns user dict or None."""
    conn = get_db()
    try:
        # Hash password with bcrypt (auto-generates salt)
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (name, email, password, phone, language, region, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name.strip(), email.strip().lower(), hashed.decode('utf-8'),
             phone.strip(), language, region, time.time())
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {
            'id': user_id,
            'name': name.strip(),
            'email': email.strip().lower(),
            'language': language,
            'region': region
        }
    except sqlite3.IntegrityError:
        return None  # Duplicate email
    finally:
        conn.close()


def authenticate_user(email, password):
    """Verify email + password. Returns user dict or None."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
        row = cursor.fetchone()

        if row is None:
            return None

        # Verify bcrypt hash
        if bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
            # Update last_login
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (time.time(), row['id']))
            conn.commit()
            return {
                'id': row['id'],
                'name': row['name'],
                'email': row['email'],
                'language': row['language'],
                'region': row['region']
            }
        return None
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Look up user by ID. Returns dict or None."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, language, region, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ===== Query Logging =====

def log_crop_query(user_id, soil, water, land, result_crop, result_score):
    """Log a crop AI query for analytics."""
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO crop_queries (user_id, soil_type, water_level, land_size, result_crop, result_score, queried_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, soil, water, land, result_crop, result_score, time.time())
        )
        conn.commit()
    finally:
        conn.close()


def log_transport_pool(user_id, farmer_count, base_cost, pooled_cost, savings):
    """Log a transport pool calculation."""
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO transport_pools (user_id, farmer_count, base_cost, pooled_cost, savings, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, farmer_count, base_cost, pooled_cost, savings, time.time())
        )
        conn.commit()
    finally:
        conn.close()


def get_user_history(user_id, limit=10):
    """Get recent crop queries for a user."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM crop_queries WHERE user_id = ? ORDER BY queried_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    print("[DB] Schema ready.")
