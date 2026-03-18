-- Fund Daily 数据库索引优化脚本
-- 执行此脚本以添加必要的索引，提升查询性能

-- 1. holdings 表索引
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_user_code ON holdings(user_id, code);
CREATE INDEX IF NOT EXISTS idx_holdings_code ON holdings(code);

-- 2. fund_nav 表索引
CREATE INDEX IF NOT EXISTS idx_fund_nav_fund_code ON fund_nav(fund_code);
CREATE INDEX IF NOT EXISTS idx_fund_nav_nav_date ON fund_nav(nav_date);
CREATE INDEX IF NOT EXISTS idx_fund_nav_code_date ON fund_nav(fund_code, nav_date DESC);

-- 3. fund_scores 表索引
CREATE INDEX IF NOT EXISTS idx_fund_scores_fund_code ON fund_scores(fund_code);
CREATE INDEX IF NOT EXISTS idx_fund_scores_score_date ON fund_scores(score_date);
CREATE INDEX IF NOT EXISTS idx_fund_scores_code_date ON fund_scores(fund_code, score_date DESC);
CREATE INDEX IF NOT EXISTS idx_fund_scores_total_score ON fund_scores(total_score DESC);

-- 4. funds 表索引
CREATE INDEX IF NOT EXISTS idx_funds_fund_code ON funds(fund_code);
CREATE INDEX IF NOT EXISTS idx_funds_fund_name ON funds(fund_name);
CREATE INDEX IF NOT EXISTS idx_funds_fund_type ON funds(fund_type);

-- 5. users 表索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- 6. watchlist 表索引
CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user_code ON watchlist(user_id, code);

-- 查看索引创建结果
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;