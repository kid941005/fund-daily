"""
Fund Basic Fetcher Functions
"""

import json
import logging
from typing import Dict, List

from src.utils import cache_keys
from src.utils.error_handling import handle_network_errors

from ..cache import get_cache, set_cache
from ..network import _make_request

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
        # Only fetch returns when we have fresh data
        returns_data = _fetch_fund_returns(fund_code)
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
                "source": "eastmoney",
            }

            # 添加收益率数据
            if returns_data:
                result.update(returns_data)

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


def _fetch_fund_returns(fund_code: str) -> Dict:
    """
    Fetch fund return data (syl_1n, syl_3y, etc.) from pingzhongdata API

    Args:
        fund_code: 6-digit fund code

    Returns:
        dict with return data or empty dict if failed
    """
    import re

    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    content = _make_request(url)

    if not content:
        return {}

    try:
        # 提取收益率数据
        returns = {}

        # 近一年收益率 syl_1n
        match = re.search(r'syl_1n="([^"]+)"', content)
        if match:
            returns["return_1y"] = float(match.group(1))

        # 近6月收益率 syl_6y
        match = re.search(r'syl_6y="([^"]+)"', content)
        if match:
            returns["return_6m"] = float(match.group(1))

        # 近3月收益率 syl_3y
        match = re.search(r'syl_3y="([^"]+)"', content)
        if match:
            returns["return_3m"] = float(match.group(1))

        # 近1月收益率 syl_1y
        match = re.search(r'syl_1y="([^"]+)"', content)
        if match:
            returns["return_1m"] = float(match.group(1))

        logger.info(f"Got returns for {fund_code}: {returns}")
        return returns

    except Exception as e:
        logger.error(f"Failed to parse returns for {fund_code}: {e}")
        return {}


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
                "source": "eastmoney",
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
@handle_network_errors
def fetch_fund_nav_history(fund_code: str, days: int = 30) -> List[Dict]:
    """
    Fetch fund NAV history from East Money API

    Args:
        fund_code: 6-digit fund code
        days: number of days of history to fetch (default 30)

    Returns:
        list of NAV history records with real data
    """
    cache_key = cache_keys.cache_keys.fund_data(fund_code) + f"_history_{days}"

    # Check cache
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching fund NAV history: {fund_code} (days={days})")

    # East Money NAV history API
    url = f"https://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={fund_code}&page=1&per={days}"
    content = _make_request(url)

    if content:
        try:
            from html.parser import HTMLParser

            class NAVHistoryParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_tbody = False
                    self.in_td = False
                    self.current_row = []
                    self.current_data = ""
                    self.results = []
                    self.td_count = 0

                def handle_starttag(self, tag, attrs):
                    if tag == "tbody":
                        self.in_tbody = True
                    elif tag == "td" and self.in_tbody:
                        self.in_td = True
                        self.current_data = ""

                def handle_endtag(self, tag):
                    if tag == "td" and self.in_tbody:
                        self.current_row.append(self.current_data.strip())
                        self.in_td = False
                        self.td_count += 1
                    elif tag == "tr" and self.in_tbody:
                        # Parse row: date, nav, cum_nav, change%, status, status, dividend
                        if len(self.current_row) >= 4:
                            try:
                                date = self.current_row[0]
                                nav = float(self.current_row[1]) if self.current_row[1] else 0
                                # Parse change % (remove % sign and color markers)
                                change_str = self.current_row[3].replace("%", "").replace("+", "").strip()
                                if change_str and change_str != "--":
                                    change_percent = float(change_str)
                                else:
                                    change_percent = 0.0

                                self.results.append(
                                    {
                                        "date": date,
                                        "nav": nav,
                                        "change": 0,  # deprecated
                                        "change_percent": change_percent,
                                    }
                                )
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Failed to parse row: {self.current_row}")
                        self.current_row = []
                        self.td_count = 0

                def handle_data(self, data):
                    if self.in_td:
                        self.current_data += data

            parser = NAVHistoryParser()
            parser.feed(content)
            result = parser.results

            # Sort by date
            result.sort(key=lambda x: x["date"])

            logger.info(f"Got {len(result)} NAV history records for {fund_code}")

            # Cache for 1 hour
            set_cache(cache_key, result, ttl=3600)
            return result

        except Exception as e:
            logger.error(f"Failed to parse NAV history for {fund_code}: {e}")
            return []

    return []
