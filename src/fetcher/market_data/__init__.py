"""
Market Data Fetcher Module
"""

from .fetcher import (
    fetch_market_news,
    fetch_hot_sectors,
    fetch_commodity_prices,
)

__all__ = [
    "fetch_market_news",
    "fetch_hot_sectors",
    "fetch_commodity_prices",
]
