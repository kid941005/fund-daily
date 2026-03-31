"""
估值评分模块
"""



def calculate_valuation_score(fund_detail: dict, fund_data: dict = None) -> dict:
    """
    估值面评分 (满分25分)
    基于基金收益率、规模调整

    边界情况处理:
    - 数据缺失: 返回较低分
    """
    details = {}
    scores = []

    # 检查数据是否存在
    has_data = (
        fund_data and any(fund_data.get(f"return_{t}") is not None for t in ["1m", "3m", "6m", "1y"])
        if fund_data
        else False
    )

    if not has_data:
        return {
            "score": 5,  # 较低的基础分
            "reason": "数据获取失败",
            "details": {"return_1y_score": 1, "return_3m_score": 1},
        }

    # 1.1 近1年收益评分 (15分) - 基于实际收益率
    return_1y = 0
    if fund_data and fund_data.get("return_1y"):
        return_1y = float(fund_data.get("return_1y", 0) or 0)

    if return_1y > 50:
        s = 15
        r = f"近1年收益{return_1y:.1f}%，顶尖"
    elif return_1y > 30:
        s = 12
        r = f"近1年收益{return_1y:.1f}%，优秀"
    elif return_1y > 15:
        s = 10
        r = f"近1年收益{return_1y:.1f}%，良好"
    elif return_1y > 5:
        s = 7
        r = f"近1年收益{return_1y:.1f}%，一般"
    elif return_1y > 0:
        s = 4
        r = f"近1年收益{return_1y:.1f}%，较小"
    else:
        s = 1
        r = f"近1年收益{return_1y:.1f}%"
    scores.append(s)
    details["return_1y_score"] = s
    details["return_1y_reason"] = r

    # 1.2 近3月收益评分 (10分)
    return_3m = 0
    if fund_data and fund_data.get("return_3m"):
        return_3m = float(fund_data.get("return_3m", 0) or 0)

    if return_3m > 20:
        s = 10
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 10:
        s = 8
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 5:
        s = 5
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 0:
        s = 3
        r = f"近3月{return_3m:.1f}%"
    else:
        s = 1
        r = f"近3月{return_3m:.1f}%"
    scores.append(s)
    details["return_3m_score"] = s
    details["return_3m_reason"] = r

    total = min(25, sum(scores))
    return {"score": total, "reason": "基于收益率表现", "details": details}
