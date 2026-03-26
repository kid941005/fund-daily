"""
基金经理评分模块
"""

import re
from typing import Dict, Optional


def calculate_manager_score(fund_manager: Optional[Dict]) -> Dict:
    """
    基金经理评分 (满分4分)
    """
    if not fund_manager:
        return {"score": 1, "reason": "无数据", "details": {}}

    star = fund_manager.get("star", 0) or 0
    work_time = fund_manager.get("workTime", "")

    # 解析任职年限
    years = 0
    match = re.search(r"(\d+)年", work_time)
    if match:
        years = int(match.group(1))

    if star >= 5 and years >= 5:
        score = 4
    elif star >= 4 and years >= 3:
        score = 3
    elif star >= 3 and years >= 1:
        score = 2
    else:
        score = 1

    return {"score": score, "reason": f"{star}星，{years}年", "details": {"star": star, "years": years}}
