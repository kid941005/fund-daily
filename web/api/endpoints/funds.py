"""
Funds API endpoints
"""

from flask import Blueprint, jsonify, request, session
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import database_pg as db
from src.fetcher import fetch_fund_data, fetch_market_news, fetch_hot_sectors
from src.advice import analyze_fund, get_fund_detail_info, generate_100_score
from src.validation import validate_fund_code_param, validate_query_params, validate_limit
from src.jwt_auth import verify_access_token, get_token_from_header
from web.api.rate_limiter import funds_limit

funds_bp = Blueprint("funds", __name__)


def _get_user_id():
    """从 JWT token 或 session 获取用户ID"""
    token = get_token_from_header()
    if token:
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return _get_user_id()


@funds_bp.route("/funds")
@funds_limit()
def get_funds():
    """Get all funds for user
    
    Query params:
        force: if 'true', bypass cache and fetch fresh data
    """
    user_id = _get_user_id()
    holdings = db.get_holdings(user_id) if user_id else []
    
    # 检查是否强制刷新
    force_refresh = request.args.get("force", "false").lower() == "true"
    use_cache = not force_refresh
    
    codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
    if not codes:
        codes = ["000001", "110022", "161725"]
    
    # 并行获取基金数据
    def process_fund(code):
        data = fetch_fund_data(code, use_cache=use_cache)
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
    
    return jsonify({
        "success": True, 
        "funds": funds_data,
        "force_refresh": force_refresh
    })


@funds_bp.route("/fund-detail/<code>")
@funds_limit()
@validate_fund_code_param("code")
def get_fund_detail(code):
    """Get fund detail
    
    Query params:
        force: if 'true', bypass cache
    """
    force_refresh = request.args.get("force", "false").lower() == "true"
    use_cache = not force_refresh
    detail = get_fund_detail_info(code, use_cache=use_cache)
    return jsonify({"success": True, "detail": detail})


@funds_bp.route("/score/<code>")
@funds_limit()
@validate_fund_code_param("code")
def get_fund_score(code):
    """Get fund score report (100-point system)
    
    Query params:
        force: if 'true', bypass cache
    """
    force_refresh = request.args.get("force", "false").lower() == "true"
    use_cache = not force_refresh
    
    try:
        fund_data = fetch_fund_data(code, use_cache=use_cache)
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
