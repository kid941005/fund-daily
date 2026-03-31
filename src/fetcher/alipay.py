"""
支付宝基金数据源
提供基金详细信息、业绩排名等
"""

import logging

logger = logging.getLogger(__name__)

# 支付宝基金API
ALIPAY_BASE = "https://fund.alipay.com"


def fetch_fund_detail_alipay(fund_code: str) -> dict:
    """
    从支付宝获取基金详细信息

    Args:
        fund_code: 基金代码

    Returns:
        dict: 基金详细信息
    """
    try:
        import requests

        # 支付宝基金详情页
        url = f"{ALIPAY_BASE}/pingzhongdata/{fund_code}.html"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://fund.alipay.com/",
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            # 解析页面数据
            import re

            content = response.text

            # 提取基金名称
            name_match = re.search(r'fundName\s*=\s*["\']([^"\']+)["\']', content)
            name = name_match.group(1) if name_match else ""

            # 提取资产规模
            scale_match = re.search(r'fundScale\s*=\s*["\']([^"\']+)["\']', content)
            scale = scale_match.group(1) if scale_match else ""

            # 提取基金经理
            manager_match = re.search(r'mgrName\s*=\s*["\']([^"\']+)["\']', content)
            manager = manager_match.group(1) if manager_match else ""

            return {
                "success": True,
                "fund_code": fund_code,
                "fund_name": name,
                "scale": scale,
                "manager": manager,
                "source": "alipay",
            }
    except Exception as e:
        logger.error(f"Failed to fetch alipay fund: {e}")

    return {"success": False, "fund_code": fund_code}


def fetch_fund_ranking(fund_code: str, period: str = "1y") -> dict:
    """
    获取基金业绩排名

    Args:
        fund_code: 基金代码
        period: 统计周期 (1m, 3m, 6m, 1y, 2y, 3y)

    Returns:
        dict: 排名数据
    """
    period_map = {"1m": "1", "3m": "2", "6m": "3", "1y": "4", "2y": "5", "3y": "6"}

    try:
        import requests

        url = f"{ALIPAY_BASE}/api/matching/{period_map.get(period, '4')}/{fund_code}.json"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "ranking": data.get("data", {}).get("ranking", "暂无"),
                "total": data.get("data", {}).get("total", 0),
                "percent": data.get("data", {}).get("percent", 0),
                "source": "alipay",
            }
    except Exception as e:
        logger.error(f"Failed to fetch alipay ranking: {e}")

    return {"success": False, "ranking": "暂无"}


def get_fund_compare(fund_codes: list) -> list[dict]:
    """
    获取多只基金对比数据

    Args:
        fund_codes: 基金代码列表

    Returns:
        list: 对比数据
    """
    results = []
    for code in fund_codes:
        detail = fetch_fund_detail_alipay(code)
        if detail.get("success"):
            results.append(detail)

    return results
