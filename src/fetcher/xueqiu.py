"""
雪球数据源
提供基金热度、讨论等社交数据
"""

import logging

logger = logging.getLogger(__name__)

# 雪球API配置
XUEQIU_BASE = "https://stock.xueqiu.com"


def get_fund_hot_rank(limit: int = 20) -> list[dict]:
    """
    获取雪球基金热度排行榜

    Args:
        limit: 返回数量

    Returns:
        list: 热度排行
    """
    import requests

    url = f"{XUEQIU_BASE}/v5/stock/hot_stock.json"
    params = {"type": "CN", "size": limit, "_": "1"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://xueqiu.com/",
        "Cookie": "xq_a_token=test_token",  # 需要真实 token
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            items = data.get("data", [])
            return [
                {
                    "code": item.get("symbol", "").replace("SH", "").replace("SZ", ""),
                    "name": item.get("name", ""),
                    "hot": item.get("hot_rank_index", 0),
                    "change": item.get("percent", 0),
                    "source": "xueqiu",
                }
                for item in items[:limit]
            ]
        else:
            logger.warning(f"Xueqiu API returned {response.status_code}")

    except Exception as e:
        logger.error(f"Failed to fetch xueqiu hot rank: {e}")

    # 如果 API 失败，返回东方财富热门板块数据作为备选
    return _get_fallback_hot()


def _get_fallback_hot() -> list[dict]:
    """
    获取备用热度数据（从东方财富）
    """
    import requests

    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": 10,
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        "fs": "m:1+t:23,m:0+t:81,s:0+t:80",
        "fields": "f1,f2,f3,f4,f12,f13,f14",
        "_": "1",
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", {}).get("diff", [])
            return [
                {
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "hot": abs(item.get("f3", 0)) * 10000,
                    "change": item.get("f2", 0),
                    "source": "eastmoney",
                }
                for item in items[:10]
            ]
    except Exception as e:
        logger.error(f"Failed to fetch fallback hot: {e}")

    return []


def fetch_fund_hot(fund_code: str) -> dict:
    """获取单只基金热度"""
    # 简化实现
    return {"hot": 0, "discussion_count": 0}


def fetch_fund_discussion(fund_code: str, limit: int = 5) -> list[dict]:
    """获取基金讨论"""
    # 需要登录 token，暂不实现
    return []
