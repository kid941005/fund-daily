"""
动态权重模块
根据市场周期自动调整评分权重
"""

from typing import Dict
from src.analyzer import get_market_sentiment

# 市场周期定义
MARKET_CYCLES = {
    "bull": {      # 牛市
        "name": "牛市",
        "valuation": 20,    # 估值权重降低
        "performance": 25,   # 业绩保持
        "risk_control": 10,  # 风控降低
        "momentum": 25,     # 动量增加
        "sentiment": 10,
        "sector": 5,
        "manager": 3,
        "liquidity": 2
    },
    "bear": {      # 熊市
        "name": "熊市",
        "valuation": 25,    # 估值重要
        "performance": 20,
        "risk_control": 25,  # 风控增加
        "momentum": 15,     # 动量适当提高
        "sentiment": 5,
        "sector": 5,
        "manager": 3,
        "liquidity": 2
        # 总计: 25+20+25+15+5+5+3+2 = 100分
    },
    "震荡": {       # 震荡市
        "name": "震荡市",
        "valuation": 25,
        "performance": 25,
        "risk_control": 15,
        "momentum": 15,
        "sentiment": 10,
        "sector": 5,
        "manager": 3,
        "liquidity": 2
    }
}

# 基础权重
BASE_WEIGHTS = {
    "valuation": 25,
    "performance": 25,
    "risk_control": 15,
    "momentum": 20,
    "sentiment": 10,
    "sector": 10,
    "manager": 3,
    "liquidity": 2
}


def detect_market_cycle() -> str:
    """检测当前市场周期"""
    try:
        sentiment = get_market_sentiment()
        trend = sentiment.get("trend", "")
        confidence = sentiment.get("confidence", 0)
        
        # 基于市场情绪判断周期
        if "涨" in trend or confidence > 70:
            return "bull"
        elif "跌" in trend or confidence < 30:
            return "bear"
        else:
            return "震荡"
    except Exception:
        return "震荡"  # 默认震荡市


def get_dynamic_weights() -> Dict[str, int]:
    """获取动态权重"""
    cycle = detect_market_cycle()
    weights = MARKET_CYCLES.get(cycle, MARKET_CYCLES["震荡"]).copy()
    weights["cycle"] = MARKET_CYCLES[cycle]["name"]
    return weights


def adjust_score_by_cycle(score: Dict, cycle: str = None) -> Dict:
    """根据市场周期调整评分"""
    if cycle is None:
        cycle = detect_market_cycle()
    
    weights = MARKET_CYCLES.get(cycle, MARKET_CYCLES["震荡"])
    adjusted = score.copy()
    adjusted["market_cycle"] = weights["name"]
    
    # 根据周期调整总分
    if cycle == "bull":
        # 牛市：动量加成
        adjusted["adjustment"] = "动量+5%"
    elif cycle == "bear":
        # 熊市：风控加成
        adjusted["adjustment"] = "风控+10%"
    else:
        adjusted["adjustment"] = "均衡"
    
    return adjusted
