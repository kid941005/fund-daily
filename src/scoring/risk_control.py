"""
风险控制评分模块
"""



def calculate_risk_control_score(risk_metrics: dict, fund_data: dict = None) -> dict:
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
    elif sharpe >= 1.0:
        s = 5
    elif sharpe >= 0.5:
        s = 3
    elif sharpe >= 0:
        s = 1
    else:
        s = 0
    scores.append(s)
    details["sharpe"] = s

    # 3.2 最大回撤 (5分)
    drawdown = risk_metrics.get("estimated_max_drawdown", 0) or 0
    if drawdown < 10:
        s = 5
    elif drawdown < 20:
        s = 3
    elif drawdown < 30:
        s = 1
    else:
        s = 0
    scores.append(s)
    details["drawdown"] = s

    # 3.3 波动率 (4分)
    volatility = risk_metrics.get("volatility", 0) or 0
    if volatility < 10:
        s = 4
    elif volatility < 20:
        s = 2
    else:
        s = 0
    scores.append(s)
    details["volatility"] = s

    total = min(15, sum(scores))
    return {"score": total, "reason": f"夏普{sharpe:.2f}，回撤{drawdown:.1f}%", "details": details}
