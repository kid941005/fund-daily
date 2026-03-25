"""
src.db - Fund Daily 数据库层

同时导出同步版本（原有 db/ 目录）和异步版本（src/db/）

使用方式:

    # 同步版本 (原有)
    from db import get_db, get_holdings, save_holding

    # 异步版本 (新增)
    from src.db import AsyncDatabase, get_async_db, AsyncHoldingsDB

    # FastAPI 中使用异步依赖
    from src.db.dependencies import get_async_database, get_async_holdings_db

    @app.get("/holdings")
    async def get_holdings(
        user_id: str,
        db: AsyncHoldingsDB = Depends(get_async_holdings_db)
    ):
        return await db.get_holdings(user_id)
"""

# ==================== 异步版本 (新增) ====================

from .async_database import (
    AsyncDatabase,
    AsyncDatabaseConfig,
    get_async_db,
    close_async_db,
    init_async_db,
)

from .async_crud import (
    AsyncUserDB,
    AsyncHoldingsDB,
    AsyncWatchlistDB,
    AsyncConfigDB,
    AsyncFundsDB,
    set_async_db,
)

from .base import (
    Base,
    TimestampMixin,
    UserMixin,
    User,
    Holding,
    Fund,
    FundNav,
    FundScore,
    Config,
    Watchlist,
    History,
    create_async_engine_from_url,
    get_async_session_factory,
    get_async_session,
)

from .repositories import (
    AsyncRepository,
    UserRepository,
    HoldingsRepository,
    FundsRepository,
    FundNavRepository,
    FundScoreRepository,
    ConfigRepository,
    WatchlistRepository,
    HistoryRepository,
)

from .dependencies import (
    get_async_database,
    get_async_db_connection,
    get_global_async_db,
    init_async_dependencies,
    close_async_dependencies,
    get_async_user_db,
    get_async_holdings_db,
    get_async_watchlist_db,
    get_async_config_db,
    get_async_funds_db,
    get_user_repository,
    AsyncDatabaseSession,
    get_db_session,
    lifespan_async_db,
)

# ==================== 同步版本重导出 (从原有 db/) ====================

# 为方便迁移，同时从原有 db 目录重导出常用符号
try:
    from db import (
        get_db as _sync_get_db,
        init_db as _sync_init_db,
        get_pool as _sync_get_pool,
        get_user_by_username as _sync_get_user_by_username,
        verify_user as _sync_verify_user,
        get_user_by_id as _sync_get_user_by_id,
        create_user as _sync_create_user,
        update_user_password as _sync_update_user_password,
        get_holdings as _sync_get_holdings,
        save_holding as _sync_save_holding,
        delete_holding as _sync_delete_holding,
        clear_holdings as _sync_clear_holdings,
        get_watchlist as _sync_get_watchlist,
        add_to_watchlist as _sync_add_to_watchlist,
        remove_from_watchlist as _sync_remove_from_watchlist,
        get_config as _sync_get_config,
        save_config as _sync_save_config,
        get_all_holdings as _sync_get_all_holdings,
        save_fund_info as _sync_save_fund_info,
        save_fund_nav as _sync_save_fund_nav,
        save_fund_score as _sync_save_fund_score,
        get_fund_info as _sync_get_fund_info,
        get_fund_nav as _sync_get_fund_nav,
        get_fund_score as _sync_get_fund_score,
        get_recent_funds as _sync_get_recent_funds,
        search_funds as _sync_search_funds,
        get_fund_history as _sync_get_fund_history,
        save_fund_data as _sync_save_fund_data,
        save_holdings as _sync_save_holdings,
    )
    
    # 别名：保留原有同步接口
    get_db = _sync_get_db
    init_db = _sync_init_db
    get_pool = _sync_get_pool
    get_user_by_username = _sync_get_user_by_username
    verify_user = _sync_verify_user
    get_user_by_id = _sync_get_user_by_id
    create_user = _sync_create_user
    update_user_password = _sync_update_user_password
    get_holdings = _sync_get_holdings
    save_holding = _sync_save_holding
    delete_holding = _sync_delete_holding
    clear_holdings = _sync_clear_holdings
    get_watchlist = _sync_get_watchlist
    add_to_watchlist = _sync_add_to_watchlist
    remove_from_watchlist = _sync_remove_from_watchlist
    get_config = _sync_get_config
    save_config = _sync_save_config
    get_all_holdings = _sync_get_all_holdings
    save_fund_info = _sync_save_fund_info
    save_fund_nav = _sync_save_fund_nav
    save_fund_score = _sync_save_fund_score
    get_fund_info = _sync_get_fund_info
    get_fund_nav = _sync_get_fund_nav
    get_fund_score = _sync_get_fund_score
    get_recent_funds = _sync_get_recent_funds
    search_funds = _sync_search_funds
    get_fund_history = _sync_get_fund_history
    save_fund_data = _sync_save_fund_data
    save_holdings = _sync_save_holdings
    
    _SYNC_AVAILABLE = True
except ImportError as e:
    logger = __import__("logging").getLogger(__name__)
    logger.warning(f"Sync db module not available: {e}")
    _SYNC_AVAILABLE = False


__all__ = [
    # 异步核心
    "AsyncDatabase",
    "AsyncDatabaseConfig",
    "get_async_db",
    "close_async_db",
    "init_async_db",
    # 异步 CRUD
    "AsyncUserDB",
    "AsyncHoldingsDB",
    "AsyncWatchlistDB",
    "AsyncConfigDB",
    "AsyncFundsDB",
    "set_async_db",
    # SQLAlchemy 模型
    "Base",
    "TimestampMixin",
    "UserMixin",
    "User",
    "Holding",
    "Fund",
    "FundNav",
    "FundScore",
    "Config",
    "Watchlist",
    "History",
    "create_async_engine_from_url",
    "get_async_session_factory",
    "get_async_session",
    # Repository
    "AsyncRepository",
    "UserRepository",
    "HoldingsRepository",
    "FundsRepository",
    "FundNavRepository",
    "FundScoreRepository",
    "ConfigRepository",
    "WatchlistRepository",
    "HistoryRepository",
    # FastAPI 依赖
    "get_async_database",
    "get_async_db_connection",
    "get_global_async_db",
    "init_async_dependencies",
    "close_async_dependencies",
    "get_async_user_db",
    "get_async_holdings_db",
    "get_async_watchlist_db",
    "get_async_config_db",
    "get_async_funds_db",
    "get_user_repository",
    "AsyncDatabaseSession",
    "get_db_session",
    "lifespan_async_db",
    # 同步版本 (从 db/ 重导出)
    "get_db",
    "init_db",
    "get_pool",
    "get_user_by_username",
    "verify_user",
    "get_user_by_id",
    "create_user",
    "update_user_password",
    "get_holdings",
    "save_holding",
    "delete_holding",
    "clear_holdings",
    "get_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
    "get_config",
    "save_config",
    "get_all_holdings",
    "save_fund_info",
    "save_fund_nav",
    "save_fund_score",
    "get_fund_info",
    "get_fund_nav",
    "get_fund_score",
    "get_recent_funds",
    "search_funds",
    "get_fund_history",
    "save_fund_data",
    "save_holdings",
]
