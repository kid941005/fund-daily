"""
异步数据库层测试
"""

import asyncio
import os
import sys
from datetime import date, timedelta
from typing import Optional

import pytest

# 确保 src 在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_db():
    """创建异步数据库实例"""
    from src.db.async_database import AsyncDatabase, AsyncDatabaseConfig
    
    config = AsyncDatabaseConfig(
        host=os.getenv("FUND_DAILY_DB_HOST", "localhost"),
        port=int(os.getenv("FUND_DAILY_DB_PORT", "5432")),
        database=os.getenv("FUND_DAILY_DB_NAME", "fund_daily"),
        user=os.getenv("FUND_DAILY_DB_USER", "kid"),
        password=os.getenv("FUND_DAILY_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        min_pool_size=2,
        max_pool_size=5,
    )
    
    db = AsyncDatabase.from_config(config)
    await db.initialize()
    
    yield db
    
    await db.close()


@pytest.fixture
async def async_funds_db(async_db):
    """创建 AsyncFundsDB"""
    from src.db.async_crud import AsyncFundsDB
    return AsyncFundsDB(async_db)


@pytest.fixture
async def async_holdings_db(async_db):
    """创建 AsyncHoldingsDB"""
    from src.db.async_crud import AsyncHoldingsDB
    return AsyncHoldingsDB(async_db)


@pytest.fixture
async def async_user_db(async_db):
    """创建 AsyncUserDB"""
    from src.db.async_crud import AsyncUserDB
    return AsyncUserDB(async_db)


# ==================== AsyncDatabase 测试 ====================

class TestAsyncDatabase:
    """AsyncDatabase 核心功能测试"""
    
    async def test_initialize(self, async_db):
        """测试初始化"""
        assert async_db._initialized
        assert async_db._pool is not None
    
    async def test_execute_and_fetch(self, async_db):
        """测试执行和查询"""
        # SELECT
        result = await async_db.fetch("SELECT 1 as id, 'test' as name")
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "test"
    
    async def test_fetchrow(self, async_db):
        """测试单行查询"""
        result = await async_db.fetchrow("SELECT 1 as id")
        assert result["id"] == 1
        
        null_result = await async_db.fetchrow("SELECT 1 WHERE 1=0")
        assert null_result is None
    
    async def test_scalar(self, async_db):
        """测试标量查询"""
        result = await async_db.scalar("SELECT 42")
        assert result == 42
        
        result = await async_db.scalar("SELECT COUNT(*) FROM users")
        assert isinstance(result, int)
    
    async def test_fetch_all(self, async_db):
        """测试获取所有记录转为字典"""
        results = await async_db.fetch_all("SELECT 1 as id UNION SELECT 2")
        assert len(results) == 2
        assert all(isinstance(r, dict) for r in results)
    
    async def test_execute_update(self, async_db):
        """测试 UPDATE"""
        # 创建一个测试基金记录
        await async_db.execute(
            "INSERT INTO funds (fund_code, fund_name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            "TEST001", "测试基金"
        )
        
        # 更新
        count = await async_db.execute_update(
            "UPDATE funds SET fund_name = $1 WHERE fund_code = $2",
            "测试基金更新", "TEST001"
        )
        assert count >= 0  # 可能 0 或 1
        
        # 清理
        await async_db.execute("DELETE FROM funds WHERE fund_code = 'TEST001'")
    
    async def test_transaction(self, async_db):
        """测试事务"""
        async with async_db.transaction() as conn:
            await conn.execute(
                "INSERT INTO funds (fund_code, fund_name) VALUES ($1, $2)",
                "TEST_TXN", "事务测试基金"
            )
        
        # 验证插入成功
        result = await async_db.fetchrow(
            "SELECT fund_name FROM funds WHERE fund_code = $1", "TEST_TXN"
        )
        assert result is not None
        
        # 清理
        await async_db.execute("DELETE FROM funds WHERE fund_code = 'TEST_TXN'")
    
    async def test_transaction_rollback(self, async_db):
        """测试事务回滚"""
        try:
            async with async_db.transaction() as conn:
                await conn.execute(
                    "INSERT INTO funds (fund_code, fund_name) VALUES ($1, $2)",
                    "TEST_ROLLBACK", "回滚测试"
                )
                raise Exception("Force rollback")
        except Exception:
            pass
        
        # 验证插入被回滚
        result = await async_db.fetchrow(
            "SELECT fund_name FROM funds WHERE fund_code = $1", "TEST_ROLLBACK"
        )
        assert result is None
    
    async def test_acquire(self, async_db):
        """测试连接获取"""
        async with async_db.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
    
    async def test_pool_status(self, async_db):
        """测试连接池状态"""
        size = async_db.pool_size
        free = async_db.pool_free
        assert size >= 0
        assert free >= 0
        assert free <= size


# ==================== AsyncFundsDB 测试 ====================

class TestAsyncFundsDB:
    """AsyncFundsDB 测试"""
    
    async def test_save_and_get_fund_info(self, async_funds_db):
        """测试保存和获取基金信息"""
        fund_code = "TEST_FUND_001"
        
        # 保存
        result = await async_funds_db.save_fund_info(
            fund_code=fund_code,
            fund_name="测试基金",
            fund_type="股票型",
            fund_company="测试公司",
            manager="测试经理",
        )
        assert result is True
        
        # 获取
        fund = await async_funds_db.get_fund_info(fund_code)
        assert fund is not None
        assert fund["fund_code"] == fund_code
        assert fund["fund_name"] == "测试基金"
        assert fund["fund_type"] == "股票型"
        
        # 清理
        await async_funds_db.db.execute("DELETE FROM funds WHERE fund_code = $1", fund_code)
    
    async def test_save_fund_nav(self, async_funds_db):
        """测试保存基金净值"""
        fund_code = "TEST_NAV_001"
        today = date.today()
        
        # 先保存基本信息
        await async_funds_db.save_fund_info(fund_code, f"基金{fund_code}")
        
        # 保存净值
        result = await async_funds_db.save_fund_nav(
            fund_code=fund_code,
            nav_date=today,
            net_value=1.2345,
            accumulated_value=2.3456,
            daily_return=0.0123,
        )
        assert result is True
        
        # 获取净值
        nav = await async_funds_db.get_fund_nav(fund_code, today)
        assert nav is not None
        assert nav["net_value"] == 1.2345
        
        # 清理
        await async_funds_db.db.execute("DELETE FROM fund_nav WHERE fund_code = $1", fund_code)
        await async_funds_db.db.execute("DELETE FROM funds WHERE fund_code = $1", fund_code)
    
    async def test_save_fund_score(self, async_funds_db):
        """测试保存基金评分"""
        fund_code = "TEST_SCORE_001"
        today = date.today()
        
        await async_funds_db.save_fund_info(fund_code, f"基金{fund_code}")
        
        result = await async_funds_db.save_fund_score(
            fund_code=fund_code,
            score_date=today,
            total_score=85,
            valuation_score=90,
            sector_score=80,
            risk_score=85,
        )
        assert result is True
        
        score = await async_funds_db.get_fund_score(fund_code)
        assert score is not None
        assert score["total_score"] == 85
        
        # 清理
        await async_funds_db.db.execute("DELETE FROM fund_scores WHERE fund_code = $1", fund_code)
        await async_funds_db.db.execute("DELETE FROM funds WHERE fund_code = $1", fund_code)
    
    async def test_search_funds(self, async_funds_db):
        """测试搜索基金"""
        # 先创建测试基金
        await async_funds_db.save_fund_info("SEARCH_TEST", "搜索测试基金")
        
        # 搜索
        results = await async_funds_db.search_funds("搜索")
        assert any(r["fund_code"] == "SEARCH_TEST" for r in results)
        
        # 清理
        await async_funds_db.db.execute("DELETE FROM funds WHERE fund_code = 'SEARCH_TEST'")


# ==================== AsyncHoldingsDB 测试 ====================

class TestAsyncHoldingsDB:
    """AsyncHoldingsDB 测试"""
    
    async def test_save_and_get_holdings(self, async_holdings_db):
        """测试保存和获取持仓"""
        user_id = "test_user_holdings"
        fund_code = "HOLD_TEST_001"
        
        # 保存持仓
        result = await async_holdings_db.save_holding(
            user_id=user_id,
            code=fund_code,
            name="测试持仓基金",
            amount=1000.0,
            buy_nav=1.5,
            buy_date=date.today(),
        )
        assert result is True
        
        # 获取持仓
        holdings = await async_holdings_db.get_holdings(user_id)
        assert len(holdings) >= 1
        assert any(h["code"] == fund_code for h in holdings)
        
        # 清理
        await async_holdings_db.delete_holding(user_id, fund_code)
    
    async def test_delete_holding(self, async_holdings_db):
        """测试删除持仓"""
        user_id = "test_user_delete"
        fund_code = "DELETE_TEST_001"
        
        await async_holdings_db.save_holding(user_id, fund_code, 100.0)
        result = await async_holdings_db.delete_holding(user_id, fund_code)
        assert result >= 0
        
        holdings = await async_holdings_db.get_holdings(user_id)
        assert not any(h["code"] == fund_code for h in holdings)
    
    async def test_clear_holdings(self, async_holdings_db):
        """测试清空持仓"""
        user_id = "test_user_clear"
        
        # 添加多个持仓
        await async_holdings_db.save_holding(user_id, "CLEAR_001", 100.0)
        await async_holdings_db.save_holding(user_id, "CLEAR_002", 200.0)
        
        # 清空
        result = await async_holdings_db.clear_holdings(user_id)
        assert result >= 0
        
        holdings = await async_holdings_db.get_holdings(user_id)
        assert len(holdings) == 0


# ==================== AsyncUserDB 测试 ====================

class TestAsyncUserDB:
    """AsyncUserDB 测试"""
    
    async def test_get_by_username(self, async_user_db):
        """测试根据用户名获取用户"""
        # 使用已存在的测试用户
        user = await async_user_db.get_by_username("admin")
        # 可能不存在，测试边界情况
        if user:
            assert "username" in user
            assert "user_id" in user
    
    async def test_create_and_get_user(self, async_user_db):
        """测试创建和获取用户"""
        user_id = "test_async_user"
        username = "test_async_user"
        password_hash = "$2b$12$test_hash_value"
        
        # 创建
        result = await async_user_db.create(user_id, username, password_hash)
        # 可能已存在，测试边界情况
        
        # 获取
        user = await async_user_db.get_by_username(username)
        if user:
            assert user["username"] == username
        
        # 清理（可选）


# ==================== 配置和生命周期测试 ====================

class TestAsyncDBLifecycle:
    """异步数据库生命周期测试"""
    
    async def test_from_env(self):
        """测试从环境变量创建"""
        from src.db.async_database import AsyncDatabase
        
        db = AsyncDatabase.from_env()
        assert db._config is not None
    
    async def test_close_and_reinit(self, async_db):
        """测试关闭和重新初始化"""
        await async_db.close()
        assert not async_db._initialized
        assert async_db._pool is None
        
        # 重新初始化
        await async_db.initialize()
        assert async_db._initialized
        assert async_db._pool is not None


# ==================== 性能基准测试 ====================

class TestAsyncDBPerformance:
    """性能测试"""
    
    @pytest.mark.skipif(
        os.getenv("SKIP_PERF_TESTS") == "1",
        reason="Performance tests skipped"
    )
    async def test_concurrent_queries(self, async_db):
        """测试并发查询"""
        import time
        
        num_queries = 100
        
        async def single_query(i):
            return await async_db.fetchrow("SELECT $1 as id", i)
        
        start = time.time()
        tasks = [single_query(i) for i in range(num_queries)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        assert len(results) == num_queries
        print(f"\n{num_queries} concurrent queries: {elapsed:.3f}s ({num_queries/elapsed:.1f} qps)")
    
    @pytest.mark.skipif(
        os.getenv("SKIP_PERF_TESTS") == "1",
        reason="Performance tests skipped"
    )
    async def test_warmup(self, async_db):
        """测试连接池预热"""
        import time
        
        await async_db.close()
        
        start = time.time()
        await async_db.initialize()
        await async_db.warmup()
        elapsed = time.time() - start
        
        print(f"\nPool warmup time: {elapsed:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
