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
    
    # 第一步：识别需要卖出的低评分基金
    sell_funds = []
    hold_funds = []
    buy_candidates = []
    
    for item in scored:
        score = item["score"]
        
        if score < ST["VERY_LOW"]:  # < 40分
            # 低评分 - 卖出
            item["action"] = "卖出"
            item["target_amount"] = 0
            item["target_pct"] = 0
            sell_funds.append(item)
        elif score < ST["ACTIVE"]:  # 40-55分
            # 中低评分 - 持有
            item["action"] = "持有"
            item["target_amount"] = item["amount"]
            item["target_pct"] = item["pct"]
            hold_funds.append(item)
        else:  # ≥ 55分
            # 高评分 - 持有（可能增持）
            item["action"] = "持有"
            item["target_amount"] = item["amount"]
            item["target_pct"] = item["pct"]
            buy_candidates.append(item)
    
    # 计算卖出总金额
    sell_amount = sum(item["amount"] for item in sell_funds)
    
    # 第二步：将卖出金额分配给高评分基金
    conversion_suggestions = []
    if sell_amount > 0 and buy_candidates:
        # 按评分排序，优先分配给最高分的基金
        buy_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # 计算当前高评分基金总金额
        current_high_total = sum(item["amount"] for item in buy_candidates)
        
        # 将卖出金额按比例分配
        remaining_sell_amount = sell_amount
        for item in buy_candidates:
            if remaining_sell_amount <= 0:
                break
            
            # 按当前占比分配
            ratio = item["amount"] / current_high_total if current_high_total > 0 else 1.0 / len(buy_candidates)
            add_amount = remaining_sell_amount * ratio
            item["target_amount"] += add_amount
            item["target_pct"] = item["target_amount"] / total_amount * 100
            
            # 记录转换建议
            if add_amount > 10:  # 只有增持金额大于10元才记录
                conversion_suggestions.append({
                    "fund_code": item["fund"].get("fund_code", ""),
                    "fund_name": item["fund"].get("fund_name", ""),
                    "score": item["score"],
                    "add_amount": round(add_amount, 2),
                    "new_pct": round(item["target_pct"], 1)
                })
            
            remaining_sell_amount -= add_amount
    
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
                "reason": f"评分{item['score']}分（低评分），建议卖出"
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
                "reason": f"评分{item['score']}分（高评分），建议增持"
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
                "reason": f"评分{item['score']}分，建议持有"
            })
    
    # 第四步：生成转换建议
    conversion_advice = []
    if sell_funds and conversion_suggestions:
        # 汇总卖出基金
        sell_summary = []
        for item in sell_funds:
            sell_summary.append({
                "fund_code": item["fund"].get("fund_code", ""),
                "fund_name": item["fund"].get("fund_name", ""),
                "score": item["score"],
                "amount": round(item["amount"], 2)
            })
        
        # 汇总买入基金
        buy_summary = []
        for suggestion in conversion_suggestions:
            buy_summary.append({
                "fund_code": suggestion["fund_code"],
                "fund_name": suggestion["fund_name"],
                "score": suggestion["score"],
                "add_amount": suggestion["add_amount"]
            })
        
        # 生成转换建议文本
        conversion_advice.append(f"建议卖出{len(sell_funds)}只低评分基金（<40分），总金额{round(sell_amount, 2)}元")
        conversion_advice.append(f"将资金转换到{len(buy_summary)}只高评分基金（≥55分）")
        
        if sell_summary:
            conversion_advice.append("卖出基金：")
            for sell in sell_summary:
                conversion_advice.append(f"  • {sell['fund_name']}({sell['fund_code']}) - 评分{sell['score']}分，金额{sell['amount']}元")
        
        if buy_summary:
            conversion_advice.append("增持基金：")
            for buy in buy_summary:
                conversion_advice.append(f"  • {buy['fund_name']}({buy['fund_code']}) - 评分{buy['score']}分，增持{buy['add_amount']}元")
    
    # 统计
    summary = {
        "buy_count": len([t for t in trades if t["action"] == "买入"]),
        "sell_count": len([t for t in trades if t["action"] == "卖出"]),
        "hold_count": len([t for t in trades if t["action"] == "持有"]),
        "sell_amount": round(sell_amount, 2),
        "conversion_advice": conversion_advice
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
