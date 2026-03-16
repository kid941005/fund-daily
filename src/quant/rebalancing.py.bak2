"""
自动调仓模块
基于评分和组合优化生成调仓建议
"""
import logging
from typing import Dict, List
from datetime import datetime
from src.constants import ST
logger = logging.getLogger(__name__)
def calculate_rebalancing(funds: List[Dict], total_amount: float) -> Dict:
    """计算调仓建议 - 去弱留强，总金额不变"""
    if not funds or total_amount <= 0:
        return {"error": "无持仓数据"}
    
    # 为每只基金计算评分和当前占比
    scored = []
    for f in funds:
        score = f.get("score_100", {}).get("total_score", 0)
        amount = f.get("amount", 0)
        pct = amount / total_amount * 100 if total_amount > 0 else 0
        scored.append({
            "fund": f, 
            "score": score, 
            "amount": amount, 
            "pct": pct,
            "action": "持有"
        })
    
    # 按评分排序
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    # 第一步：计算卖出总金额
    sell_amount = 0
    for item in scored:
        score = item["score"]
        amount = item["amount"]
        
        if score < ST["LOW"]:
            # 低分 - 卖出
            item["action"] = "卖出"
            item["target_amount"] = 0
            item["target_pct"] = 0
            sell_amount += amount
        elif score < ST["ACTIVE"]:
            # 中低分 - 持有
            item["action"] = "持有"
            item["target_amount"] = amount
            item["target_pct"] = item["pct"]
        else:
            # 高分 - 持有（待增持）
            item["action"] = "持有"
            item["target_amount"] = amount
            item["target_pct"] = item["pct"]
    
    # 第二步：将卖出金额分配给高分基金（保持总金额不变）
    if sell_amount > 0:
        # 高分基金列表
        high_score_funds = [item for item in scored if item["score"] >= ST["HIGH"]]
        
        if high_score_funds:
            # 按评分排序，优先分配给高分基金
            high_score_funds.sort(key=lambda x: x["score"], reverse=True)
            
            # 计算当前高分基金总金额
            current_high_total = sum(item["amount"] for item in high_score_funds)
            
            # 将卖出金额按比例分配
            for item in high_score_funds:
                if sell_amount <= 0:
                    break
                # 按当前占比分配
                ratio = item["amount"] / current_high_total if current_high_total > 0 else 0
                add_amount = sell_amount * ratio
                item["target_amount"] += add_amount
                item["target_pct"] = item["target_amount"] / total_amount * 100
    
    # 第三步：生成交易清单
    trades = []
    for item in scored:
        fund = item["fund"]
        action = item["action"]
        current_amount = item["amount"]
        target_amount = item["target_amount"]
        
        # 记录所有卖出
        if action == "卖出" and current_amount > 0:
            trades.append({
                "fund_code": fund.get("fund_code", ""),
                "fund_name": fund.get("fund_name", ""),
                "score": item["score"],
                "action": action,
                "current_amount": round(current_amount, 2),
                "current_pct": round(item["pct"], 1),
                "target_amount": 0,
                "target_pct": 0,
                "reason": f"评分{item['score']}分，{action}"
            })
        # 记录增持的基金
        elif target_amount > current_amount + 10:
            trades.append({
                "fund_code": fund.get("fund_code", ""),
                "fund_name": fund.get("fund_name", ""),
                "score": item["score"],
                "action": "买入",
                "current_amount": round(current_amount, 2),
                "current_pct": round(item["pct"], 1),
                "target_amount": round(target_amount, 2),
                "target_pct": round(item["target_pct"], 1),
                "reason": f"评分{item['score']}分，买入"
            })
        # 记录不变的
        elif action == "持有":
            trades.append({
                "fund_code": fund.get("fund_code", ""),
                "fund_name": fund.get("fund_name", ""),
                "score": item["score"],
                "action": action,
                "current_amount": round(current_amount, 2),
                "current_pct": round(item["pct"], 1),
                "target_amount": round(target_amount, 2),
                "target_pct": round(item["target_pct"], 1),
                "reason": f"评分{item['score']}分，持有"
            })
    
    # 统计
    summary = {
        "buy_count": len([t for t in trades if t["action"] == "买入"]),
        "sell_count": len([t for t in trades if t["action"] == "卖出"]),
        "hold_count": len([t for t in trades if t["action"] == "持有"]),
        "sell_amount": round(sell_amount, 2),
    }
    
    return {
        "total_amount": round(total_amount, 2),
        "fund_count": len(scored),
        "trades": trades,
        "summary": summary,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
def generate_trade_orders(rebalancing: Dict) -> List[Dict]:
    """生成具体的交易订单"""
    trades = rebalancing.get("trades", [])
    orders = []
    
    for trade in trades:
        if trade["action"] == "持有":
            continue
            
        orders.append({
            "fund_code": trade["fund_code"],
            "fund_name": trade["fund_name"],
            "action": trade["action"],
            "amount": trade.get("trade_amount"),
            "priority": "高" if trade["score"] < 40 or trade["score"] >= 70 else "中",
            "reason": trade["reason"]
        })
    
    return orders
