"""
PostgreSQL Database Module for Fund Daily
向后兼容的 facade，实际实现已拆分到子模块：
  - db.pool: 连接池管理
  - db.users: 用户操作
  - db.holdings: 持仓/监控列表/配置
  - db.fund_ops: 基金数据操作
"""

from .pool import (
    get_pool, get_db, get_cursor, init_db,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
)
from .users import (
    get_user_by_username, verify_user,
    get_user_by_id, create_user, update_user_password,
)
from .holdings import (
    get_holdings, save_holding, delete_holding, clear_holdings,
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    get_config, save_config,
)
from .fund_ops import (
    save_fund_info, save_fund_nav, save_fund_score,
    get_fund_info, get_fund_nav, get_fund_score,
    get_recent_funds, search_funds, get_fund_history,
    save_fund_data, get_all_holdings, save_holdings,
)

__all__ = [
    'get_pool', 'get_db', 'get_cursor', 'init_db',
    'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
    'get_user_by_username', 'verify_user', 'get_user_by_id', 'create_user', 'update_user_password',
    'get_holdings', 'save_holding', 'delete_holding', 'clear_holdings',
    'get_watchlist', 'add_to_watchlist', 'remove_from_watchlist',
    'get_config', 'save_config',
    'save_fund_info', 'save_fund_nav', 'save_fund_score',
    'get_fund_info', 'get_fund_nav', 'get_fund_score',
    'get_recent_funds', 'search_funds', 'get_fund_history',
    'save_fund_data', 'get_all_holdings', 'save_holdings',
]
