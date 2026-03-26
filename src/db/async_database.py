"""
AsyncDatabase - 异步 PostgreSQL 数据库模块
使用 asyncpg + SQLAlchemy[asyncio] 实现高性能异步数据库操作
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import asyncpg
from asyncpg import Connection, Pool, Record

logger = logging.getLogger(__name__)


@dataclass
class AsyncDatabaseConfig:
    """异步数据库配置"""

    host: str = "localhost"
    port: int = 5432
    database: str = "fund_daily"
    user: str = "kid"
    password: str = ""
    min_pool_size: int = 5
    max_pool_size: int = 20
    command_timeout: float = 60.0
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0
    connect_timeout: float = 10.0
    retry_times: int = 3
    retry_delay: float = 0.5


class AsyncDatabase:
    """
    异步数据库管理器
    封装 asyncpg 连接池，提供简洁的异步数据库操作接口
    """

    _instance: Optional["AsyncDatabase"] = None
    _pool: Optional[Pool] = None
    _config: AsyncDatabaseConfig
    _initialized: bool = False
    _lock: asyncio.Lock

    def __new__(cls, config: Optional[AsyncDatabaseConfig] = None) -> "AsyncDatabase":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    def __init__(self, config: Optional[AsyncDatabaseConfig] = None):
        if config is not None:
            self._config = config
        elif not hasattr(self, "_config"):
            self._config = AsyncDatabaseConfig()

    @classmethod
    def from_config(cls, config: AsyncDatabaseConfig) -> "AsyncDatabase":
        """从配置创建实例"""
        instance = cls(config)
        return instance

    @classmethod
    def from_env(cls) -> "AsyncDatabase":
        """从环境变量创建实例"""
        import os

        config = AsyncDatabaseConfig(
            host=os.getenv("FUND_DAILY_DB_HOST", "localhost"),
            port=int(os.getenv("FUND_DAILY_DB_PORT", "5432")),
            database=os.getenv("FUND_DAILY_DB_NAME", "fund_daily"),
            user=os.getenv("FUND_DAILY_DB_USER", "kid"),
            password=os.getenv("FUND_DAILY_DB_PASSWORD", ""),
            min_pool_size=int(os.getenv("ASYNC_POOL_MIN", "5")),
            max_pool_size=int(os.getenv("ASYNC_POOL_MAX", "20")),
        )
        return cls.from_config(config)

    async def initialize(self) -> None:
        """初始化连接池"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                self._pool = await asyncpg.create_pool(
                    host=self._config.host,
                    port=self._config.port,
                    database=self._config.database,
                    user=self._config.user,
                    password=self._config.password,
                    min_size=self._config.min_pool_size,
                    max_size=self._config.max_pool_size,
                    command_timeout=self._config.command_timeout,
                    max_queries=self._config.max_queries,
                    max_inactive_connection_lifetime=self._config.max_inactive_connection_lifetime,
                    connect_timeout=self._config.connect_timeout,
                )
                self._initialized = True
                logger.info(
                    f"AsyncDB pool initialized: {self._config.host}:{self._config.port}/"
                    f"{self._config.database} (size: {self._config.min_pool_size}-{self._config.max_pool_size})"
                )
            except Exception as e:
                logger.error(f"Failed to initialize async pool: {e}")
                raise

    async def warmup(self) -> None:
        """连接池预热 - 预先建立 min_pool_size 个连接"""
        if not self._initialized or self._pool is None:
            await self.initialize()

        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            logger.info("AsyncDB pool warmed up")
        except Exception as e:
            logger.warning(f"Pool warmup failed: {e}")

    async def close(self) -> None:
        """关闭连接池"""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info("AsyncDB pool closed")

    async def get_pool(self) -> Pool:
        """获取连接池"""
        if not self._initialized or self._pool is None:
            await self.initialize()
        return self._pool

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Connection]:
        """获取数据库连接（上下文管理器）"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Connection]:
        """事务上下文管理器"""
        async with self.acquire() as conn:
            async with conn.transaction():
                yield conn

    # ==================== 核心查询方法 ====================

    async def _retry_on_failure(self, coro):
        """失败重试装饰器"""
        last_error = None
        for attempt in range(self._config.retry_times):
            try:
                return await coro()
            except (asyncpg.PostgresConnectionError, asyncpg.PostgresNetworkError) as e:
                last_error = e
                if attempt < self._config.retry_times - 1:
                    await asyncio.sleep(self._config.retry_delay * (attempt + 1))
                    logger.warning(f"Retry {attempt + 1}/{self._config.retry_times} after connection error")
            except Exception:
                raise
        raise last_error

    async def execute(self, query: str, *args, timeout: Optional[float] = None) -> str:
        """
        执行 SQL 并返回命令标签 (如 INSERT 0 1)

        Args:
            query: SQL 语句
            *args: 查询参数
            timeout: 超时时间(秒)

        Returns:
            执行结果字符串
        """

        async def _do():
            async with self.acquire() as conn:
                return await conn.execute(query, *args, timeout=timeout)

        if self._config.retry_times > 0:
            return await self._retry_on_failure(_do)
        return await _do()

    async def fetch(self, query: str, *args, timeout: Optional[float] = None) -> List[Record]:
        """
        执行 SELECT 查询并返回所有结果

        Args:
            query: SQL 语句
            *args: 查询参数
            timeout: 超时时间(秒)

        Returns:
            记录列表
        """

        async def _do():
            async with self.acquire() as conn:
                return await conn.fetch(query, *args, timeout=timeout)

        if self._config.retry_times > 0:
            return await self._retry_on_failure(_do)
        return await _do()

    async def fetchrow(self, query: str, *args, timeout: Optional[float] = None) -> Optional[Record]:
        """
        执行 SELECT 查询并返回单条结果

        Args:
            query: SQL 语句
            *args: 查询参数
            timeout: 超时时间(秒)

        Returns:
            单条记录或 None
        """

        async def _do():
            async with self.acquire() as conn:
                return await conn.fetchrow(query, *args, timeout=timeout)

        if self._config.retry_times > 0:
            return await self._retry_on_failure(_do)
        return await _do()

    async def scalar(self, query: str, *args, timeout: Optional[float] = None) -> Any:
        """
        执行查询并返回第一个字段的值

        Args:
            query: SQL 语句
            *args: 查询参数
            timeout: 超时时间(秒)

        Returns:
            第一个字段的值
        """

        async def _do():
            async with self.acquire() as conn:
                return await conn.fetchval(query, *args, timeout=timeout)

        if self._config.retry_times > 0:
            return await self._retry_on_failure(_do)
        return await _do()

    async def executemany(self, command: str, args_list: List[tuple]) -> None:
        """
        批量执行相同的 SQL 语句

        Args:
            command: SQL 语句模板
            args_list: 参数列表
        """

        async def _do():
            async with self.acquire() as conn:
                await conn.executemany(command, args_list)

        if self._config.retry_times > 0:
            await self._retry_on_failure(_do)
        else:
            await _do()

    # ==================== 便捷方法 ====================

    async def fetch_all(self, query: str, *args, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """获取所有记录并转为字典列表"""
        records = await self.fetch(query, *args, timeout=timeout)
        return [dict(r) for r in records]

    async def fetch_one(self, query: str, *args, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """获取单条记录并转为字典"""
        record = await self.fetchrow(query, *args, timeout=timeout)
        return dict(record) if record else None

    async def execute_insert(self, query: str, *args, timeout: Optional[float] = None) -> int:
        """执行 INSERT 并返回 last insert id"""
        async with self.acquire() as conn:
            rows = await conn.fetch(query, *args, timeout=timeout)
            if rows and "id" in rows[0]:
                return rows[0]["id"]
            # 尝试获取 lastval
            return await conn.fetchval("SELECT lastval()", timeout=timeout)

    async def execute_update(self, query: str, *args, timeout: Optional[float] = None) -> int:
        """执行 UPDATE/DELETE 并返回影响行数"""
        result = await self.execute(query, *args, timeout=timeout)
        # asyncpg 返回格式: "UPDATE/DELETE n"
        if " " in result:
            try:
                return int(result.split()[-1])
            except ValueError:
                return 0
        return 0

    # ==================== 事务支持 ====================

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[Connection]:
        """开始事务（兼容别名）"""
        async with self.transaction() as conn:
            yield conn

    async def commit(self) -> None:
        """提交事务（保留接口，实际由上下文管理器处理）"""
        pass

    async def rollback(self) -> None:
        """回滚事务（保留接口，实际由上下文管理器处理）"""
        pass

    # ==================== 连接池状态 ====================

    @property
    def pool_size(self) -> int:
        """当前连接池大小"""
        return len(self._pool.get_idle_connections()) if self._pool else 0

    @property
    def pool_free(self) -> int:
        """空闲连接数"""
        return len(self._pool.get_idle_connections()) if self._pool else 0


# 全局实例
_db_instance: Optional[AsyncDatabase] = None


async def get_async_db(config: Optional[AsyncDatabaseConfig] = None) -> AsyncDatabase:
    """获取全局异步数据库实例"""
    global _db_instance
    if _db_instance is None:
        if config is not None:
            _db_instance = AsyncDatabase.from_config(config)
        else:
            _db_instance = AsyncDatabase.from_env()
        await _db_instance.initialize()
    return _db_instance


async def close_async_db() -> None:
    """关闭全局异步数据库实例"""
    global _db_instance
    if _db_instance is not None:
        await _db_instance.close()
        _db_instance = None


# 便捷函数
async def init_async_db() -> AsyncDatabase:
    """初始化异步数据库（便捷函数）"""
    db = await get_async_db()
    await db.warmup()
    return db


__all__ = [
    "AsyncDatabase",
    "AsyncDatabaseConfig",
    "get_async_db",
    "close_async_db",
    "init_async_db",
]
