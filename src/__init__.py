"""
Fund Daily - Main package
Exports all core functions for easy importing
"""

from .fetcher import (
    fetch_fund_data,
    fetch_fund_detail,
    fetch_market_news,
    fetch_hot_sectors,
    fetch_commodity_prices,
    get_cache,
    set_cache,
    clear_cache,
)

from .analyzer import (
    calculate_risk_metrics,
    get_market_sentiment,
    get_commodity_sentiment,
    calculate_expected_return,
)

from .advice import (
    analyze_fund,
    generate_daily_report,
    format_report_for_share,
    generate_advice,
    get_fund_detail_info,
)

__all__ = [
    # Fetcher
    'fetch_fund_data',
    'fetch_fund_detail',
    'fetch_market_news',
    'fetch_hot_sectors',
    'fetch_commodity_prices',
    'get_cache',
    'set_cache',
    'clear_cache',
    # Analyzer
    'calculate_risk_metrics',
    'get_market_sentiment',
    'get_commodity_sentiment',
    'calculate_expected_return',
    # Advice
    'analyze_fund',
    'generate_daily_report',
    'format_report_for_share',
    'generate_advice',
    'get_fund_detail_info',
]

__version__ = "2.0"
