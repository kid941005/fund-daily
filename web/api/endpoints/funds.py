"""
Funds API endpoints
"""

from flask import Blueprint, jsonify, request, session
from concurrent.futures import ThreadPoolExecutor, as_completed
from web.services import fund_service
from db import database as db
from src.fetcher import fetch_fund_data, fetch_market_news, fetch_hot_sectors
from src.advice import analyze_fund, get_fund_detail_info, generate_100_score

funds_bp = Blueprint("funds", __name__)


@funds_bp.route("/funds")
def get_funds():
    """Get all funds for user"""
    user_id = session.get("user_id")
    holdings = db.get_holdings(user_id) if user_id else []
    
    codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
    if not codes:
        codes = ["000001", "110022", "161725"]
    
    # 并行获取基金数据
    def process_fund(code):
        data = fetch_fund_data(code)
        if not data.get("error"):
            return analyze_fund(data)
        return None
    
    funds_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_fund, code): code for code in codes}
        for future in as_completed(futures):
            result = future.result()
            if result:
                funds_data.append(result)
    
    return jsonify({"success": True, "funds": funds_data})


@funds_bp.route("/fund-detail/<code>")
def get_fund_detail(code):
    """Get fund detail"""
    detail = get_fund_detail_info(code)
    return jsonify({"success": True, "detail": detail})


@funds_bp.route("/score/<code>")
def get_fund_score(code):
    """Get fund score report (100-point system)"""
    try:
        fund_data = fetch_fund_data(code)
        if fund_data.get("error"):
            return jsonify({"success": False, "error": fund_data.get("error", "获取数据失败")})
        
        daily_change = float(fund_data.get("gszzl", 0) or 0)
        scoring = generate_100_score(code, daily_change)
        
        if "error" in scoring:
            return jsonify({"success": False, "error": scoring.get("error", "计算评分失败")})
        
        return jsonify({
            "success": True,
            "fund_code": code,
            "fund_name": fund_data.get("name", ""),
            "daily_change": daily_change,
            "scoring": scoring
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
