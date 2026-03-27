"""
Market Data Fetcher Module
"""

from .market import (
    fetch_commodity_prices,
    fetch_hot_sectors,
    fetch_market_news,
)

__all__ = [
    "fetch_market_news",
    "fetch_hot_sectors",
    "fetch_commodity_prices",
]
