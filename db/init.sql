-- Fund Daily 数据库初始化脚本
-- 在 PostgreSQL 容器启动时自动执行
-- 注意: 使用与 db/pool.py 一致的 schema

-- 创建扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建用户表 (与 db/pool.py 一致)
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建持仓表 (与 db/pool.py 一致)
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
);

-- 创建基金基本信息表 (与 db/pool.py 一致)
CREATE TABLE IF NOT EXISTS funds (
    id SERIAL PRIMARY KEY,
    fund_code VARCHAR(20) UNIQUE NOT NULL,
    fund_name VARCHAR(200) NOT NULL,
    full_name VARCHAR(200),
    fund_type VARCHAR(50),
    fund_company VARCHAR(100),
    manager VARCHAR(100),
    established_date DATE,
    net_assets DECIMAL(20,2),
    risk_level VARCHAR(20),
    rating VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 创建基金净值表 (与 db/pool.py 一致)
CREATE TABLE IF NOT EXISTS fund_nav (
    id SERIAL PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL,
    nav_date DATE NOT NULL,
    nav_value DECIMAL(10,4) NOT NULL,
    change_rate DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, nav_date)
);

-- 创建基金评分表 (与 db/pool.py 一致)
CREATE TABLE IF NOT EXISTS fund_scores (
    id SERIAL PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL,
    score_date DATE NOT NULL,
    total_score DECIMAL(5,2) NOT NULL,
    valuation_score DECIMAL(5,2),
    performance_score DECIMAL(5,2),
    risk_score DECIMAL(5,2),
    momentum_score DECIMAL(5,2),
    sentiment_score DECIMAL(5,2),
    sector_score DECIMAL(5,2),
    manager_score DECIMAL(5,2),
    liquidity_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, score_date)
);

-- 创建配置表 (与 db/pool.py 一致)
CREATE TABLE IF NOT EXISTS config (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, config_key)
);

-- 创建监控列表表 (与 db/pool.py 一致)
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    fund_code VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, fund_code)
);

-- 创建历史记录表 (与 db/pool.py 一致)
CREATE TABLE IF NOT EXISTS history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建 updated_at 更新函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要 updated_at 的表创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_funds_updated_at BEFORE UPDATE ON funds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_holdings_updated_at BEFORE UPDATE ON holdings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_config_updated_at BEFORE UPDATE ON config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入默认管理员用户 (密码: admin123)
-- 使用 PBKDF2-HMAC-SHA256 哈希 (salt$hash 格式)
INSERT INTO users (user_id, username, password, created_at) 
VALUES 
    ('admin_default_id_001', 'admin', '370cab64d190f4be34627af172e5ef53$cb71ddfe90195a537e46c5c32f6a2dea44ab8402d9e81ed145828210a9dcd6e5', CURRENT_TIMESTAMP)
ON CONFLICT (username) DO NOTHING;

-- 插入示例基金数据
INSERT INTO funds (fund_code, fund_name, full_name, fund_type, manager) 
VALUES 
    ('000001', '华夏成长', '华夏成长混合型证券投资基金', '混合型', '华夏基金'),
    ('000002', '嘉实增长', '嘉实增长混合型证券投资基金', '混合型', '嘉实基金'),
    ('000003', '易方达消费', '易方达消费行业股票型证券投资基金', '股票型', '易方达基金')
ON CONFLICT (fund_code) DO NOTHING;

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_code ON holdings(code);
CREATE INDEX IF NOT EXISTS idx_fund_nav_fund_code ON fund_nav(fund_code);
CREATE INDEX IF NOT EXISTS idx_fund_nav_nav_date ON fund_nav(nav_date DESC);
CREATE INDEX IF NOT EXISTS idx_fund_scores_fund_code ON fund_scores(fund_code);
CREATE INDEX IF NOT EXISTS idx_fund_scores_score_date ON fund_scores(score_date DESC);
CREATE INDEX IF NOT EXISTS idx_config_user_id ON config(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_history_user_id ON history(user_id);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at DESC);

-- 创建只读用户（可选，用于监控）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'fund_daily_reader') THEN
        CREATE ROLE fund_daily_reader WITH LOGIN PASSWORD 'reader_password_123';
    END IF;
END
$$;

-- 授予只读权限
GRANT CONNECT ON DATABASE fund_daily TO fund_daily_reader;
GRANT USAGE ON SCHEMA public TO fund_daily_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fund_daily_reader;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO fund_daily_reader;

-- 设置默认搜索路径
ALTER DATABASE fund_daily SET search_path TO public;

-- 完成消息
DO $$
BEGIN
    RAISE NOTICE 'Fund Daily 数据库初始化完成';
END $$;