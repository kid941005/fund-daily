"""
Enhanced market sentiment analysis
"""

import logging
from typing import Dict, List
from datetime import datetime

from ..fetcher import fetch_hot_sectors, fetch_market_news

logger = logging.getLogger(__name__)


# 扩展情绪词典
SENTIMENT_DICT = {
    # 极度乐观
    '暴涨': 15, '大涨': 12, '涨停': 15, '突破': 10, '创新高': 12, '全面上涨': 15,
    '利好': 8, '利好出台': 10, '政策利好': 8, '业绩大增': 10, '订单大增': 8,
    '看涨': 10, '强烈推荐': 12, '牛市': 15, '拐点': 8, '反转': 10,
    
    # 乐观
    '上涨': 5, '反弹': 6, '回暖': 5, '企稳': 4, '收涨': 4, '红盘': 5,
    '活跃': 4, '资金流入': 5, '加仓': 5, '增持': 5, '买入': 5,
    '看好': 5, '推荐': 4, '机会': 4, '低估': 5, '价值': 4,
    
    # 中性
    '震荡': 0, '整理': 0, '平盘': 0, '轮动': 0, '中性': 0,
    
    # 悲观
    '下跌': -5, '回落': -4, '调整': -3, '收跌': -4, '绿盘': -5,
    '减仓': -4, '风险': -4,
    '高估': -5, '谨慎': -4, '回避': -5, '偏空': -5,
    
    # 极度悲观
    '暴跌': -15, '大跌': -12, '跌停': -15, '创新低': -12, '崩盘': -18,
    '利空': -8, '业绩下滑': -8, '亏损': -8, '违约': -10,
    '看跌': -10, '熊市': -15, '清仓': -10, '割肉': -10,
    '恐慌': -12, '踩踏': -15, '爆仓': -15, '闪崩': -12,
}


# 板块情绪权重
SECTOR_WEIGHTS = {
    '新能源': 1.3,    # 热点板块，权重高
    '光伏': 1.3,
    '锂电': 1.3,
    '芯片': 1.2,
    '半导体': 1.2,
    '人工智能': 1.2,
    '医药': 1.0,
    '消费': 1.0,
    '银行': 0.9,
    '地产': 0.8,      # 传统行业，权重低
    '基建': 0.9,
}


def calculate_sentiment_score(text: str) -> float:
    """
    Calculate sentiment score for text using enhanced dictionary
    
    Args:
        text: Text to analyze
        
    Returns:
        float: Sentiment score
    """
    score = 0.0
    matched_words = []
    
    text = text.lower()  # 统一小写匹配
    
    for word, value in SENTIMENT_DICT.items():
        if word in text:
            score += value
            matched_words.append((word, value))
    
    return score, matched_words


def analyze_news_sentiment(news: List[Dict]) -> Dict:
    """
    Analyze sentiment from news headlines
    
    Args:
        news: List of news items
        
    Returns:
        dict: News sentiment analysis
    """
    if not news:
        return {"score": 0, "sentiment": "平稳", "details": {}}
    
    total_score = 0
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    all_matches = []
    
    for item in news:
        title = item.get('title', '')
        score, matches = calculate_sentiment_score(title)
        
        total_score += score
        all_matches.extend(matches)
        
        if score > 0:
            positive_count += 1
        elif score < 0:
            negative_count += 1
        else:
            neutral_count += 1
    
    # Normalize by number of news
    avg_score = total_score / len(news) if news else 0
    
    # Determine sentiment
    if avg_score > 8:
        sentiment = "极度乐观"
    elif avg_score > 3:
        sentiment = "乐观"
    elif avg_score > -3:
        sentiment = "平稳"
    elif avg_score > -8:
        sentiment = "悲观"
    else:
        sentiment = "极度悲观"
    
    return {
        "score": round(avg_score, 2),
        "sentiment": sentiment,
        "positive": positive_count,
        "negative": negative_count,
        "neutral": neutral_count,
        "top_matches": sorted(all_matches, key=lambda x: abs(x[1]), reverse=True)[:5]
    }


def analyze_sector_sentiment(sectors: List[Dict]) -> Dict:
    """
    Analyze sentiment from sector performance
    
    Args:
        sectors: List of sector data
        
    Returns:
        dict: Sector sentiment analysis
    """
    if not sectors:
        return {"score": 0, "sentiment": "平稳", "details": {}}
    
    total_score = 0
    total_weight = 0
    up_count = 0
    down_count = 0
    
    for sector in sectors:
        name = sector.get('name', '')
        change = sector.get('change', 0)
        
        # Get sector weight
        weight = 1.0
        for key, w in SECTOR_WEIGHTS.items():
            if key in name:
                weight = w
                break
        
        # Score based on change
        if change > 3:
            sector_score = 10 * weight
        elif change > 1:
            sector_score = 5 * weight
        elif change > -1:
            sector_score = 0
        elif change > -3:
            sector_score = -5 * weight
        else:
            sector_score = -10 * weight
        
        total_score += sector_score
        total_weight += weight
        
        if change > 0:
            up_count += 1
        elif change < 0:
            down_count += 1
    
    avg_score = total_score / total_weight if total_weight > 0 else 0
    
    # Determine sentiment
    if avg_score > 6:
        sentiment = "乐观"
    elif avg_score > 2:
        sentiment = "偏多"
    elif avg_score > -2:
        sentiment = "平稳"
    elif avg_score > -6:
        sentiment = "偏空"
    else:
        sentiment = "悲观"
    
    return {
        "score": round(avg_score, 2),
        "sentiment": sentiment,
        "up_count": up_count,
        "down_count": down_count,
        "total": len(sectors)
    }


def get_enhanced_market_sentiment() -> Dict:
    """
    Get enhanced market sentiment with improved algorithm
    
    Returns:
        dict: Enhanced market sentiment analysis
    """
    try:
        # Get data
        sectors = fetch_hot_sectors(10)
        news = fetch_market_news(10)
        
        # Analyze each component
        sector_analysis = analyze_sector_sentiment(sectors)
        news_analysis = analyze_news_sentiment(news)
        
        # Calculate combined score
        # 板块表现权重 60%，新闻情绪权重 40%
        combined_score = (
            sector_analysis.get('score', 0) * 0.6
            + news_analysis.get('score', 0) * 0.4
        )
        
        # Clamp to -100 to 100
        combined_score = max(-100, min(100, combined_score))
        
        # Determine final sentiment
        if combined_score > 30:
            final_sentiment = "乐观"
        elif combined_score > 10:
            final_sentiment = "偏多"
        elif combined_score > -10:
            final_sentiment = "平稳"
        elif combined_score > -30:
            final_sentiment = "偏空"
        else:
            final_sentiment = "恐慌"
        
        # Generate recommendation
        if final_sentiment == "乐观":
            recommendation = "市场情绪乐观，建议适度加仓"
        elif final_sentiment == "偏多":
            recommendation = "市场偏多，建议保持当前仓位"
        elif final_sentiment == "平稳":
            recommendation = "市场平稳，建议观望为主"
        elif final_sentiment == "偏空":
            recommendation = "市场偏谨慎，建议适当减仓"
        else:
            recommendation = "市场恐慌，建议减仓或清仓观望"
        
        return {
            "sentiment": final_sentiment,
            "score": round(combined_score, 2),
            "sector_analysis": sector_analysis,
            "news_analysis": news_analysis,
            "recommendation": recommendation,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced sentiment analysis: {e}")
        return {
            "sentiment": "平稳",
            "score": 0,
            "error": str(e)
        }
