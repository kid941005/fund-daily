"""
动量趋势评分模块
"""


def calculate_momentum_score(fund_data: dict = None) -> dict:
    """
    动量趋势评分 (满分15分)
    基于短期动量和趋势强度
    """
    details = {}
    scores = []

    if not fund_data:
        return {"score": 5, "reason": "无数据", "details": {}}

    # 4.1 短期动量 (8分)
    return_1m = float(fund_data.get("return_1m", 0) or 0)
    daily_change = float(fund_data.get("daily_change", 0) or 0)

    # 动量评分
    if return_1m > 10 and daily_change > 2:
        s = 8
        r = "强势上涨"
    elif return_1m > 5 and daily_change > 0:
        s = 6
        r = "温和上涨"
    elif return_1m > 0:
        s = 4
        r = "小幅上涨"
    elif return_1m > -5:
        s = 2
        r = "小幅下跌"
    elif return_1m > -10:
        s = 1
        r = "明显下跌"
    else:
        s = 0
        r = "大幅下跌"
    scores.append(s)
    details["momentum"] = s

    # 4.2 趋势强度 (7分)
    # 比较近1月和近3月
    return_3m = float(fund_data.get("return_3m", 0) or 0)
    if return_1m > 0 and return_3m > 0 and return_1m > return_3m / 3:
        s = 7
        r = "上升趋势强劲"
    elif return_1m > 0 and return_3m > 0:
        s = 5
        r = "上升趋势稳健"
    elif return_1m < 0 and return_3m < 0 and return_1m < return_3m / 3:
        s = 0
        r = "下降趋势加速"
    elif return_1m < 0 and return_3m < 0:
        s = 2
        r = "下降趋势"
    elif return_1m * return_3m < 0:
        s = 3
        r = "趋势震荡"
    else:
        s = 4
        r = "趋势不明"
    scores.append(s)
    details["trend"] = s

    total = min(15, sum(scores))
    return {"score": total, "reason": f"动量{r}，趋势{r}", "details": details}
