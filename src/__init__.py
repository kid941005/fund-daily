"""
Fund Daily - Main package
Exports all core functions for easy importing
"""

from .advice import (
    analyze_fund,
    format_report_for_share,
    generate_advice,
    generate_daily_report,
    get_fund_detail_info,
)
from .analyzer import (
    calculate_expected_return,
    calculate_risk_metrics,
    get_commodity_sentiment,
    get_market_sentiment,
)
from .fetcher import (
    clear_cache,
    fetch_commodity_prices,
    fetch_fund_data,
    fetch_fund_detail,
    fetch_hot_sectors,
    fetch_market_news,
    get_cache,
    set_cache,
)

__all__ = [
    # Fetcher
    "fetch_fund_data",
    "fetch_fund_detail",
    "fetch_market_news",
    "fetch_hot_sectors",
    "fetch_commodity_prices",
    "get_cache",
    "set_cache",
    "clear_cache",
    # Analyzer
    "calculate_risk_metrics",
    "get_market_sentiment",
    "get_commodity_sentiment",
    "calculate_expected_return",
    # Advice
    "analyze_fund",
    "generate_daily_report",
    "format_report_for_share",
    "generate_advice",
    "get_fund_detail_info",
]

__version__ = "2.0"
