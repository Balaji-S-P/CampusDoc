import sqlite3
import json
from datetime import datetime
import os
DB_FILE = "tokens.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gmail_tokens (
        user_id TEXT PRIMARY KEY,
        access_token TEXT,
        refresh_token TEXT,
        token_expiry TEXT,
        scopes TEXT,
        email TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT,
        role TEXT
    )

    """)
    conn.commit()
    conn.close()

def save_tokens(user_id, creds, email):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO gmail_tokens (user_id, access_token, refresh_token, token_expiry, scopes, email)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        creds.token,
        creds.refresh_token,
        creds.expiry.isoformat() if creds.expiry else None,
        json.dumps(creds.scopes),
        email
    ))
    conn.commit()
    conn.close()

def get_tokens(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gmail_tokens WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "access_token": row[1],
        "refresh_token": row[2],
        "token_expiry": row[3],
        "scopes": json.loads(row[4]),
        "email": row[5],
    }

def user_exists(email):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def create_user(email, password, role):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, password, role))
    conn.commit()
    conn.close()

def get_user_id(email):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row[0]

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_user_email(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0]
