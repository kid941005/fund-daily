"""
Funds API endpoints
"""

from flask import Blueprint, jsonify, request, session
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import database_pg as db
from src.fetcher import fetch_fund_data, fetch_market_news, fetch_hot_sectors
from src.advice import analyze_fund, get_fund_detail_info, generate_100_score
from web.api.validation import validate_fund_code_param, validate_query_params, validate_limit
from src.jwt_auth import verify_access_token, get_token_from_header
from src.error import ErrorCode, create_error_response
from web.api.rate_limiter import funds_limit

funds_bp = Blueprint("funds", __name__)


def _get_user_id():
    """从 JWT token 或 session 获取用户ID"""
    token = get_token_from_header()
    if token:
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    # 回退到 session
    return session.get("user_id")


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
    fund_codes = codes
    
    # 并行获取基金数据
    def process_fund(fund_code):
        data = fetch_fund_data(fund_code, use_cache=use_cache)
        if not data.get("error"):
            return analyze_fund(data)
        return None
    
    funds_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_fund, fund_code): fund_code for fund_code in fund_codes}
        for future in as_completed(futures):
            result = future.result()
            if result:
                funds_data.append(result)
    
    return jsonify({
        "success": True, 
        "funds": funds_data,
        "force_refresh": force_refresh
    })


@funds_bp.route("/fund-detail/<fund_code>")
@funds_limit()
@validate_fund_code_param("fund_code")
def get_fund_detail(fund_code):
    """Get fund detail
    
    Query params:
        force: if 'true', bypass cache
    """
    force_refresh = request.args.get("force", "false").lower() == "true"
    use_cache = not force_refresh
    detail = get_fund_detail_info(fund_code, use_cache=use_cache)
    return jsonify({"success": True, "detail": detail})


@funds_bp.route("/score/<fund_code>")
@funds_limit()
@validate_fund_code_param("fund_code")
def get_fund_score(fund_code):
    """Get fund score report (100-point system)
    
    Query params:
        force: if 'true', bypass cache
    """
    force_refresh = request.args.get("force", "false").lower() == "true"
    use_cache = not force_refresh
    
    try:
        fund_data = fetch_fund_data(fund_code, use_cache=use_cache)
        if fund_data.get("error"):
            return create_error_response(
                ErrorCode.FUND_DATA_FETCH_FAILED,
                fund_data.get("error", "获取基金数据失败"),
                details={"fund_code": fund_code},
                http_status=500
            )
        
        daily_change = float(fund_data.get("estimated_change", 0) or fund_data.get("gszzl", 0) or 0)
        scoring = generate_100_score(fund_code, daily_change)
        
        if "error" in scoring:
            return create_error_response(
                ErrorCode.FUND_SCORE_CALCULATION_FAILED,
                scoring.get("error", "计算基金评分失败"),
                details={"fund_code": fund_code},
                http_status=500
            )
        
        return jsonify({
            "success": True,
            "fund_code": fund_code,
            "fund_name": fund_data.get("name", ""),
            "daily_change": daily_change,
            "scoring": scoring
        })
    except Exception as e:
        return create_error_response(
            ErrorCode.FUND_SCORE_CALCULATION_FAILED,
            f"基金评分计算异常: {str(e)}",
            details={"fund_code": fund_code},
            http_status=500
        )
