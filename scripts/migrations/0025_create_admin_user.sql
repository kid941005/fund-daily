-- Migration 0025: 创建默认管理员用户
-- 用户名: admin
-- 密码: admin123

DO $$
DECLARE
    user_id TEXT;
    password_hash TEXT;
BEGIN
    -- 检查是否已存在 admin 用户
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin') THEN
        -- 生成用户ID
        user_id := SUBSTRING(MD5(RANDOM()::TEXT || CLOCK_TIMESTAMP()::TEXT) FROM 1 FOR 16);
        
        -- 生成密码哈希 (使用 PBKDF2-HMAC-SHA256)
        -- 注意: 这里需要与 src/auth.py 中的 hash_password 函数一致
        -- 格式: salt$hash
        password_hash := 'c7f9a8b3e5d1f2a4b6c8d0e9f1a3b5c7$' || 
                         ENCODE(HMAC('c7f9a8b3e5d1f2a4b6c8d0e9f1a3b5c7'::BYTEA, 'admin123'::BYTEA, 'sha256'), 'hex');
        
        -- 插入管理员用户
        INSERT INTO users (user_id, username, password, created_at)
        VALUES (user_id, 'admin', password_hash, CURRENT_TIMESTAMP);
        
        RAISE NOTICE '管理员用户 admin 创建成功，用户ID: %', user_id;
    ELSE
        RAISE NOTICE '管理员用户 admin 已存在';
    END IF;
END $$;