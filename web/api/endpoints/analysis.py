"""
Analysis API endpoints
"""

from flask import Blueprint, jsonify, request, session
from concurrent.futures import ThreadPoolExecutor, as_completed
from web.services import fund_service
from db import database as db

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/portfolio-analysis")
def get_portfolio_analysis():
    """Get portfolio analysis"""
    user_id = session.get("user_id")

    if user_id:
        holdings = db.get_holdings(user_id)
        holdings_dict = {h["code"]: h for h in holdings}
    else:
        holdings = []
        holdings_dict = {}

    analysis = fund_service.get_portfolio_analysis(holdings, holdings_dict)
    return jsonify({"success": True, "analysis": analysis})


@analysis_bp.route("/expected-return")
def get_expected_return():
    """Calculate expected return"""
    from src.fetcher import fetch_fund_data
    from src.analyzer import calculate_expected_return
    
    user_id = session.get("user_id")

    if user_id:
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h.get("amount", 0) > 0]
    else:
        holdings = []

    if not holdings:
        return jsonify({"success": False, "error": "暂无持仓", "expected_return": 0})

    codes = [h.get("code") for h in holdings]
    
    # 并行获取基金数据
    funds_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_fund_data, code): code for code in codes}
        for future in as_completed(futures):
            data = future.result()
            if not data.get("error"):
                funds_data.append(data)

    result = calculate_expected_return(holdings, funds_data)
    return jsonify({"success": True, "result": result})
