-- Migration: 001_extend_fund_scores
-- Description: 为评分系统添加完整的审计追踪字段
-- Date: 2026-04-05

-- 1. 添加缺失的维度 reason 字段（当前只有 3 个，需要 8 个）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'valuation_reason') THEN
        ALTER TABLE fund_scores ADD COLUMN valuation_reason TEXT;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'performance_reason') THEN
        ALTER TABLE fund_scores ADD COLUMN performance_reason TEXT;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'momentum_reason') THEN
        ALTER TABLE fund_scores ADD COLUMN momentum_reason TEXT;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'sentiment_reason') THEN
        ALTER TABLE fund_scores ADD COLUMN sentiment_reason TEXT;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'manager_reason') THEN
        ALTER TABLE fund_scores ADD COLUMN manager_reason TEXT;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'liquidity_reason') THEN
        ALTER TABLE fund_scores ADD COLUMN liquidity_reason TEXT;
    END IF;
END$$;

-- 2. 添加审计字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'data_source') THEN
        ALTER TABLE fund_scores ADD COLUMN data_source VARCHAR(50);
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'data_fetched_at') THEN
        ALTER TABLE fund_scores ADD COLUMN data_fetched_at TIMESTAMP;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'calculation_version') THEN
        ALTER TABLE fund_scores ADD COLUMN calculation_version VARCHAR(20);
    END IF;
END$$;

-- 3. 添加各维度的原始输入快照（JSONB 格式，可选）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'dimension_inputs') THEN
        ALTER TABLE fund_scores ADD COLUMN dimension_inputs JSONB;
    END IF;
END$$;

-- 4. 添加备注字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_scores' AND column_name = 'notes') THEN
        ALTER TABLE fund_scores ADD COLUMN notes TEXT;
    END IF;
END$$;

-- 5. 创建索引
CREATE INDEX IF NOT EXISTS idx_fund_scores_data_source ON fund_scores(data_source);
CREATE INDEX IF NOT EXISTS idx_fund_scores_data_fetched_at ON fund_scores(data_fetched_at DESC);

-- 6. 添加注释
COMMENT ON COLUMN fund_scores.valuation_reason IS '估值面评分原因';
COMMENT ON COLUMN fund_scores.performance_reason IS '业绩表现评分原因';
COMMENT ON COLUMN fund_scores.momentum_reason IS '动量趋势评分原因';
COMMENT ON COLUMN fund_scores.sentiment_reason IS '市场情绪评分原因';
COMMENT ON COLUMN fund_scores.manager_reason IS '基金经理评分原因';
COMMENT ON COLUMN fund_scores.liquidity_reason IS '流动性评分原因';
COMMENT ON COLUMN fund_scores.data_source IS '数据来源: api/cache/db';
COMMENT ON COLUMN fund_scores.data_fetched_at IS '数据抓取时间';
COMMENT ON COLUMN fund_scores.calculation_version IS '评分算法版本号';
COMMENT ON COLUMN fund_scores.dimension_inputs IS '各维度原始输入数据快照';

RAISE NOTICE 'Migration 001_extend_fund_scores completed successfully';
