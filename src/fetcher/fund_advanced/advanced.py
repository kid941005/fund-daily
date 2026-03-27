"""
Fund Advanced Fetcher Functions
"""

import logging
import re
from typing import Dict, List, Optional

from src.utils import cache_keys

from ..cache import get_cache, set_cache
from ..network import _make_request

logger = logging.getLogger(__name__)


import logging


def calculate_technical_from_history(closes: List[float]) -> Dict:
    """
    Calculate technical indicators from historical NAV data

    Args:
        closes: List of NAV values (oldest to newest)

    Returns:
        Technical indicators dict
    """
    if len(closes) < 5:
        return {"ma5": None, "ma10": None, "ma20": None, "macd": {}, "rsi": None}

    from src.utils.technical import calculate_ma, calculate_macd, calculate_rsi

    # Calculate moving averages
    ma5 = calculate_ma(closes, 5)
    ma10 = calculate_ma(closes, 10)
    ma20 = calculate_ma(closes, 20)

    # Calculate MACD
    macd = calculate_macd(closes)

    # Calculate RSI
    rsi = calculate_rsi(closes, 14)

    return {"ma5": ma5, "ma10": ma10, "ma20": ma20, "macd": macd, "rsi": rsi}


def fetch_fund_manager(fund_code: str) -> Optional[Dict]:
    """
    Fetch fund manager information

    Args:
        fund_code: 6-digit fund code

    Returns:
        dict: Fund manager data or None
    """
    cache_key = cache_keys.cache_keys.fund_manager(fund_code)
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching fund manager: {fund_code}")

    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    content = _make_request(url)

    if not content:
        return None

    try:
        # 提取基金经理信息
        pattern = r"var Data_currentFundManager\s*=\s*\[([^\]]+)\]"
        match = re.search(pattern, content)

        if match:
            manager_str = match.group(1)
            # 解析第一个基金经理
            name_match = re.search(r'"name":"([^"]+)"', manager_str)
            star_match = re.search(r'"star":(\d+)', manager_str)
            time_match = re.search(r'"workTime":"([^"]+)"', manager_str)

            manager = {}
            if name_match:
                manager["name"] = name_match.group(1)
            if star_match:
                manager["star"] = int(star_match.group(1))
            if time_match:
                manager["workTime"] = time_match.group(1)

            if manager.get("name"):
                set_cache(cache_key, manager)
                return manager
    except Exception as e:
        logger.warning(f"Parse manager error: {e}")

    return None


def fetch_fund_scale(fund_code: str) -> float:
    """
    Fetch fund scale (in 100 million yuan)

    Args:
        fund_code: 6-digit fund code

    Returns:
        float: Fund scale in 100 million yuan
    """
    cache_key = f"fund_scale:{fund_code}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    content = _make_request(url)

    if not content:
        return 0.0

    try:
        # 提取规模数据 (单位：亿元)
        pattern = r"var Data_fluctuationScale\s*=\s*\{[^}]*\"series\":\s*\[\{[^}]*\"y\":\s*([\d.]+)"
        match = re.search(pattern, content)

        if match:
            scale = float(match.group(1))
            set_cache(cache_key, scale)
            return scale
    except Exception as e:
        logger.warning(f"Parse scale error: {e}")

    return 0.0
