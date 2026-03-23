"""
自动调仓模块
基于评分和组合优化生成调仓建议
去弱留强策略：
  评分 < 30   → 清仓 (0%)
  评分 30-50 → 降至一半（上限20%）
  评分 50-60 → 维持当前仓位
  评分 60-70 → 增仓至1.5倍
  评分 >= 70  → 增仓至2倍
"""
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_rebalancing(funds: List[Dict], total_amount: float) -> Dict:
    """计算调仓建议 - 去弱留强，总金额不变"""
    if not funds or total_amount <= 0:
        return {"error": "无持仓数据"}

    # 计算每只基金的评分和当前占比
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

    # 第一步：计算目标仓位
    for item in scored:
        score = item["score"]
        current_pct = item["pct"]

        if score < 30:
            # 清仓
            item["action"] = "卖出"
            item["target_pct"] = 0
        elif score < 50:
            # 降至一半（上限20%）
            target_pct = current_pct * 0.5
            item["action"] = "卖出" if target_pct < current_pct else "持有"
            item["target_pct"] = min(target_pct, 20)  # 上限20%
        elif score < 60:
            # 维持
            item["action"] = "持有"
            item["target_pct"] = current_pct
        elif score < 70:
            # 增仓至1.5倍
            target_pct = current_pct * 1.5
            item["action"] = "买入"
            item["target_pct"] = target_pct
        else:
            # 增仓至2倍
            target_pct = current_pct * 2.0
            item["action"] = "买入"
            item["target_pct"] = target_pct

    # 第二步：归一化（确保总仓位为100%）
    total_target_pct = sum(item["target_pct"] for item in scored)
    if total_target_pct > 0:
        for item in scored:
            item["target_pct"] = item["target_pct"] / total_target_pct * 100

    # 第三步：计算目标金额
    for item in scored:
        item["target_amount"] = item["target_pct"] / 100 * total_amount

    # 第四步：生成交易清单
    trades = []
    for item in scored:
        fund = item["fund"]
        action = item["action"]
        current_amount = item["amount"]
        target_amount = item["target_amount"]

        if action == "卖出" and current_amount > 0:
            trades.append({
                "fund_code": fund.get("fund_code", ""),
                "fund_name": fund.get("fund_name", ""),
                "score": item["score"],
                "action": action,
                "current_amount": round(current_amount, 2),
                "current_pct": round(item["pct"], 1),
                "target_amount": round(target_amount, 2),
                "target_pct": round(item["target_pct"], 1),
                "reason": f"评分{item['score']}分（<30分），建议清仓"
            })
        elif action == "买入" and target_amount > current_amount:
            trades.append({
                "fund_code": fund.get("fund_code", ""),
                "fund_name": fund.get("fund_name", ""),
                "score": item["score"],
                "action": action,
                "current_amount": round(current_amount, 2),
                "current_pct": round(item["pct"], 1),
                "target_amount": round(target_amount, 2),
                "target_pct": round(item["target_pct"], 1),
                "reason": f"评分{item['score']}分（>=60分），建议增持"
            })
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
                "reason": f"评分{item['score']}分（30-60分），建议持有"
            })

    # 统计
    sell_items = [item for item in scored if item["action"] == "卖出"]
    buy_items = [item for item in scored if item["action"] == "买入"]
    sell_amount = sum(item["amount"] - item["target_amount"] for item in sell_items)
    buy_amount = sum(item["target_amount"] - item["amount"] for item in buy_items)

    summary = {
        "buy_count": len(buy_items),
        "sell_count": len(sell_items),
        "hold_count": len([t for t in trades if t["action"] == "持有"]),
        "sell_amount": round(sell_amount, 2),
        "buy_amount": round(buy_amount, 2)
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
        action = trade.get("action", "")
        current = trade.get("current_amount", 0)
        target = trade.get("target_amount", 0)

        if action == "卖出":
            orders.append({
                "fund_code": trade["fund_code"],
                "fund_name": trade["fund_name"],
                "action": "卖出",
                "amount": round(current - target, 2),
                "reason": trade.get("reason", "")
            })
        elif action == "买入":
            orders.append({
                "fund_code": trade["fund_code"],
                "fund_name": trade["fund_name"],
                "action": "买入",
                "amount": round(target - current, 2),
                "reason": trade.get("reason", "")
            })

    return orders
