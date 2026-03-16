"""
自动调仓模块
基于评分和组合优化生成调仓建议
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# 评分阈值配置 - 去弱留强
SCORE_THRESHOLDS = {
    "VERY_LOW": 40,   # 低于40分，清仓
    "LOW": 45,       # 低于45分，卖出
    "ACTIVE": 50,     # 低于50分，持有
    "HIGH": 50,       # 高于50分，买入
}

# 持仓比例配置 - 去弱留强
ALLOCATION_RATIOS = {
    "VERY_LOW": 0.0,    # 清仓
    "LOW": 0.0,        # 卖出
    "NORMAL": 1.0,      # 正常持有
    "HIGH": 1.5,        # 超配50%
}


def calculate_rebalancing(funds: List[Dict], total_amount: float) -> Dict:
    """计算调仓建议（简化版）"""
    if not funds or total_amount <= 0:
        return {"error": "无持仓数据"}
    
    # 排序
    scored = []
    for f in funds:
        score = f.get("score_100", {}).get("total_score", 0)
        amount = f.get("amount", 0)
        pct = amount / total_amount * 100 if total_amount > 0 else 0
        scored.append({"fund": f, "score": score, "amount": amount, "pct": pct})
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    trades = []
    for item in scored:
        fund = item["fund"]
        score = item["score"]
        amount = item["amount"]
        pct = item["pct"]
        
        # 根据分数决定操作 - 去弱留强
        if score >= SCORE_THRESHOLDS["HIGH"]:
            action = "买入"
            target_pct = min(pct * 1.5, 50)
        elif score >= SCORE_THRESHOLDS["ACTIVE"]:
            action = "持有"
            target_pct = pct
        elif score >= SCORE_THRESHOLDS["LOW"]:
            action = "卖出"
            target_pct = 0  # 卖出
        else:
            action = "清仓"
            target_pct = 0  # 完全清仓
        
        target_amount = total_amount * target_pct / 100
        
        # 有差异就添加
        if abs(target_amount - amount) > 10 or action == "清仓":
            trades.append({
                "fund_code": fund.get("fund_code", ""),
                "fund_name": fund.get("fund_name", ""),
                "score": score,
                "action": action,
                "current_amount": round(amount, 2),
                "current_pct": round(pct, 1),
                "target_amount": round(target_amount, 2),
                "target_pct": round(target_pct, 1),
                "reason": f"评分{score}分，{action}"
            })
    
    # 统计
    summary = {
        "buy_count": len([t for t in trades if t["action"] == "买入"]),
        "sell_count": len([t for t in trades if t["action"] in ["卖出", "清仓"]]),
        "hold_count": len([t for t in trades if t["action"] == "持有"]),
    }
    
    return {
        "total_amount": round(total_amount, 2),
        "fund_count": len(scored),
        "trades": trades,
        "summary": summary,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
def generate_trade_orders(rebalancing: Dict) -> List[Dict]:
    """
    生成具体的交易订单
    
    Args:
        rebalancing: 调仓建议
    
    Returns:
        list: 交易订单列表
    """
    trades = rebalancing.get("trades", [])
    orders = []
    
    for trade in trades:
        if trade["action"] == "持有":
            continue
            
        orders.append({
            "fund_code": trade["fund_code"],
            "fund_name": trade["fund_name"],
            "action": trade["action"],
            "amount": trade["trade_amount"],
            "priority": "高" if trade["score"] < 40 or trade["score"] >= 70 else "中",
            "reason": trade["reason"]
        })
    
    return orders
