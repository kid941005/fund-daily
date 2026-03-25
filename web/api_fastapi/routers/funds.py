"""
Funds Router
"""

import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db import database_pg as db
from src.fetcher import fetch_fund_data, fetch_market_news, fetch_hot_sectors
from src.advice import analyze_fund, get_fund_detail_info, generate_100_score
from src.error import ErrorCode, create_error_response
from src.jwt_auth import verify_access_token, create_token_pair
from web.api_fastapi.middleware.rate_limiter import check_rate_limit
from web.api_fastapi.deps import get_current_user, AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["基金"])


def _get_user_id(request: Request) -> Optional[str]:
    """Get user_id from JWT token or session"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    
    # Fallback to session
    return request.cookies.get("session")


def _validate_fund_code(code: str) -> str:
    """Validate fund code format"""
    code = code.strip()
    if not re.match(r'^\d{6}[A-Z]*$', code):
        raise ValueError("基金代码格式错误，应为6位数字加可选字母后缀")
    return code


@router.get("/funds")
async def get_funds(request: Request, force: str = Query("false")):
    """Get all funds for user"""
    # Check rate limit
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})
    
    user_id = _get_user_id(request)
    holdings = db.get_holdings(user_id) if user_id else []
    
    # Check force refresh
    use_cache = force.lower() != "true"
    
    codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
    if not codes:
        codes = ["000001", "110022", "161725"]
    
    def process_fund(fund_code):
        data = fetch_fund_data(fund_code, use_cache=use_cache)
        if not data.get("error"):
            return analyze_fund(data, use_cache=use_cache)
        return None
    
    funds_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_fund, code): code for code in codes}
        for future in as_completed(futures):
            result = future.result()
            if result:
                funds_data.append(result)
    
    return {
        "success": True,
        "funds": funds_data,
        "force_refresh": force.lower() == "true"
    }


@router.get("/fund-detail/{fund_code}")
async def get_fund_detail(request: Request, fund_code: str, force: str = Query("false")):
    """Get fund detail"""
    # Check rate limit
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})
    
    # Validate fund code
    try:
        fund_code = _validate_fund_code(fund_code)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )
    
    use_cache = force.lower() != "true"
    detail = get_fund_detail_info(fund_code, use_cache=use_cache)
    return {"success": True, "detail": detail}


@router.get("/score/{fund_code}")
async def get_fund_score(request: Request, fund_code: str, force: str = Query("false")):
    """Get fund score report (100-point system)"""
    # Check rate limit
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})
    
    # Validate fund code
    try:
        fund_code = _validate_fund_code(fund_code)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )
    
    use_cache = force.lower() != "true"
    
    try:
        fund_data = fetch_fund_data(fund_code, use_cache=use_cache)
        if fund_data.get("error"):
            error_response, status_code = create_error_response(
                ErrorCode.FUND_DATA_FETCH_FAILED,
                fund_data.get("error", "获取基金数据失败"),
                details={"fund_code": fund_code},
                http_status=500
            )
            return JSONResponse(status_code=status_code, content=error_response)
        
        daily_change = float(fund_data.get("estimated_change", 0) or fund_data.get("gszzl", 0) or 0)
        scoring = generate_100_score(fund_code, daily_change, use_cache=use_cache)
        
        if "error" in scoring:
            error_response, status_code = create_error_response(
                ErrorCode.FUND_SCORE_CALCULATION_FAILED,
                scoring.get("error", "计算基金评分失败"),
                details={"fund_code": fund_code},
                http_status=500
            )
            return JSONResponse(status_code=status_code, content=error_response)
        
        return {
            "success": True,
            "fund_code": fund_code,
            "fund_name": fund_data.get("name", ""),
            "daily_change": daily_change,
            "scoring": scoring
        }
    except Exception as e:
        error_response, status_code = create_error_response(
            ErrorCode.FUND_SCORE_CALCULATION_FAILED,
            f"基金评分计算异常: {str(e)}",
            details={"fund_code": fund_code},
            http_status=500
        )
        return JSONResponse(status_code=status_code, content=error_response)
