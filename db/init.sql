-- Fund Daily 数据库初始化脚本
-- 在 PostgreSQL 容器启动时自动执行

-- 创建扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}'::jsonb
);

-- 创建基金表
CREATE TABLE IF NOT EXISTS funds (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200),
    fund_type VARCHAR(50),
    manager VARCHAR(100),
    established_date DATE,
    net_assets DECIMAL(20,2),
    risk_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 创建持仓表
CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    fund_code VARCHAR(10) NOT NULL,
    amount DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    cost_basis DECIMAL(15,4) DEFAULT 0.0000,
    purchase_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(user_id, fund_code)
);

-- 创建监控列表表
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    fund_code VARCHAR(10) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(user_id, fund_code)
);

-- 创建基金历史数据表
CREATE TABLE IF NOT EXISTS fund_history (
    id SERIAL PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    net_value DECIMAL(8,4) NOT NULL,
    accumulated_value DECIMAL(8,4),
    daily_growth_rate DECIMAL(6,4),
    week_growth_rate DECIMAL(6,4),
    month_growth_rate DECIMAL(6,4),
    three_month_growth_rate DECIMAL(6,4),
    six_month_growth_rate DECIMAL(6,4),
    year_growth_rate DECIMAL(6,4),
    year_to_date_growth_rate DECIMAL(6,4),
    two_year_growth_rate DECIMAL(6,4),
    three_year_growth_rate DECIMAL(6,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, date)
);

-- 创建用户会话表（用于JWT黑名单）
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_id VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);

-- 创建API请求日志表
CREATE TABLE IF NOT EXISTS api_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time INTEGER,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_funds_code ON funds(code);
CREATE INDEX IF NOT EXISTS idx_funds_name ON funds(name);
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_fund_code ON holdings(fund_code);
CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_fund_history_fund_code ON fund_history(fund_code);
CREATE INDEX IF NOT EXISTS idx_fund_history_date ON fund_history(date);
CREATE INDEX IF NOT EXISTS idx_fund_history_fund_code_date ON fund_history(fund_code, date);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_id ON user_sessions(token_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON api_logs(created_at);

-- 创建函数和触发器
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

-- 插入默认数据（可选）
INSERT INTO users (username, email, password_hash, is_active) 
VALUES 
    ('admin', 'admin@fund-daily.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true),
    ('testuser', 'test@fund-daily.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true)
ON CONFLICT (username) DO NOTHING;

-- 插入示例基金数据
INSERT INTO funds (code, name, full_name, fund_type, manager) 
VALUES 
    ('000001', '华夏成长', '华夏成长混合型证券投资基金', '混合型', '华夏基金'),
    ('000002', '嘉实增长', '嘉实增长混合型证券投资基金', '混合型', '嘉实基金'),
    ('000003', '易方达消费', '易方达消费行业股票型证券投资基金', '股票型', '易方达基金')
ON CONFLICT (code) DO NOTHING;

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

-- 记录初始化完成
COMMENT ON DATABASE fund_daily IS 'Fund Daily v2.6.0 数据库 - 初始化完成于 ' || CURRENT_TIMESTAMP;