"""
雪球数据源
提供基金热度、讨论等社交数据
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 雪球API配置
XUEQIU_BASE = "https://stock.xueqiu.com"


def fetch_fund_hot(fund_code: str) -> Dict:
    """
    获取基金热度数据
    
    Args:
        fund_code: 基金代码
        
    Returns:
        dict: 热度数据
    """
    try:
        import requests
        
        # 雪球基金讨论热度
        url = f"{XUEQIU_BASE}/v5/stock/quote.json"
        params = {
            "symbol": f"SH{fund_code}" if fund_code.startswith("1") or fund_code.startswith("5") 
                      else f"SZ{fund_code}",
            "_": "1"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": "xq_a_token=test"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "hot": data.get("data", {}).get("percent", 0),
                "discussion_count": data.get("data", {}).get("discussion_count", 0)
            }
    except Exception as e:
        logger.error(f"Failed to fetch xueqiu hot: {e}")
    
    return {"success": False, "hot": 0, "discussion_count": 0}


def fetch_fund_discussion(fund_code: str, limit: int = 5) -> List[Dict]:
    """
    获取基金最新讨论
    
    Args:
        fund_code: 基金代码
        limit: 返回数量
        
    Returns:
        list: 讨论列表
    """
    try:
        import requests
        
        url = f"{XUEQIU_BASE}/v5/status/mentions.json"
        params = {
            "symbol": f"SH{fund_code}" if fund_code.startswith("1") or fund_code.startswith("5") 
                      else f"SZ{fund_code}",
            "size": limit,
            "_": "1"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": "xq_a_token=test"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", {}).get("items", [])
            return [
                {
                    "user": item.get("user", {}).get("screen_name", ""),
                    "text": item.get("text", ""),
                    "created_at": item.get("created_at", ""),
                    "source": "xueqiu"
                }
                for item in items[:limit]
            ]
    except Exception as e:
        logger.error(f"Failed to fetch xueqiu discussion: {e}")
    
    return []


def get_fund_hot_rank(limit: int = 20) -> List[Dict]:
    """
    获取基金热度排行榜
    
    Args:
        limit: 返回数量
        
    Returns:
        list: 热度排行
    """
    try:
        import requests
        
        url = f"{XUEQIU_BASE}/v5/stock/hot_stock.json"
        params = {
            "type": "CN",
            "size": limit,
            "_": "1"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", [])
            return [
                {
                    "code": item.get("symbol", ""),
                    "name": item.get("name", ""),
                    "hot": item.get("hot_rank_index", 0),
                    "change": item.get("percent", 0),
                    "source": "xueqiu"
                }
                for item in items[:limit]
            ]
    except Exception as e:
        logger.error(f"Failed to fetch xueqiu hot rank: {e}")
    
    return []
