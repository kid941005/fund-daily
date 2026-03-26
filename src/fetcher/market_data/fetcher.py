"""
Market Data Fetcher Functions
"""

import logging
import urllib.parse
from typing import Dict, List, Optional, Any
import requests
import json

from src.utils import cache_keys
from src.utils.error_handling import handle_network_errors
from ..network import _make_request
from ..cache import get_cache, set_cache

logger = logging.getLogger(__name__)


def fetch_market_news(limit: int = 8) -> List[Dict]:
    """
    Fetch market hot news

    Args:
        limit: number of news items to fetch (default 8)

    Returns:
        list of news items
    """
    cache_key = cache_keys.cache_keys.market_news(limit)

    # 检查缓存
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching market news (limit={limit})")

    # East Money hot news API
    url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
    content = _make_request(url)

    if content and content.strip():
        try:
            # 解析JSON（东方财富返回格式：var ajaxResult={...}）
            json_str = content.strip()
            if json_str.startswith("var ajaxResult="):
                json_str = json_str[len("var ajaxResult=") :]
            data = json.loads(json_str)
            raw_list = data.get("LivesList", []) or []
            news_list = [
                {
                    "title": item.get("title", ""),
                    "summary": item.get("digest", ""),
                    "url": item.get("url_w", "") or item.get("url_m", ""),
                    "time": item.get("showtime", ""),
                    "source": "东方财富",
                }
                for item in raw_list[:limit]
            ]

            # 缓存结果
            set_cache(cache_key, news_list)
            return news_list
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse market news JSON: {e}")
            return []
    else:
        logger.error("Failed to fetch market news: empty response")
        return []


def fetch_hot_sectors(limit: int = 10) -> List[Dict]:
    """
    Fetch hot sectors (行业板块)

    Args:
        limit: number of sectors to fetch (default 10)

    Returns:
        list of hot sectors
    """
    cache_key = cache_keys.cache_keys.hot_sectors(limit)

    # 检查缓存
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching hot sectors (limit={limit})")

    # East Money hot sectors API
    base_url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": limit,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        "fs": "m:90+t:2+f:!50",
        "fields": "f1,f2,f3,f4,f12,f13,f14,f152,f227,f228,f229,f230,f231,f232,f233,f234,f235,f236,f237,f238",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "wbp2u": "|0|0|0|web",
    }

    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"

    content = _make_request(url)

    if content:
        try:
            data = json.loads(content)
            raw_sectors = data.get("data", {}).get("diff", [])[:limit]
            sectors = [
                {
                    "name": s.get("f14", ""),
                    "change": s.get("f3", 0),
                    "volume": s.get("f2", 0),
                    "reason": s.get("f4", ""),
                }
                for s in raw_sectors
            ]

            # 缓存结果
            set_cache(cache_key, sectors)
            return sectors
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse hot sectors JSON: {e}")
            return []
    else:
        logger.error("Failed to fetch hot sectors")
        return []


def fetch_commodity_prices() -> Dict[str, float]:
    """
    Fetch commodity prices (gold, oil, etc.)

    Returns:
        dict of commodity prices
    """
    cache_key = cache_keys.cache_keys.market_sentiment("commodity")

    # 检查缓存
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info("Fetching commodity prices")

    # 这里可以添加实际的商品价格API
    # 目前返回模拟数据
    prices = {"gold": 1950.50, "oil": 75.30, "silver": 23.15, "copper": 3.85}

    # 缓存结果
    set_cache(cache_key, prices)
    return prices
