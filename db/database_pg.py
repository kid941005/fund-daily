#!/usr/bin/env python3
"""
PostgreSQL Database Module for Fund Daily
直接使用 psycopg2，避免 SQLite 兼容性问题
"""

import os
import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# PostgreSQL 配置
DB_HOST = os.environ.get("FUND_DAILY_DB_HOST", "localhost")
DB_PORT = os.environ.get("FUND_DAILY_DB_PORT", "5432")
DB_NAME = os.environ.get("FUND_DAILY_DB_NAME", "fund_daily")
DB_USER = os.environ.get("FUND_DAILY_DB_USER", "kid")
DB_PASSWORD = os.environ.get("FUND_DAILY_DB_PASSWORD", "")

# 连接池
_connection_pool = None

def get_pool():
    """获取连接池"""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info("PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    return _connection_pool

@contextmanager
def get_db():
    """获取数据库连接"""
    conn = get_pool().getconn()
    try:
        yield conn
    finally:
        get_pool().putconn(conn)

@contextmanager
def get_cursor(conn):
    """获取字典游标"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
    finally:
        cursor.close()

def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            # Users 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(64) PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Holdings 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    code VARCHAR(16) NOT NULL,
                    name VARCHAR(255),
                    amount DECIMAL(12, 2) DEFAULT 0,
                    buy_nav DECIMAL(10, 4),
                    buy_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, code)
                )
            """)
            
            # 基金基本信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funds (
                    id SERIAL PRIMARY KEY,
                    fund_code VARCHAR(20) UNIQUE NOT NULL,
                    fund_name VARCHAR(200) NOT NULL,
                    fund_type VARCHAR(50),
                    fund_company VARCHAR(100),
                    establish_date DATE,
                    fund_size DECIMAL(15,2),
                    manager VARCHAR(100),
                    risk_level VARCHAR(20),
                    rating DECIMAL(3,1),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 基金净值表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_nav (
                    id SERIAL PRIMARY KEY,
                    fund_code VARCHAR(20) NOT NULL,
                    nav_date DATE NOT NULL,
                    net_value DECIMAL(10,4),
                    accumulated_value DECIMAL(10,4),
                    daily_return DECIMAL(8,4),
                    weekly_return DECIMAL(8,4),
                    monthly_return DECIMAL(8,4),
                    quarterly_return DECIMAL(8,4),
                    yearly_return DECIMAL(8,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(fund_code, nav_date),
                    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
                )
            """)
            
            # 基金评分表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_scores (
                    id SERIAL PRIMARY KEY,
                    fund_code VARCHAR(20) NOT NULL,
                    score_date DATE NOT NULL,
                    total_score INTEGER,
                    valuation_score INTEGER,
                    sector_score INTEGER,
                    risk_score INTEGER,
                    valuation_reason TEXT,
                    sector_reason TEXT,
                    risk_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(fund_code, score_date),
                    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
                )
            """)
            
            # Config 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    user_id VARCHAR(64) PRIMARY KEY,
                    config JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # History 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(64),
                    action VARCHAR(64),
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Watchlist 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(64),
                    code VARCHAR(16),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, code)
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_holdings_code ON holdings(code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_nav_fund_code ON fund_nav(fund_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_nav_date ON fund_nav(nav_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_scores_fund_code ON fund_scores(fund_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_scores_date ON fund_scores(score_date)")
            
            conn.commit()
            logger.info("Database tables initialized")

# 用户操作
def get_user_by_username(username):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return dict(cursor.fetchone()) if cursor.rowcount > 0 else None

def verify_user(username, password):
    """验证用户登录"""
    from src.auth import verify_password
    user = get_user_by_username(username)
    if not user:
        return None
    if verify_password(password, user.get("password", "")):
        return user
    return None

def get_user_by_id(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return dict(cursor.fetchone()) if cursor.rowcount > 0 else None

def create_user(user_id, username, password_hash):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute(
                "INSERT INTO users (user_id, username, password) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (user_id, username, password_hash)
            )
            conn.commit()

def update_user_password(user_id, new_password_hash):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("UPDATE users SET password = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", 
                         (new_password_hash, user_id))
            conn.commit()

# 持仓操作
def get_holdings(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute(
                "SELECT code, name, amount, buy_nav, buy_date FROM holdings WHERE user_id = %s",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

def save_holding(user_id, code, amount, name="", buy_nav=None, buy_date=None):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, code) DO UPDATE SET
                    name = EXCLUDED.name,
                    amount = EXCLUDED.amount,
                    buy_nav = EXCLUDED.buy_nav,
                    buy_date = EXCLUDED.buy_date,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, code, name, amount, buy_nav, buy_date))
            conn.commit()

def delete_holding(user_id, code):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("DELETE FROM holdings WHERE user_id = %s AND code = %s", (user_id, code))
            conn.commit()

def clear_holdings(user_id):
    """清空用户的所有持仓"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("DELETE FROM holdings WHERE user_id = %s", (user_id,))
            conn.commit()

# 其他操作...
def get_watchlist(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT code FROM watchlist WHERE user_id = %s", (user_id,))
            return [row['code'] for row in cursor.fetchall()]

def add_to_watchlist(user_id, code):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("INSERT INTO watchlist (user_id, code) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                         (user_id, code))
            conn.commit()

def remove_from_watchlist(user_id, code):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("DELETE FROM watchlist WHERE user_id = %s AND code = %s", (user_id, code))
            conn.commit()

def get_config(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT config FROM config WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            return row['config'] if row else None

def save_config(user_id, config):
    import json
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                INSERT INTO config (user_id, config) VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET config = EXCLUDED.config, updated_at = CURRENT_TIMESTAMP
            """, (user_id, json.dumps(config)))
            conn.commit()

# 基金数据操作函数
def save_fund_info(fund_code, fund_name, fund_type=None, fund_company=None, 
                   establish_date=None, fund_size=None, manager=None, 
                   risk_level=None, rating=None):
    """保存基金基本信息"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                INSERT INTO funds (
                    fund_code, fund_name, fund_type, fund_company,
                    establish_date, fund_size, manager, risk_level, rating
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fund_code) DO UPDATE SET
                    fund_name = EXCLUDED.fund_name,
                    fund_type = EXCLUDED.fund_type,
                    fund_company = EXCLUDED.fund_company,
                    establish_date = EXCLUDED.establish_date,
                    fund_size = EXCLUDED.fund_size,
                    manager = EXCLUDED.manager,
                    risk_level = EXCLUDED.risk_level,
                    rating = EXCLUDED.rating,
                    updated_at = CURRENT_TIMESTAMP
            """, (fund_code, fund_name, fund_type, fund_company, 
                  establish_date, fund_size, manager, risk_level, rating))
            conn.commit()

def save_fund_nav(fund_code, nav_date, net_value=None, accumulated_value=None,
                  daily_return=None, weekly_return=None, monthly_return=None,
                  quarterly_return=None, yearly_return=None):
    """保存基金净值数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            # 首先确保基金基本信息存在
            cursor.execute("INSERT INTO funds (fund_code, fund_name) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                         (fund_code, f"基金{fund_code}"))
            
            cursor.execute("""
                INSERT INTO fund_nav (
                    fund_code, nav_date, net_value, accumulated_value,
                    daily_return, weekly_return, monthly_return,
                    quarterly_return, yearly_return
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fund_code, nav_date) DO UPDATE SET
                    net_value = EXCLUDED.net_value,
                    accumulated_value = EXCLUDED.accumulated_value,
                    daily_return = EXCLUDED.daily_return,
                    weekly_return = EXCLUDED.weekly_return,
                    monthly_return = EXCLUDED.monthly_return,
                    quarterly_return = EXCLUDED.quarterly_return,
                    yearly_return = EXCLUDED.yearly_return,
                    created_at = CURRENT_TIMESTAMP
            """, (fund_code, nav_date, net_value, accumulated_value,
                  daily_return, weekly_return, monthly_return,
                  quarterly_return, yearly_return))
            conn.commit()

def save_fund_score(fund_code, score_date, total_score=None,
                    valuation_score=None, sector_score=None, risk_score=None,
                    valuation_reason=None, sector_reason=None, risk_reason=None):
    """保存基金评分数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            # 首先确保基金基本信息存在
            cursor.execute("INSERT INTO funds (fund_code, fund_name) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                         (fund_code, f"基金{fund_code}"))
            
            cursor.execute("""
                INSERT INTO fund_scores (
                    fund_code, score_date, total_score,
                    valuation_score, sector_score, risk_score,
                    valuation_reason, sector_reason, risk_reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fund_code, score_date) DO UPDATE SET
                    total_score = EXCLUDED.total_score,
                    valuation_score = EXCLUDED.valuation_score,
                    sector_score = EXCLUDED.sector_score,
                    risk_score = EXCLUDED.risk_score,
                    valuation_reason = EXCLUDED.valuation_reason,
                    sector_reason = EXCLUDED.sector_reason,
                    risk_reason = EXCLUDED.risk_reason,
                    created_at = CURRENT_TIMESTAMP
            """, (fund_code, score_date, total_score,
                  valuation_score, sector_score, risk_score,
                  valuation_reason, sector_reason, risk_reason))
            conn.commit()

def get_fund_info(fund_code):
    """获取基金基本信息"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM funds WHERE fund_code = %s", (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

def get_fund_nav(fund_code, nav_date=None):
    """获取基金净值数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            if nav_date:
                cursor.execute("SELECT * FROM fund_nav WHERE fund_code = %s AND nav_date = %s", 
                             (fund_code, nav_date))
            else:
                cursor.execute("SELECT * FROM fund_nav WHERE fund_code = %s ORDER BY nav_date DESC LIMIT 1", 
                             (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

def get_fund_score(fund_code, score_date=None):
    """获取基金评分数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            if score_date:
                cursor.execute("SELECT * FROM fund_scores WHERE fund_code = %s AND score_date = %s", 
                             (fund_code, score_date))
            else:
                cursor.execute("SELECT * FROM fund_scores WHERE fund_code = %s ORDER BY score_date DESC LIMIT 1", 
                             (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

def get_recent_funds(days=7):
    """获取最近有更新的基金"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                SELECT DISTINCT f.*, 
                       fn.nav_date as last_nav_date,
                       fn.net_value as last_net_value,
                       fs.score_date as last_score_date,
                       fs.total_score as last_total_score
                FROM funds f
                LEFT JOIN fund_nav fn ON f.fund_code = fn.fund_code 
                    AND fn.nav_date = (SELECT MAX(nav_date) FROM fund_nav WHERE fund_code = f.fund_code)
                LEFT JOIN fund_scores fs ON f.fund_code = fs.fund_code 
                    AND fs.score_date = (SELECT MAX(score_date) FROM fund_scores WHERE fund_code = f.fund_code)
                WHERE f.updated_at >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY f.updated_at DESC
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

def search_funds(query):
    """搜索基金"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                SELECT * FROM funds 
                WHERE fund_code LIKE %s OR fund_name LIKE %s
                ORDER BY fund_code
                LIMIT 20
            """, (f"%{query}%", f"%{query}%"))
            return [dict(row) for row in cursor.fetchall()]

def get_fund_history(fund_code, days=30):
    """获取基金历史数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            # 获取净值历史
            cursor.execute("""
                SELECT * FROM fund_nav 
                WHERE fund_code = %s AND nav_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY nav_date DESC
            """, (fund_code, days))
            nav_history = [dict(row) for row in cursor.fetchall()]
            
            # 获取评分历史
            cursor.execute("""
                SELECT * FROM fund_scores 
                WHERE fund_code = %s AND score_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY score_date DESC
            """, (fund_code, days))
            score_history = [dict(row) for row in cursor.fetchall()]
            
            return {
                'fund_info': get_fund_info(fund_code),
                'nav_history': nav_history,
                'score_history': score_history
            }

def save_fund_data(fund_code, fund_data):
    """保存完整的基金数据（兼容现有API格式）"""
    import json
    from datetime import date
    
    try:
        # 保存基本信息
        save_fund_info(
            fund_code=fund_code,
            fund_name=fund_data.get('fund_name', f'基金{fund_code}'),
            fund_type=fund_data.get('fund_type'),
            fund_company=fund_data.get('fund_company'),
            establish_date=fund_data.get('establish_date'),
            fund_size=fund_data.get('fund_size'),
            manager=fund_data.get('manager'),
            risk_level=fund_data.get('risk_level'),
            rating=fund_data.get('rating')
        )
        
        # 保存净值数据（如果存在）
        if 'net_value' in fund_data:
            save_fund_nav(
                fund_code=fund_code,
                nav_date=date.today(),
                net_value=fund_data.get('net_value'),
                accumulated_value=fund_data.get('accumulated_value'),
                daily_return=fund_data.get('daily_return'),
                weekly_return=fund_data.get('weekly_return'),
                monthly_return=fund_data.get('monthly_return'),
                quarterly_return=fund_data.get('quarterly_return'),
                yearly_return=fund_data.get('yearly_return')
            )
        
        # 保存评分数据（如果存在）
        score_100 = fund_data.get('score_100', {})
        if score_100:
            save_fund_score(
                fund_code=fund_code,
                score_date=date.today(),
                total_score=score_100.get('total_score'),
                valuation_score=score_100.get('valuation', {}).get('score'),
                sector_score=score_100.get('sector', {}).get('score'),
                risk_score=score_100.get('risk_control', {}).get('score'),
                valuation_reason=score_100.get('valuation', {}).get('reason'),
                sector_reason=score_100.get('sector', {}).get('reason'),
                risk_reason=score_100.get('risk_control', {}).get('reason')
            )
        
        return True
    except Exception as e:
        logger.error(f"保存基金数据失败: {fund_code}, {e}")
        return False

# 兼容性别名
def get_all_holdings():
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM holdings")
            return [dict(row) for row in cursor.fetchall()]

def save_holdings(user_id, holdings):
    for h in holdings:
        save_holding(
            user_id,
            h.get("code", ""),
            h.get("amount", 0),
            h.get("name") or "",
            h.get("buy_nav") or h.get("buyNav"),
            h.get("buy_date") or h.get("buyDate")
        )

if __name__ == "__main__":
    init_db()
    print("Database initialized!")
