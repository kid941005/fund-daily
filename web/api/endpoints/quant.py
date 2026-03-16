"""
量化分析API端点
包含：择时信号、组合优化、自动调仓
"""

from flask import Blueprint, jsonify, request, session
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import database as db
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
    
    # 使用公共服务获取基金数据（自动缓存市场数据）
    from web.services.fund_service import get_funds_for_user
    from src.advice import analyze_fund
    
    funds = get_funds_for_user(holdings)
    
    # 为每只基金计算评分
    for fund in funds:
        from web.services.fund_service import calculate_fund_score
        scoring = calculate_fund_score(fund, fund.get("fund_code", ""))
        if scoring:
            fund["score_100"] = scoring
    
    total_amount = sum(h.get("amount", 0) for h in holdings)
    
    # 组合优化
    result = optimize_portfolio(funds)
    
    return jsonify({"success": True, "data": result})


@quant_bp.route("/rebalancing")
def get_rebalancing():
    """获取调仓建议 - 直接使用 advice API 的数据"""
    # 直接调用 advice API 获取完整数据
    from web.api.routes import get_advice
    from flask import make_response
    
    # 获取 advice 数据
    advice_result = get_advice()
    advice_data = advice_result.get_json()
    
    if not advice_data.get("success"):
        return jsonify({"success": False, "error": "获取建议失败"})
    
    funds = advice_data.get("advice", {}).get("funds", [])
    if not funds:
        return jsonify({"success": False, "error": "无基金数据"})
    
    # 计算总金额
    total_amount = sum(f.get("amount", 0) for f in funds)
    
    # 使用新的调仓逻辑
    result = calculate_rebalancing(funds, total_amount)
    
    return jsonify({"success": True, "data": result})
