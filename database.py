import sqlite3
import datetime
from typing import Optional, Dict, Any

DB_FILE = "bot_database.db"

def init_db():
    """បង្កើតតារាងទុកទិន្នន័យ (Database Tables)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # តារាងរក្សាទុកព័ត៌មាន User
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # តារាងរក្សាទុកប្រតិបត្តិការបង់ប្រាក់
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        tran_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'pending',
        checkout_url TEXT,
        deeplink TEXT,
        invite_link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    conn.commit()
    conn.close()

def save_user(user_id: int, username: str, first_name: str, last_name: str = ""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO users (user_id, username, first_name, last_name)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name,
        last_name=excluded.last_name
    """, (user_id, username or "", first_name or "", last_name or ""))
    conn.commit()
    conn.close()

def save_payment(tran_id: str, user_id: int, amount: float, checkout_url: str, deeplink: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO payments (tran_id, user_id, amount, status, checkout_url, deeplink)
    VALUES (?, ?, ?, 'pending', ?, ?)
    """, (tran_id, user_id, amount, checkout_url, deeplink))
    conn.commit()
    conn.close()

def get_payment(tran_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE tran_id = ?", (tran_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def mark_payment_approved(tran_id: str, invite_link: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE payments
    SET status = 'approved',
        invite_link = ?,
        approved_at = ?
    WHERE tran_id = ?
    """, (invite_link, now, tran_id))
    conn.commit()
    conn.close()

def has_user_paid(user_id: int) -> bool:
    """ពិនិត្យមើលថាតើ User ធ្លាប់បានបង់លុយជោគជ័យរួចហើយឬនៅ"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 1 FROM payments WHERE user_id = ? AND status = 'approved' LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None
