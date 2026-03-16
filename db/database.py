#!/usr/bin/env python3
"""
Database module for Fund Daily
支持 SQLite 和 PostgreSQL
"""

import os
import sqlite3
import logging
import threading
from typing import Optional, Dict, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 数据库配置
DB_TYPE = os.environ.get("FUND_DAILY_DB_TYPE", "sqlite")  # sqlite 或 postgres
DB_PATH = os.environ.get("FUND_DAILY_DB_PATH", "/app/data/fund-daily.db")

# PostgreSQL 配置
DB_HOST = os.environ.get("FUND_DAILY_DB_HOST", "localhost")
DB_PORT = os.environ.get("FUND_DAILY_DB_PORT", "5432")
DB_NAME = os.environ.get("FUND_DAILY_DB_NAME", "fund_daily")
DB_USER = os.environ.get("FUND_DAILY_DB_USER", "kid")
DB_PASSWORD = os.environ.get("FUND_DAILY_DB_PASSWORD", "")


def get_placeholder():
    """根据数据库类型返回正确的占位符"""
    return "%s" if DB_TYPE == "postgres" else "?"


_pg_conn = None
_pg_conn_count = 0

# PostgreSQL 连接池（线程本地存储）
_pg_local = threading.local()


def get_db():
    """获取数据库连接（根据配置自动选择）"""
    if DB_TYPE == "postgres":
        return get_pg_connection()
    else:
        return get_sqlite_connection()


def get_sqlite_connection():
    """获取 SQLite 连接"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.executescript("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=30000; PRAGMA synchronous=NORMAL;")
    return conn


def get_cursor(conn):
    """统一游标获取"""
    if DB_TYPE == "postgres":
        return conn.cursor()
    else:
        return conn.cursor()


def get_pg_connection():
    """获取 PostgreSQL 连接（使用线程本地存储连接池）"""
    import psycopg2
    
    # 检查线程本地存储是否有可用连接
    if hasattr(_pg_local, 'conn') and _pg_local.conn:
        try:
            # 验证连接是否有效
            _pg_local.conn.execute("SELECT 1")
            return _pg_local.conn
        except Exception:
            # 连接无效，关闭并重建
            try:
                _pg_local.conn.close()
            except Exception:
                pass
            _pg_local.conn = None
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        _pg_local.conn = conn
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL 连接失败: {e}")
        # 回退到 SQLite
        return get_sqlite_connection()


def init_db():
    """初始化数据库表"""
    if DB_TYPE == "postgres":
        init_pg_db()
    else:
        init_sqlite_db()


def init_sqlite_db():
    """初始化 SQLite 表"""
    conn = get_sqlite_connection()
    cursor = conn.cursor()

    ph = get_placeholder()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    ph = get_placeholder()

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

    ph = get_placeholder()

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

    ph = get_placeholder()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            user_id TEXT PRIMARY KEY,
            config TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    ph = get_placeholder()

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

    if hasattr(conn, "commit"): conn.commit()
    conn.close()
    logger.info("SQLite 数据库初始化完成")


def init_pg_db():
    """初始化 PostgreSQL 表"""
    conn = get_pg_connection()
    cursor = conn.cursor()

    ph = get_placeholder()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    ph = get_placeholder()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id SERIAL PRIMARY KEY,
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

    ph = get_placeholder()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            code TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, code)
        )
    """)

    ph = get_placeholder()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            user_id TEXT PRIMARY KEY,
            config TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    ph = get_placeholder()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    if hasattr(conn, "commit"): conn.commit()
    cursor.close()
    conn.close()
    logger.info("PostgreSQL 数据库初始化完成")


# ============== User Operations ==============

def create_user(username, password_hash):
    """Create a new user"""
    import uuid
    user_id = str(uuid.uuid4())
    
    conn = get_db()
    try:
        ph = get_placeholder()

        cursor = get_cursor(conn); cursor.execute(
            "INSERT INTO users (user_id, username, password) VALUES (%s, %s, %s)",
            (user_id, username, password_hash),
        )
        if hasattr(conn, "commit"): conn.commit()
        return user_id
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(f"创建用户失败: {e}")
        return None
    finally:
        conn.close()


def get_user_by_username(username):
    """Get user by username"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(zip([desc[0] for desc in cursor.description], row)) if row else None


def verify_user(username: str, password: str) -> Optional[Dict]:
    """Verify user credentials"""
    user = get_user_by_username(username)
    if not user:
        return None
    
    from web.api.auth import verify_password
    if verify_password(password, user["password"]):
        return user
    return None


def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(zip([desc[0] for desc in cursor.description], row)) if row else None


def update_user_password(user_id, new_password_hash):
    """Update user password"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (new_password_hash, user_id))
    if hasattr(conn, "commit"): conn.commit()
    conn.close()


# ============== Holdings Operations ==============

def get_holdings(user_id):
    """Get all holdings for a user"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute(
        "SELECT code, name, amount, buy_nav, buy_date FROM holdings WHERE user_id = %s",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip([c[0] for c in cursor.description], row)) for row in rows]


def get_all_holdings():
    """Get all holdings (admin)"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute("SELECT * FROM holdings")
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip([c[0] for c in cursor.description], row)) for row in rows]


def save_holdings(user_id, holdings):
    """Save/update holdings for a user"""
    conn = get_db()
    for h in holdings:
        ph = get_placeholder()

        cursor = get_cursor(conn); cursor.execute(
            """
            INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
            VALUES (%s, %s, %s, %s, %s, %s)
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
                h.get("name") or "",
                h.get("amount", 0),
                h.get("buy_nav") or h.get("buyNav") or None,
                h.get("buy_date") or h.get("buyDate") or None,
            ),
        )
    if hasattr(conn, "commit"): conn.commit()
    conn.close()


def save_holding(user_id, code, amount, name="", buy_nav=None, buy_date=None):
    """Save/update a single holding"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute(
        """
        INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(user_id, code) DO UPDATE SET
            name = excluded.name,
            amount = excluded.amount,
            buy_nav = excluded.buy_nav,
            buy_date = excluded.buy_date,
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, code, name, amount, buy_nav, buy_date),
    )
    if hasattr(conn, "commit"): conn.commit()
    conn.close()


def delete_holding(user_id, code):
    """Delete a holding"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute("DELETE FROM holdings WHERE user_id = %s AND code = %s", (user_id, code))
    if hasattr(conn, "commit"): conn.commit()
    conn.close()


def clear_holdings(user_id):
    """Clear all holdings for a user"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute("DELETE FROM holdings WHERE user_id = %s", (user_id,))
    if hasattr(conn, "commit"): conn.commit()
    conn.close()


# ============== Config Operations ==============

def get_user_config(user_id):
    """Get user config"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute("SELECT config FROM config WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        import json
        return json.loads(row[0])
    return {}


def save_user_config(user_id, config):
    """Save user config"""
    import json
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute(
        """
        INSERT INTO config (user_id, config) VALUES (%s, %s)
        ON CONFLICT(user_id) DO UPDATE SET
            config = excluded.config,
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, json.dumps(config)),
    )
    if hasattr(conn, "commit"): conn.commit()
    conn.close()


# ============== Watchlist Operations ==============

def get_watchlist(user_id):
    """Get user watchlist"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute(
        "SELECT code FROM watchlist WHERE user_id = %s",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def add_to_watchlist(user_id, code):
    """Add to watchlist"""
    conn = get_db()
    try:
        ph = get_placeholder()

        cursor = get_cursor(conn); cursor.execute(
            "INSERT INTO watchlist (user_id, code) VALUES (%s, %s)",
            (user_id, code),
        )
        if hasattr(conn, "commit"): conn.commit()
    except Exception as e:
        logger.error(f"Error: {e}")
        pass
    finally:
        conn.close()


def remove_from_watchlist(user_id, code):
    """Remove from watchlist"""
    conn = get_db()
    ph = get_placeholder()

    cursor = get_cursor(conn); cursor.execute(
        "DELETE FROM watchlist WHERE user_id = %s AND code = %s",
        (user_id, code),
    )
    if hasattr(conn, "commit"): conn.commit()
    conn.close()


# ============== Migration ==============

def migrate_from_json(json_file):
    """从 JSON 文件迁移数据"""
    import json
    with open(json_file, "r") as f:
        data = json.load(f)
    
    conn = get_db()
    for user_id, holdings in data.items():
        for h in holdings:
            ph = get_placeholder()

            cursor = get_cursor(conn); cursor.execute(
                """
                INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id, code) DO UPDATE SET
                    name = excluded.name,
                    amount = excluded.amount
                """,
                (
                    user_id,
                    h.get("code", ""),
                    h.get("name", ""),
                    h.get("amount", 0),
                    h.get("buy_nav", ""),
                    h.get("buy_date", ""),
                ),
            )
    if hasattr(conn, "commit"): conn.commit()
    conn.close()
    logger.info(f"从 {json_file} 迁移完成")


def batch_save_holdings(user_id: str, holdings: List[Dict]) -> None:
    """批量保存持仓（使用事务）"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        for h in holdings:
            ph = get_placeholder()

            cursor.execute(
                """
                INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
                VALUES (%s, %s, %s, %s, %s, %s)
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
                    h.get("buy_nav"),
                    h.get("buy_date"),
                ),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"批量保存失败: {e}")
    finally:
        cursor.close()
        conn.close()
