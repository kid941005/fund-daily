"""
速率限制器测试
"""

import time
import threading
import pytest
from src.utils.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试速率限制器"""
    
    def test_basic_rate_limiting(self):
        """测试基本速率限制"""
        limiter = RateLimiter(default_limit=2, default_window=1)  # 1秒内最多2次
        
        key = "test_key"
        
        # 第一次请求应该允许
        assert limiter.is_allowed(key) is True
        
        # 第二次请求应该允许
        assert limiter.is_allowed(key) is True
        
        # 第三次请求应该被限制
        assert limiter.is_allowed(key) is False
        
        # 等待1秒后应该允许
        time.sleep(1.1)
        assert limiter.is_allowed(key) is True
    
    def test_different_keys(self):
        """测试不同键的独立限制"""
        limiter = RateLimiter(default_limit=1, default_window=1)
        
        key1 = "key1"
        key2 = "key2"
        
        # key1 第一次请求允许
        assert limiter.is_allowed(key1) is True
        # key1 第二次请求限制
        assert limiter.is_allowed(key1) is False
        
        # key2 应该允许（独立计数）
        assert limiter.is_allowed(key2) is True
        # key2 第二次请求限制
        assert limiter.is_allowed(key2) is False
    
    def test_custom_limit_and_window(self):
        """测试自定义限制和窗口"""
        limiter = RateLimiter(default_limit=10, default_window=60)
        
        key = "test_key"
        
        # 使用自定义限制：2次/1秒
        assert limiter.is_allowed(key, limit=2, window=1) is True
        assert limiter.is_allowed(key, limit=2, window=1) is True
        assert limiter.is_allowed(key, limit=2, window=1) is False
        
        # 使用默认限制应该允许（10次/60秒）
        assert limiter.is_allowed(key) is True
    
    def test_get_remaining(self):
        """测试获取剩余请求次数"""
        limiter = RateLimiter(default_limit=3, default_window=1)
        
        key = "test_key"
        
        # 初始剩余3次
        assert limiter.get_remaining(key) == 3
        
        # 使用1次
        limiter.is_allowed(key)
        assert limiter.get_remaining(key) == 2
        
        # 使用2次
        limiter.is_allowed(key)
        assert limiter.get_remaining(key) == 1
        
        # 使用3次
        limiter.is_allowed(key)
        assert limiter.get_remaining(key) == 0
        
        # 超过限制
        limiter.is_allowed(key)
        assert limiter.get_remaining(key) == 0
        
        # 等待后重置
        time.sleep(1.1)
        assert limiter.get_remaining(key) == 3
    
    def test_get_reset_time(self):
        """测试获取重置时间"""
        limiter = RateLimiter(default_limit=1, default_window=2)
        
        key = "test_key"
        start_time = time.time()
        
        # 第一次请求
        limiter.is_allowed(key)
        reset_time = limiter.get_reset_time(key)
        
        # 重置时间应该在开始时间后2秒左右
        assert abs(reset_time - (start_time + 2)) < 0.1
    
    def test_clear(self):
        """测试清除限制"""
        limiter = RateLimiter(default_limit=1, default_window=10)
        
        key = "test_key"
        
        # 使用1次
        assert limiter.is_allowed(key) is True
        assert limiter.is_allowed(key) is False  # 限制
        
        # 清除限制
        limiter.clear(key)
        assert limiter.is_allowed(key) is True  # 应该允许
        
        # 测试清除所有
        key2 = "key2"
        limiter.is_allowed(key2)
        limiter.clear()  # 清除所有
        assert limiter.is_allowed(key2) is True
    
    def test_thread_safety(self):
        """测试线程安全"""
        limiter = RateLimiter(default_limit=100, default_window=1)
        key = "test_key"
        
        results = []
        
        def make_requests():
            for _ in range(20):
                allowed = limiter.is_allowed(key)
                results.append(allowed)
        
        # 创建多个线程同时访问
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_requests)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 总共100次限制，应该正好有100次允许
        allowed_count = sum(1 for r in results if r)
        assert allowed_count == 100, f"应该允许100次，实际允许{allowed_count}次"
    
    def test_get_stats(self):
        """测试获取统计信息"""
        limiter = RateLimiter(default_limit=10, default_window=60)
        
        key = "test_key"
        
        # 添加一些请求
        limiter.is_allowed(key)
        limiter.is_allowed(key)
        limiter.is_allowed(key)
        
        stats = limiter.get_stats(key)
        
        assert stats["total_requests"] == 3
        assert stats["last_request"] is not None
        assert stats["recent_1m"] <= 3
        assert stats["recent_5m"] <= 3
        assert stats["recent_1h"] <= 3


def test_wait_if_needed():
    """测试wait_if_needed函数"""
    # 这个测试需要模拟配置，暂时跳过
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])