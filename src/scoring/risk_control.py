"""
风险控制评分模块
"""

from typing import Dict


def calculate_risk_control_score(risk_metrics: Dict, fund_data: Dict = None) -> Dict:
    """
    风险控制评分 (满分15分)
    基于夏普比率、最大回撤、波动率
    """
    details = {}
    scores = []

    # 3.1 夏普比率 (6分)
    sharpe = risk_metrics.get("sharpe_ratio", 0) or 0
    if sharpe >= 1.5:
        s = 6
        r = f"夏普比率{sharpe:.2f}，优秀"
    elif sharpe >= 1.0:
        s = 5
        r = f"夏普比率{sharpe:.2f}，良好"
    elif sharpe >= 0.5:
        s = 3
        r = f"夏普比率{sharpe:.2f}，一般"
    elif sharpe >= 0:
        s = 1
        r = f"夏普比率{sharpe:.2f}，较差"
    else:
        s = 0
        r = f"夏普比率{sharpe:.2f}，很差"
    scores.append(s)
    details["sharpe"] = s

    # 3.2 最大回撤 (5分)
    drawdown = risk_metrics.get("estimated_max_drawdown", 0) or 0
    if drawdown < 10:
        s = 5
        r = f"回撤{drawdown:.1f}%，控制良好"
    elif drawdown < 20:
        s = 3
        r = f"回撤{drawdown:.1f}%，控制一般"
    elif drawdown < 30:
        s = 1
        r = f"回撤{drawdown:.1f}%，波动较大"
    else:
        s = 0
        r = f"回撤{drawdown:.1f}%，风险较高"
    scores.append(s)
    details["drawdown"] = s

    # 3.3 波动率 (4分)
    volatility = risk_metrics.get("volatility", 0) or 0
    if volatility < 10:
        s = 4
        r = f"波动{volatility:.1f}%，较低"
    elif volatility < 20:
        s = 2
        r = f"波动{volatility:.1f}%，中等"
    else:
        s = 0
        r = f"波动{volatility:.1f}%，较高"
    scores.append(s)
    details["volatility"] = s

    total = min(15, sum(scores))
    return {"score": total, "reason": f"夏普{sharpe:.2f}，回撤{drawdown:.1f}%", "details": details}
