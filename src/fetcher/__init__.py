"""
Fund Data Fetcher - Main Facade Module
统一入口：提供基金数据获取、市场数据、缓存操作等公共 API
"""

from .cache.ops import clear_cache, get_cache, get_cache_stats, set_cache
from .enhanced_fetcher import (
    EnhancedFetcher,
    fetch_fund_data_enhanced,
    fetch_fund_detail_enhanced,
    get_enhanced_fetcher,
    get_fund_history_enhanced,
)
from .fund_advanced.advanced import (
    calculate_technical_from_history,
    fetch_fund_manager,
    fetch_fund_scale,
)
from .fund_basic.basic import (
    fetch_fund_data,
    fetch_fund_detail,
    fetch_fund_nav_history,
)
from .market_data.market import (
    fetch_commodity_prices,
    fetch_hot_sectors,
    fetch_market_news,
)
from .network.client import _get_ssl_context, _make_request

HAS_ENHANCED_FETCHER = True

__all__ = [
    # 缓存
    "get_cache",
    "set_cache",
    "clear_cache",
    "get_cache_stats",
    # 基础数据
    "fetch_fund_data",
    "fetch_fund_detail",
    "fetch_fund_nav_history",
    # 高级数据
    "fetch_fund_data_enhanced",
    "fetch_fund_detail_enhanced",
    "fetch_fund_manager",
    "fetch_fund_scale",
    "get_fund_history_enhanced",
    "calculate_technical_from_history",
    "EnhancedFetcher",
    "get_enhanced_fetcher",
    # 市场数据
    "fetch_market_news",
    "fetch_hot_sectors",
    "fetch_commodity_prices",
    # 网络
    "_get_ssl_context",
    "_make_request",
    # 标志
    "HAS_ENHANCED_FETCHER",
]
