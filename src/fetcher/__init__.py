"""
Fund Data Fetcher - Main Facade Module
"""

# 导入所有子模块
from .cache import *
from .network import *
from .fund_basic import *
from .market_data import *
from .fund_advanced import *
from .enhanced_fetcher import (
    EnhancedFetcher,
    fetch_fund_data_enhanced,
    fetch_fund_detail_enhanced,
    get_enhanced_fetcher,
    get_fund_history_enhanced,
)

HAS_ENHANCED_FETCHER = True

__all__ = [
    "_get_ssl_context",
    "_make_request",
    "calculate_technical_from_history",
    "clear_cache",
    "fetch_commodity_prices",
    "fetch_fund_data",
    "fetch_fund_data_enhanced",
    "fetch_fund_detail",
    "fetch_fund_detail_enhanced",
    "fetch_fund_manager",
    "fetch_fund_nav_history",
    "fetch_fund_scale",
    "fetch_hot_sectors",
    "fetch_market_news",
    "get_cache",
    "get_cache_stats",
    "get_enhanced_fetcher",
    "get_fund_history_enhanced",
    "set_cache",
    "EnhancedFetcher",
    "HAS_ENHANCED_FETCHER",
]
