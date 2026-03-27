"""
Risk calculation module
提供基金风险指标计算
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def calculate_risk_metrics(month_1, month_3, year_1, fund_type: str = "") -> Dict:
    """
    Calculate risk metrics based on returns and fund type

    Args:
        month_1: 近1月收益率 (%)
        month_3: 近3月收益率 (%)
        year_1: 近1年收益率 (%)
        fund_type: 基金类型（如"股票型"、"混合型"等）

    Returns:
        dict: 风险指标
    """

    def parse_return(val):
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        return float(str(val).replace("%", "").strip()) if val else 0.0

    m1 = parse_return(month_1)
    m3 = parse_return(month_3)
    y1 = parse_return(year_1)

    # 1. 根据基金类型确定基础风险等级
    base_risk_score = 2

    if fund_type:
        if "股票" in fund_type or "指数" in fund_type or "ETF" in fund_type or "LOF" in fund_type:
            base_risk_score = 7
        elif "混合" in fund_type:
            base_risk_score = 5
        elif "债券" in fund_type or "纯债" in fund_type:
            base_risk_score = 1
        elif "货币" in fund_type:
            base_risk_score = 0

    # 2. 基于波动性调整
    volatility = abs(m3 - m1)
    risk_score = base_risk_score

    if volatility > 15:
        risk_score += 2
    elif volatility > 10:
        risk_score += 1
    elif volatility < 5 and base_risk_score < 5:
        risk_score -= 1

    # 3. 确定风险等级
    risk_score = max(0, min(10, risk_score))

    if risk_score >= 7:
        risk_level = "高风险"
    elif risk_score >= 5:
        risk_level = "中高风险"
    elif risk_score >= 3:
        risk_level = "中等风险"
    elif risk_score >= 1:
        risk_level = "中低风险"
    else:
        risk_level = "低风险"

    # 4. 年化波动率
    returns = [m1, m3, y1 / 12]
    std_dev = (max(returns) - min(returns)) / 2 if len(returns) > 1 else 0

    # 5. 夏普比率
    risk_free_rate = 3.0
    if std_dev > 0:
        sharpe_ratio = (y1 - risk_free_rate) / (std_dev * 12)
    else:
        sharpe_ratio = 0

    # 6. 最大回撤估算
    estimated_max_drawdown = min(volatility * 1.5, 50)

    # 7. 收益风险比
    return_ratio = y1 / volatility if volatility > 0 else 0

    suggestions = {
        "高风险": "适合风险承受能力强的投资者，建议占比不超过30%",
        "中高风险": "适合追求高收益的投资者，建议占比不超过50%",
        "中等风险": "适合稳健型投资者，建议占比不超过70%",
        "中低风险": "适合保守型投资者，可作为主力持仓",
        "低风险": "适合保本型投资者，可作为现金管理",
    }

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "volatility": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "estimated_max_drawdown": round(estimated_max_drawdown, 2),
        "return_ratio": round(return_ratio, 2),
        "suggestion": suggestions.get(risk_level, "请根据自身风险承受能力配置"),
    }


def fetch_historical_nav(fund_code: str, days: int = 365) -> List[Dict]:
    """Fetch historical NAV data"""
    # 简化实现
    return []


__all__ = ["calculate_risk_metrics", "fetch_historical_nav"]
