#!/usr/bin/env python3
"""
PostgreSQL Database Module for Fund Daily
直接使用 psycopg2，避免 SQLite 兼容性问题
"""

import logging
from contextlib import contextmanager

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from src.config import get_config

logger = logging.getLogger(__name__)

# PostgreSQL 配置 - 使用统一配置管理器
config = get_config()
DB_HOST = config.database.host
DB_PORT = config.database.port
DB_NAME = config.database.name
DB_USER = config.database.user
DB_PASSWORD = config.database.password

# 连接池
_connection_pool = None


def get_pool():
    """获取连接池"""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=2, maxconn=20, host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
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

            # 高频查询优化索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_funds_updated_at
                ON funds(updated_at DESC)
            """)

            # 启用 pg_trgm 扩展（用于 GIN 索引加速 LIKE 查询）
            cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_trgm
            """)

            # 基金名称全文搜索索引（支持 LIKE '%xxx%' 加速）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_funds_fund_name_trgm
                ON funds USING gin (fund_name gin_trgm_ops)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_funds_fund_code_trgm
                ON funds USING gin (fund_code gin_trgm_ops)
            """)

            # fund_nav / fund_scores 按基金和时间范围快速查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fund_nav_code_date
                ON fund_nav(fund_code, nav_date DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fund_scores_code_date
                ON fund_scores(fund_code, score_date DESC)
            """)

            conn.commit()
            logger.info("Database tables initialized")
