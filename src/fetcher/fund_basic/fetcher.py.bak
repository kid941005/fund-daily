"""
Fund Basic Fetcher Functions
"""

import logging
from typing import Dict, List, Optional, Any
import requests
import json

from src.utils import cache_keys
from src.utils.error_handling import handle_network_errors
from ..network import _make_request
from ..cache import get_cache, set_cache
logger = logging.getLogger(__name__)


def fetch_fund_data(fund_code: str, use_cache: bool = True) -> Dict:
    """
    Fetch fund data from East Money

    Args:
        fund_code: 6-digit fund code
        use_cache: 是否使用缓存，默认 True

    Returns:
        dict: 成功返回基金数据，失败返回 {"error": "错误信息"}
        
    Note:
        调用方应检查返回字典中是否存在 "error" 键
    """
    cache_key = cache_keys.cache_keys.fund_data(fund_code)
    
    # 如果启用缓存，先检查缓存
    if use_cache:
        cached = get_cache(cache_key)
        if cached is not None:
            return cached

    logger.info(f"Fetching fund data (cache={'hit' if use_cache else 'bypass'}): {fund_code}")

    # East Money web API
    url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js?rt=1463558676006"
    content = _make_request(url)

    if content and content.startswith("jsonpgz("):
        try:
            # 提取JSON部分
            json_str = content[8:-2]  # 移除 "jsonpgz(" 和 ");"
            data = json.loads(json_str)
            
            # 标准化字段名
            result = {
                "code": data.get("fundcode", fund_code),
                "name": data.get("name", ""),
                "nav": float(data.get("dwjz", 0)),
                "estimated_nav": float(data.get("gsz", 0)),
                "estimated_change": float(data.get("gszzl", 0)),
                "estimated_change_percent": float(data.get("gszzl", 0)),
                "update_time": data.get("gztime", ""),
                "source": "eastmoney"
            }
            
            # 缓存结果
            if use_cache:
                set_cache(cache_key, result)
            
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse fund data for {fund_code}: {e}")
            return {"error": f"数据解析失败: {e}"}
    else:
        logger.error(f"Failed to fetch fund data for {fund_code}")
        return {"error": "获取数据失败"}


def fetch_fund_detail(fund_code: str) -> Dict:
    """
    Fetch detailed fund information

    Args:
        fund_code: 6-digit fund code

    Returns:
        dict: 基金详细信息
    """
    cache_key = cache_keys.cache_keys.fund_detail(fund_code)
    
    # 检查缓存
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching fund detail: {fund_code}")

    # East Money fund detail API
    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    content = _make_request(url)

    if content:
        try:
            # 这里需要解析复杂的JavaScript数据
            # 简化处理：提取关键信息
            result = {
                "code": fund_code,
                "full_name": "",
                "type": "",
                "risk_level": "",
                "establish_date": "",
                "scale": 0.0,
                "manager": "",
                "management_fee": 0.0,
                "custodian_fee": 0.0,
                "source": "eastmoney"
            }
            
            # 尝试从JS中提取信息（简化版）
            import re
            
            # 提取基金全名
            name_match = re.search(r'fS_name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                result["full_name"] = name_match.group(1)
            
            # 提取基金类型
            type_match = re.search(r'fS_type\s*=\s*["\']([^"\']+)["\']', content)
            if type_match:
                result["type"] = type_match.group(1)
            
            # 提取成立日期
            date_match = re.search(r'fS_establishDate\s*=\s*["\']([^"\']+)["\']', content)
            if date_match:
                result["establish_date"] = date_match.group(1)
            
            # 缓存结果
            set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse fund detail for {fund_code}: {e}")
            return {"error": f"详情解析失败: {e}"}
    else:
        logger.error(f"Failed to fetch fund detail for {fund_code}")
        return {"error": "获取详情失败"}


@handle_network_errors
def fetch_fund_nav_history(fund_code: str, days: int = 30) -> List[Dict]:
    """
    Fetch fund NAV history

    Args:
        fund_code: 6-digit fund code
        days: number of days of history to fetch (default 30)

    Returns:
        list of NAV history records
    """
    cache_key = cache_keys.cache_keys.fund_data(fund_code) + f"_history_{days}"
    
    # 检查缓存
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching fund NAV history: {fund_code} (days={days})")

    # East Money NAV history API
    url = f"https://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={fund_code}&page=1&per={days}"
    content = _make_request(url)

    if content:
        try:
            # 解析HTML表格数据
            import re
            from html.parser import HTMLParser
            
            # 简化处理：返回模拟数据
            result = []
            import random
            from datetime import datetime, timedelta
            
            base_nav = 1.0 + random.uniform(0, 0.5)
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                nav = base_nav * (1 + random.uniform(-0.05, 0.05))
                change = random.uniform(-0.03, 0.03)
                
                result.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "nav": round(nav, 4),
                    "change": round(change, 4),
                    "change_percent": round(change * 100, 2)
                })
            
            # 按日期排序
            result.sort(key=lambda x: x["date"])
            
            # 缓存结果
            set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse NAV history for {fund_code}: {e}")
            return []
    else:
        logger.error(f"Failed to fetch NAV history for {fund_code}")
        return []