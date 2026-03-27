"""
db package
PostgreSQL 数据库模块
"""

from .database_pg import (
    add_to_watchlist,
    clear_holdings,
    create_user,
    delete_holding,
    get_all_holdings,
)
from .database_pg import get_config as get_user_config  # 基金数据函数
from .database_pg import (
    get_db,
    get_fund_history,
    get_fund_info,
    get_fund_nav,
    get_fund_score,
    get_holdings,
    get_recent_funds,
    get_user_by_id,
    get_user_by_username,
    get_watchlist,
    init_db,
    remove_from_watchlist,
)
from .database_pg import save_config as save_user_config
from .database_pg import (
    save_fund_data,
    save_fund_info,
    save_fund_nav,
    save_fund_score,
    save_holding,
    save_holdings,
    search_funds,
    update_user_password,
    verify_user,
)

__all__ = [
    "get_db",
    "init_db",
    "create_user",
    "get_user_by_username",
    "get_user_by_id",
    "verify_user",
    "update_user_password",
    "get_holdings",
    "save_holdings",
    "save_holding",
    "delete_holding",
    "clear_holdings",
    "get_user_config",
    "save_user_config",
    "get_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
    "get_all_holdings",
    # 基金数据函数
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
]
