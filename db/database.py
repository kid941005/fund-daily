#!/usr/bin/env python3
"""
Database module for Fund Daily
SQLite-based storage for users, holdings, and config
"""

import sqlite3
import os
import json

# Database path - use environment variable or default to /app/data
DB_PATH = os.environ.get("FUND_DAILY_DB_PATH", "/app/data/fund-daily.db")


def get_db():
    """Get database connection with optimized settings for concurrency"""
    # Ensure database directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    # Set busy timeout to wait for locks (30 seconds)
    conn.execute("PRAGMA busy_timeout=30000")
    # Synchronous mode - NORMAL is safe with WAL
    conn.execute("PRAGMA synchronous=NORMAL")
    
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Holdings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            amount REAL DEFAULT 0,
            buy_nav REAL,
            buy_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, code)
        )
    """)

    # Watchlist table (funds to track)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            code TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, code)
        )
    """)

    # Config table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            user_id TEXT PRIMARY KEY,
            config_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # History table (optional, for analytics)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")


# ============== User Operations ==============


def create_user(username, password_hash):
    """Create a new user"""
    import secrets

    user_id = secrets.token_hex(8)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (user_id, username, password) VALUES (?, ?, ?)", (user_id, username, password_hash)
        )
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username):
    """Get user by username"""
    conn = get_db()
    cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db()
    cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_password(user_id, new_password_hash):
    """Update user password"""
    conn = get_db()
    conn.execute("UPDATE users SET password = ? WHERE user_id = ?", (new_password_hash, user_id))
    conn.commit()
    conn.close()


# ============== Holdings Operations ==============


def get_holdings(user_id):
    """Get all holdings for a user"""
    conn = get_db()
    cursor = conn.execute(
        "SELECT code, name, amount, buy_nav, buy_date FROM holdings WHERE user_id = ? AND amount > 0", (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_holdings(user_id, holdings):
    """Save/更新 holdings for a user"""
    conn = get_db()
    for h in holdings:
        conn.execute(
            """
            INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, code) DO UPDATE SET
                name = excluded.name,
                amount = excluded.amount,
                buy_nav = excluded.buy_nav,
                buy_date = excluded.buy_date,
                updated_at = CURRENT_TIMESTAMP
        """,
            (
                user_id,
                h.get("code", ""),
                h.get("name", ""),
                h.get("amount", 0),
                h.get("buyNav", ""),
                h.get("buyDate", ""),
            ),
        )
    conn.commit()
    conn.close()


def delete_holding(user_id, code):
    """Delete a holding"""
    conn = get_db()
    conn.execute("DELETE FROM holdings WHERE user_id = ? AND code = ?", (user_id, code))
    conn.commit()
    conn.close()


# ============== Config Operations ==============


def get_user_config(user_id):
    """Get user config"""
    conn = get_db()
    cursor = conn.execute("SELECT config_json FROM config WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row["config_json"]:
        return json.loads(row["config_json"])
    return {}


def save_user_config(user_id, config):
    """Save user config"""
    conn = get_db()
    conn.execute(
        """
        INSERT INTO config (user_id, config_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            config_json = excluded.config_json,
            updated_at = CURRENT_TIMESTAMP
    """,
        (user_id, json.dumps(config)),
    )
    conn.commit()
    conn.close()


# ============== Watchlist Operations ==============


def get_watchlist(user_id):
    """Get user's watchlist"""
    conn = get_db()
    cursor = conn.execute("SELECT code FROM watchlist WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row["code"] for row in rows]


def add_to_watchlist(user_id, code):
    """Add fund to watchlist"""
    conn = get_db()
    try:
        conn.execute("INSERT INTO watchlist (user_id, code) VALUES (?, ?)", (user_id, code))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def remove_from_watchlist(user_id, code):
    """Remove fund from watchlist"""
    conn = get_db()
    conn.execute("DELETE FROM watchlist WHERE user_id = ? AND code = ?", (user_id, code))
    conn.commit()
    conn.close()


# ============== Migration Helper ==============


def migrate_from_json(json_file):
    """Migrate data from JSON file to SQLite"""
    if not os.path.exists(json_file):
        print(f"JSON file not found: {json_file}")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_db()

    for user_id, user_data in data.items():
        username = user_data.get("username")
        password = user_data.get("password", "")

        try:
            conn.execute(
                "INSERT INTO users (user_id, username, password) VALUES (?, ?, ?)", (user_id, username, password)
            )

            # Migrate holdings
            holdings = user_data.get("holdings", [])
            for h in holdings:
                conn.execute(
                    """
                    INSERT INTO holdings (user_id, code, name, amount)
                    VALUES (?, ?, ?, ?)
                """,
                    (user_id, h.get("code", ""), h.get("name", ""), h.get("amount", 0)),
                )

        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print(f"Migration complete from {json_file}")


if __name__ == "__main__":
    init_db()
