"""
量化分析API端点
包含：择时信号、组合优化、自动调仓
"""

from flask import Blueprint, jsonify, request, session
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import database_pg as db
from src.quant import (
    get_timing_signals,
    optimize_portfolio,
    calculate_rebalancing,
    generate_trade_orders,
)

quant_bp = Blueprint("quant", __name__)


@quant_bp.route("/timing-signals")
def get_timing():
    """获取市场择时信号"""
    try:
        result = get_timing_signals([])
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@quant_bp.route("/portfolio-optimize")
def get_optimize():
    """获取组合优化建议"""
    user_id = session.get("user_id")
    
    # 获取持仓
    if user_id:
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h.get("amount", 0) > 0]
    else:
        return jsonify({"success": False, "error": "请先登录"})
    
    if not holdings:
        return jsonify({"success": False, "error": "无持仓数据"})
    
    # 使用新的FundService获取基金数据和评分（统一服务层）
    from src.services.fund_service import get_fund_service
    
    fund_service = get_fund_service(cache_enabled=True)
    
    # 计算持仓建议（包含基金数据和评分）
    advice_result = fund_service.calculate_holdings_advice(holdings)
    funds = advice_result.get("funds", [])
    
    # 确保每只基金都有score_100字段
    for fund in funds:
        if "score_100" not in fund:
            fund["score_100"] = {
                "total_score": 0,
                "grade": "E",
                "details": {},
                "error": "评分数据缺失"
            }
    
    total_amount = sum(h.get("amount", 0) for h in holdings)
    
    # 组合优化
    result = optimize_portfolio(funds)
    
    return jsonify({"success": True, "data": result})


@quant_bp.route("/rebalancing")
def get_rebalancing():
    """获取调仓建议"""
    from flask import session
    from db import database_pg as db
    from src.services.fund_service import FundService
    
    user_id = session.get("user_id")
    
    # 如果没有用户ID，尝试获取所有持仓
    if not user_id:
        try:
            # 获取所有持仓
            pool = db.get_pool()
            conn = pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT code, name, amount FROM holdings WHERE amount > 0")
            holdings = []
            for row in cursor.fetchall():
                holdings.append({
                    "code": row[0],
                    "name": row[1] or f"基金{row[0]}",
                    "amount": float(row[2])
                })
            cursor.close()
            pool.putconn(conn)
        except Exception as e:
            print(f"[DEBUG] 获取所有持仓失败: {e}")
            holdings = []
    else:
        # 获取用户持仓
        holdings = db.get_holdings(user_id)
    
    if not holdings:
        return jsonify({"success": False, "error": "无持仓数据"})
    
    try:
        # 生成建议
        fund_service = FundService()
        result = fund_service.calculate_holdings_advice(holdings)
        
        funds = result.get("funds", [])
        if not funds:
            # 如果没有基金数据，使用持仓数据
            funds = []
            for holding in holdings:
                funds.append({
                    "fund_code": holding.get("code"),
                    "fund_name": holding.get("name", f"基金{holding.get('code')}"),
                    "amount": holding.get("amount", 0),
                    "score_100": {"total_score": 50}  # 默认评分
                })
        
        # 计算总金额
        total_amount = sum(f.get("amount", 0) for f in funds)
        
        # 使用调仓逻辑
        rebalancing_result = calculate_rebalancing(funds, total_amount)
        
        return jsonify({"success": True, "data": rebalancing_result})
    except Exception as e:
        import logging
        logging.error(f"Rebalancing error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@quant_bp.route("/dynamic-weights", methods=["GET"])
def get_dynamic_weights_api():
    """获取动态权重信息"""
    try:
        from src.quant import get_dynamic_weights, detect_market_cycle
        
        cycle = detect_market_cycle()
        weights = get_dynamic_weights()
        
        return jsonify({
            "success": True,
            "data": {
                "market_cycle": weights.get("cycle", "未知"),
                "weights": {
                    "valuation": weights.get("valuation"),
                    "performance": weights.get("performance"),
                    "risk_control": weights.get("risk_control"),
                    "momentum": weights.get("momentum"),
                    "sentiment": weights.get("sentiment"),
                    "sector": weights.get("sector"),
                    "manager": weights.get("manager"),
                    "liquidity": weights.get("liquidity")
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
