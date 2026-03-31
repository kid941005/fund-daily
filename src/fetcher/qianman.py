"""
且慢数据源
提供基金组合、投顾策略等数据
"""

import logging

logger = logging.getLogger(__name__)

# 且慢API
QIANMAN_BASE = "https://qieman.com"


def fetch_portfolio_list() -> list[dict]:
    """
    获取且慢上的基金组合列表

    Returns:
        list: 组合列表
    """
    try:
        import requests

        url = f"{QIANMAN_BASE}/cmc/allPortfolios"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://qieman.com/",
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "risk_level": item.get("riskLevel"),
                    "min_amount": item.get("minInvestAmount"),
                    "source": "qieman",
                }
                for item in data.get("data", [])
            ]
    except Exception as e:
        logger.error(f"Failed to fetch qieman portfolios: {e}")

    return []


def fetch_portfolio_detail(portfolio_id: str) -> dict:
    """
    获取组合详情

    Args:
        portfolio_id: 组合ID

    Returns:
        dict: 组合详情
    """
    try:
        import requests

        url = f"{QIANMAN_BASE}/cmc/portfolios/{portfolio_id}"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "id": portfolio_id,
                "name": data.get("name"),
                "description": data.get("description"),
                "funds": data.get("funds", []),
                "allocation": data.get("allocation", []),
                "source": "qieman",
            }
    except Exception as e:
        logger.error(f"Failed to fetch qieman portfolio: {e}")

    return {"success": False}


def fetch_fund_advisor() -> list[dict]:
    """
    获取基金投顾策略

    Returns:
        list: 投顾策略列表
    """
    try:
        import requests

        url = f"{QIANMAN_BASE}/cmc/allAdvisors"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "risk_level": item.get("riskLevel"),
                    "annual_return": item.get("annualReturn"),
                    "source": "qieman",
                }
                for item in data.get("data", [])
            ]
    except Exception as e:
        logger.error(f"Failed to fetch qieman advisors: {e}")

    return []
