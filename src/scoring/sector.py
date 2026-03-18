"""
板块景气评分模块
"""

from typing import Dict, List, Optional


def calculate_sector_score(fund_type: str, hot_sectors: List[Dict], commodity_sentiment: str, fund_data: Dict = None) -> Dict:
    """
    板块景气评分 (满分8分)
    """
    details = {}
    scores = []
    
    # 6.1 大宗商品环境 (4分)
    if commodity_sentiment in ["乐观", "偏多"]:
        s = 4
        r = "商品景气高"
    elif commodity_sentiment == "平稳":
        s = 2
        r = "商品平稳"
    else:
        s = 1
        r = "商品低迷"
    scores.append(s)
    details["commodity"] = s
    
    # 6.2 行业匹配 (4分)
    hot_names = [s.get("name", "").lower() for s in hot_sectors[:5]]
    fund_type_lower = fund_type.lower() if fund_type else ""
    
    matched = False
    for name in hot_names:
        if name in fund_type_lower or fund_type_lower in name:
            s = 4
            r = f"属于热门板块{name}"
            matched = True
            break
    
    if not matched:
        s = 2
        r = "行业一般"
    scores.append(s)
    details["sector_match"] = s
    
    total = min(8, sum(scores))
    return {
        "score": total,
        "reason": r,
        "details": details
    }