"""
业绩表现评分模块
"""


def calculate_performance_score(fund_data: dict = None) -> dict:
    """
    业绩表现评分 (满分20分)
    基于各时间段收益表现

    边界情况处理:
    - fund_data 为空或 None: 返回中等分
    - 收益数据缺失: 使用0或负向评分
    """
    details = {}
    scores = []

    if not fund_data:
        return {"score": 6, "reason": "无数据", "details": {}}

    # 检查收益数据是否存在（避免API返回None）
    has_return_data = any(fund_data.get(f"return_{t}") is not None for t in ["1m", "3m", "6m", "1y"])

    if not has_return_data:
        # 数据获取失败，返回较低分
        return {"score": 3, "reason": "收益数据获取失败", "details": {"return_3m": 0, "return_1m": 0, "stability": 0}}

    # 2.1 近3月表现 (8分)
    return_3m = float(fund_data.get("return_3m", 0) or 0)
    if return_3m > 30:
        s = 8
    elif return_3m > 15:
        s = 6
    elif return_3m > 5:
        s = 4
    elif return_3m > 0:
        s = 2
    else:
        s = 0
    scores.append(s)
    details["return_3m"] = s

    # 2.2 近1月表现 (6分)
    return_1m = float(fund_data.get("return_1m", 0) or 0)
    if return_1m > 10:
        s = 6
    elif return_1m > 5:
        s = 5
    elif return_1m > 0:
        s = 3
    elif return_1m > -5:
        s = 1
    else:
        s = 0
    scores.append(s)
    details["return_1m"] = s

    # 2.3 收益稳定性 (6分)
    # 比较近1月和近3月趋势
    if return_1m > 0 and return_3m > 0:
        s = 6  # 趋势一致向上
    elif return_1m > 0 and return_3m < 0:
        s = 4  # 短期反弹
    elif return_1m < 0 and return_3m > 0:
        s = 3  # 短期回调
    elif return_1m < 0 and return_3m < 0:
        s = 0  # 持续下跌
    else:
        s = 2
    scores.append(s)
    details["stability"] = s

    total = min(20, sum(scores))
    return {"score": total, "reason": f"近3月{return_3m:+.1f}%，近1月{return_1m:+.1f}%", "details": details}
