"""
Market Data Fetcher Module
"""

from .fetcher import (
    fetch_commodity_prices,
    fetch_hot_sectors,
    fetch_market_news,
)

__all__ = [
    "fetch_market_news",
    "fetch_hot_sectors",
    "fetch_commodity_prices",
]
