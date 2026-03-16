"""
择时信号模块
基于市场情绪、技术指标、资金流向判断买入/卖出时机
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def analyze_market_timing(market_sentiment: Dict, commodity_sentiment: Dict, 
                         hot_sectors: List[Dict], news: List[Dict]) -> Dict:
    """
    综合分析市场择时信号
    
    Args:
        market_sentiment: 市场情绪数据
        commodity_sentiment: 大宗商品情绪
        hot_sectors: 热门板块
        news: 市场新闻
    
    Returns:
        dict: 择时信号
    """
    signals = []
    score = 0
    
    # 1. 市场情绪信号
    sentiment = market_sentiment.get("sentiment", "平稳")
    sentiment_score = market_sentiment.get("score", 0)
    
    if "乐观" in sentiment or sentiment_score > 30:
        signals.append({"type": "市场情绪", "signal": "买入", "reason": "市场情绪乐观", "weight": 0.3})
        score += 30
    elif "恐慌" in sentiment or sentiment_score < -30:
        signals.append({"type": "市场情绪", "signal": "卖出", "reason": "市场恐慌情绪", "weight": 0.3})
        score -= 30
    elif "平稳" in sentiment:
        signals.append({"type": "市场情绪", "signal": "持有", "reason": "市场情绪平稳", "weight": 0.1})
    
    # 2. 大宗商品信号
    commodity = commodity_sentiment.get("sentiment", "平稳")
    if "上涨" in commodity or "强势" in commodity:
        signals.append({"type": "大宗商品", "signal": "买入", "reason": "商品价格强势", "weight": 0.2})
        score += 20
    elif "下跌" in commodity or "弱势" in commodity:
        signals.append({"type": "大宗商品", "signal": "卖出", "reason": "商品价格走弱", "weight": 0.2})
        score -= 20
    
    # 3. 板块信号
    if hot_sectors:
        # 计算热门板块上涨比例
        up_count = sum(1 for s in hot_sectors[:5] if s.get("change", 0) > 0)
        if up_count >= 4:
            signals.append({"type": "板块动能", "signal": "买入", "reason": "热门板块多数上涨", "weight": 0.2})
            score += 20
        elif up_count <= 1:
            signals.append({"type": "板块动能", "signal": "卖出", "reason": "热门板块多数下跌", "weight": 0.2})
            score -= 20
    
    # 4. 新闻情绪信号
    if news:
        positive = sum(1 for n in news[:5] if "涨" in n.get("title", "") or "利好" in n.get("title", ""))
        negative = sum(1 for n in news[:5] if "跌" in n.get("title", "") or "利空" in n.get("title", ""))
        if positive > negative + 1:
            signals.append({"type": "新闻情绪", "signal": "买入", "reason": "利好消息较多", "weight": 0.15})
            score += 15
        elif negative > positive + 1:
            signals.append({"type": "新闻情绪", "signal": "卖出", "reason": "利空消息较多", "weight": 0.15})
            score -= 15
    
    # 综合判断
    if score >= 30:
        overall = "强烈买入"
    elif score >= 15:
        overall = "买入"
    elif score > -15:
        overall = "持有"
    elif score > -30:
        overall = "卖出"
    else:
        overall = "强烈卖出"
    
    return {
        "overall_signal": overall,
        "score": score,
        "signals": signals,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_timing_signals(fund_codes: List[str]) -> Dict:
    """
    获取基金的择时信号
    
    Args:
        fund_codes: 基金代码列表
    
    Returns:
        dict: 择时信号结果
    """
    from ..fetcher import fetch_market_news, fetch_hot_sectors
    from ..analyzer import get_market_sentiment, get_commodity_sentiment
    
    # 获取市场数据
    market = get_market_sentiment()
    commodity = get_commodity_sentiment()
    sectors = fetch_hot_sectors(5)
    news = fetch_market_news(5)
    
    # 分析市场时机
    timing = analyze_market_timing(market, commodity, sectors, news)
    
    return {
        "market_timing": timing,
        "fund_codes": fund_codes,
    }
