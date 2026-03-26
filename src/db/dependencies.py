"""
FastAPI 依赖注入模块
提供异步数据库依赖和会话管理
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .async_database import (
    AsyncDatabase,
    AsyncDatabaseConfig,
    get_async_db,
    close_async_db,
)
from .async_crud import (
    AsyncUserDB,
    AsyncHoldingsDB,
    AsyncWatchlistDB,
    AsyncConfigDB,
    AsyncFundsDB,
)
from .repositories import (
    UserRepository,
    HoldingsRepository,
    FundsRepository,
    FundNavRepository,
    FundScoreRepository,
    ConfigRepository,
    WatchlistRepository,
    HistoryRepository,
)

logger = logging.getLogger(__name__)


# ==================== 全局数据库实例管理 ====================

_async_db_instance: Optional[AsyncDatabase] = None


async def get_global_async_db() -> AsyncDatabase:
    """获取全局异步数据库实例"""
    global _async_db_instance
    if _async_db_instance is None:
        _async_db_instance = await get_async_db()
    return _async_db_instance


async def init_async_dependencies() -> AsyncDatabase:
    """初始化异步依赖（在应用启动时调用）"""
    global _async_db_instance
    _async_db_instance = await get_async_db()
    await _async_db_instance.warmup()
    logger.info("Async database dependencies initialized")
    return _async_db_instance


async def close_async_dependencies() -> None:
    """关闭异步依赖（在应用关闭时调用）"""
    global _async_db_instance
    if _async_db_instance is not None:
        await _async_db_instance.close()
        _async_db_instance = None
        logger.info("Async database dependencies closed")


# ==================== FastAPI 依赖 ====================


async def get_async_database() -> AsyncDatabase:
    """
    FastAPI 依赖：获取异步数据库实例

    用法:
        @app.get("/users")
        async def get_users(db: AsyncDatabase = Depends(get_async_database)):
            users = await db.fetch_all("SELECT * FROM users")
            return users
    """
    return await get_global_async_db()


async def get_async_db_connection():
    """
    FastAPI 依赖：获取异步数据库连接（with transaction）

    用法:
        @app.post("/users")
        async def create_user(conn = Depends(get_async_db_connection)):
            async with conn.transaction():
                await conn.execute("INSERT INTO users ...")
    """
    db = await get_global_async_db()
    async with db.acquire() as conn:
        yield conn


# ==================== CRUD 依赖 ====================


async def get_async_user_db(
    db: AsyncDatabase = Depends(get_async_database),
) -> AsyncUserDB:
    """FastAPI 依赖：获取异步用户 DB"""
    return AsyncUserDB(db)


async def get_async_holdings_db(
    db: AsyncDatabase = Depends(get_async_database),
) -> AsyncHoldingsDB:
    """FastAPI 依赖：获取异步持仓 DB"""
    return AsyncHoldingsDB(db)


async def get_async_watchlist_db(
    db: AsyncDatabase = Depends(get_async_database),
) -> AsyncWatchlistDB:
    """FastAPI 依赖：获取异步监控列表 DB"""
    return AsyncWatchlistDB(db)


async def get_async_config_db(
    db: AsyncDatabase = Depends(get_async_database),
) -> AsyncConfigDB:
    """FastAPI 依赖：获取异步配置 DB"""
    return AsyncConfigDB(db)


async def get_async_funds_db(
    db: AsyncDatabase = Depends(get_async_database),
) -> AsyncFundsDB:
    """FastAPI 依赖：获取异步基金 DB"""
    return AsyncFundsDB(db)


# ==================== Repository 依赖 ====================


async def get_user_repository(
    db: AsyncDatabase = Depends(get_async_database),
) -> UserRepository:
    """FastAPI 依赖：获取用户 Repository"""
    # Repository 需要 AsyncSession，这里暂时用简化的方式
    # 如需完整 ORM 支持，请使用 SQLAlchemy async session
    from sqlalchemy.ext.asyncio import AsyncSession

    async with db.acquire() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield UserRepository(session)


# ==================== 生命周期管理 ====================


@asynccontextmanager
async def lifespan_async_db(
    config: Optional[AsyncDatabaseConfig] = None,
) -> AsyncIterator[AsyncDatabase]:
    """
    异步数据库上下文管理器（用于 lifespan）

    用法:
        async with lifespan_async_db() as db:
            await db.execute("INSERT ...")
    """
    global _async_db_instance

    if config:
        _async_db_instance = AsyncDatabase.from_config(config)
    else:
        _async_db_instance = await get_async_db()

    await _async_db_instance.initialize()
    await _async_db_instance.warmup()

    try:
        yield _async_db_instance
    finally:
        await _async_db_instance.close()
        _async_db_instance = None


# ==================== 请求级数据库会话 ====================


class AsyncDatabaseSession:
    """
    请求级数据库会话
    自动管理连接获取和释放
    """

    def __init__(self, db: Optional[AsyncDatabase] = None):
        self._db = db
        self._conn = None

    async def __aenter__(self) -> "AsyncDatabaseSession":
        if self._db is None:
            self._db = await get_global_async_db()
        self._conn = await self._db._pool.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn and self._db and self._db._pool:
            await self._db._pool.release(self._conn)
        self._conn = None

    @property
    def conn(self):
        """获取连接"""
        return self._conn


async def get_db_session() -> AsyncIterator[AsyncDatabaseSession]:
    """
    FastAPI 依赖：获取请求级数据库会话

    用法:
        @app.get("/users")
        async def get_users(session: AsyncDatabaseSession = Depends(get_db_session)):
            async with session:
                result = await session.conn.fetch("SELECT * FROM users")
    """
    session = AsyncDatabaseSession()
    await session.__aenter__()
    try:
        yield session
    finally:
        await session.__aexit__(None, None, None)


# ==================== 中间件/背景任务 ====================


class AsyncDatabaseMiddleware:
    """
    异步数据库中间件（用于需要全局数据库访问的场景）
    """

    def __init__(self, app, config: Optional[AsyncDatabaseConfig] = None):
        self.app = app
        self.config = config

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            startup = scope.get("state", {}).get("startup", False)

            async def receive_and_wait():
                message = await receive()
                if message["type"] == "lifespan.startup.complete":
                    scope["state"]["startup"] = True
                elif message["type"] == "lifespan.shutdown.complete":
                    scope["state"]["shutdown"] = True
                return message

            scope["receive"] = receive_and_wait

            # Initialize on startup
            await init_async_dependencies()

            # Wait for shutdown signal
            message = await receive()
            while message["type"] not in ("lifespan.shutdown.complete", "lifespan.startup.failure"):
                message = await receive()

            # Cleanup on shutdown
            await close_async_dependencies()

        await self.app(scope, receive, send)


__all__ = [
    # 数据库实例
    "AsyncDatabase",
    "AsyncDatabaseConfig",
    "get_async_database",
    "get_async_db_connection",
    "get_global_async_db",
    "init_async_dependencies",
    "close_async_dependencies",
    "lifespan_async_db",
    # CRUD
    "AsyncUserDB",
    "AsyncHoldingsDB",
    "AsyncWatchlistDB",
    "AsyncConfigDB",
    "AsyncFundsDB",
    "get_async_user_db",
    "get_async_holdings_db",
    "get_async_watchlist_db",
    "get_async_config_db",
    "get_async_funds_db",
    # Repository
    "UserRepository",
    "HoldingsRepository",
    "FundsRepository",
    "FundNavRepository",
    "FundScoreRepository",
    "ConfigRepository",
    "WatchlistRepository",
    "HistoryRepository",
    "get_user_repository",
    # 会话
    "AsyncDatabaseSession",
    "get_db_session",
    # 中间件
    "AsyncDatabaseMiddleware",
]
