"""
流动性评分模块
"""

from typing import Dict


def calculate_liquidity_score(daily_change: float, fund_scale: float) -> Dict:
    """
    流动性评分 (满分3分)
    """
    # 涨幅太大或太小都影响流动性
    if abs(daily_change) < 3:
        s = 3
        r = f"涨跌{daily_change:+.2f}%，正常"
    elif abs(daily_change) < 5:
        s = 2
        r = f"涨跌{daily_change:+.2f}%，波动较大"
    else:
        s = 1
        r = f"涨跌{daily_change:+.2f}%，异常波动"
    
    return {
        "score": s,
        "reason": r,
        "details": {"daily_change": daily_change}
    }