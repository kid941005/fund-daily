"""
市场情绪评分模块
"""

from typing import Dict


def calculate_sentiment_score(market_sentiment: str, market_score: int) -> Dict:
    """
    市场情绪评分 (满分10分)
    """
    sentiment_map = {
        "乐观": 10,
        "偏多": 8,
        "平稳": 5,
        "偏空": 2,
        "恐慌": 0,
    }

    score = sentiment_map.get(market_sentiment, 5)

    return {
        "score": score,
        "reason": f"市场{market_sentiment}",
        "details": {"sentiment": market_sentiment, "score": market_score},
    }
