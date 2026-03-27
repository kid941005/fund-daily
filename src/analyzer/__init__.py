"""
Analysis module for Fund Daily
统一入口模块 - 负责风险计算和市场情绪分析
"""

import logging
from typing import Dict, List

from src.utils.error_handling import handle_errors

# 从fetcher导入必要的函数（保持向后兼容）
from ..fetcher import (
    fetch_commodity_prices,
    fetch_hot_sectors,
    fetch_market_news,
)

# 统一从risk.py导入风险计算
from .risk import calculate_risk_metrics

# 统一从sentiment.py导入情绪分析
from .sentiment import get_enhanced_market_sentiment

logger = logging.getLogger(__name__)


@handle_errors(default_return={"sentiment": "平稳", "score": 3, "error": True}, log_level="warning")
def get_market_sentiment() -> Dict:
    """Get market sentiment (兼容旧接口，内部调用enhanced版本)"""
    return get_enhanced_market_sentiment()


def get_commodity_sentiment() -> Dict:
    """
    Get commodity sentiment analysis

    Returns:
        dict: {
            "sentiment": "乐观"/"偏多"/"平稳"/"偏空",
            "score": 0-10,
            "details": {...}
        }
    """

    prices = fetch_commodity_prices()

    sentiment = "平稳"
    score = 3

    if prices:
        # fetch_commodity_prices 返回 Dict[str, float]，值为价格变化百分比
        changes = [float(v) for v in prices.values() if v is not None]
        avg_change = sum(changes) / len(changes) if changes else 0

        if avg_change > 2:
            sentiment = "乐观"
            score = 8
        elif avg_change > 0:
            sentiment = "偏多"
            score = 5
        elif avg_change > -2:
            sentiment = "平稳"
            score = 3
        else:
            sentiment = "偏空"
            score = 1

    return {"sentiment": sentiment, "score": score, "details": prices}


@handle_errors(default_return={"expected_return": 0, "error": True}, log_level="warning")
def calculate_expected_return(holdings: List[Dict], funds_data: List[Dict]) -> Dict:
    """
    Calculate expected return for holdings

    Args:
        holdings: List of holdings with code and amount
        funds_data: List of fund data

    Returns:
        dict: Expected return analysis
    """
    if not holdings or not funds_data:
        return {"expected_return": 0, "message": "无持仓数据"}

    # 计算加权平均预期收益
    total_value = sum(h.get("amount", 0) for h in holdings)
    if total_value == 0:
        return {"expected_return": 0, "message": "持仓金额为0"}

    # 构建基金数据字典，避免 O(n*m) 查找
    fund_dict = {f.get("fundcode"): f for f in funds_data}

    # 简化实现：基于基金近期收益计算
    weighted_return = 0
    for h in holdings:
        code = h.get("code")
        amount = h.get("amount", 0)
        weight = amount / total_value

        # O(1) 查找
        f = fund_dict.get(code)
        if f:
            return_1y = float(f.get("syl_1n") or 0)
            weighted_return += weight * return_1y

    return {"expected_return": round(weighted_return, 2), "total_value": total_value, "message": "基于近1年收益计算"}


__all__ = [
    "calculate_risk_metrics",
    "get_market_sentiment",
    "get_enhanced_market_sentiment",
    "get_commodity_sentiment",
    "calculate_expected_return",
]
