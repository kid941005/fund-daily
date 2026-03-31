"""
Analysis Router
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from db import database_pg as db
from src.analyzer import calculate_expected_return
from src.error import ErrorCode, create_error_response
from src.fetcher import fetch_fund_data
from src.jwt_auth import verify_access_token
from src.services.quant_service import get_quant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["分析"])


def _get_user_id(request: Request) -> str | None:
    """Get user_id from JWT token or session"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return request.cookies.get("session")


@router.get("/analysis/portfolio")
@router.get("/portfolio-analysis")
async def get_portfolio_analysis(request: Request):
    """Get portfolio analysis"""
    user_id = _get_user_id(request)

    if not user_id:
        error_response, status_code = create_error_response(
            code=ErrorCode.UNAUTHORIZED, message="请先登录", http_status=401
        )
        return JSONResponse(status_code=status_code, content=error_response)

    holdings = db.get_holdings(user_id)
    {h["code"]: h for h in holdings}

    try:
        # Use QuantService.optimize_portfolio for consistent scores with quant/portfolio-optimize
        quant_service = get_quant_service()
        optimize_result = quant_service.optimize_portfolio(user_id)
        allocations = optimize_result.get("allocations", [])

        if not allocations:
            return {"success": False, "error": "无持仓数据", "analysis": None}

        # Get holdings advice from cache for 8-dimension details
        holdings_advice = quant_service._holdings_advice_cache

        # Build funds with scores from optimize_portfolio (ensures consistency)
        funds = []
        holdings_map = {}
        if holdings_advice:
            for f in holdings_advice.get("funds", []):
                holdings_map[f.get("fund_code")] = f

        for a in allocations:
            fund_code = a.get("fund_code")
            holdings_fund = holdings_map.get(fund_code, {})
            score_100 = holdings_fund.get("score_100", {})

            fund = {
                "fund_code": fund_code,
                "fund_name": a.get("fund_name", holdings_fund.get("fund_name", f"基金{fund_code}")),
                "amount": holdings_fund.get("amount", 0),
                "current_pct": a.get("weight", 0),
                "score_100": {
                    "total_score": a.get("score", 0),
                    "base_score": score_100.get("base_score"),
                    "ranking_bonus": score_100.get("ranking_bonus"),
                    "details": score_100.get("details"),
                },
            }
            funds.append(fund)

        # Calculate risk metrics
        if holdings_advice:
            risk_level = holdings_advice.get("risk_level", "未知")
            risk_score = holdings_advice.get("risk_score", 0)
            avg_return_1y = holdings_advice.get("avg_return_1y", 0)
            diversification = holdings_advice.get("diversification", "一般")
            total_amount = holdings_advice.get("total_amount", 0)
        else:
            risk_level = "未知"
            risk_score = 0
            avg_return_1y = 0
            diversification = "一般"
            total_amount = sum(a.get("weight", 0) for a in allocations)

        analysis = {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 1),
            "avg_return_1y": round(avg_return_1y, 2),
            "fund_count": len(funds),
            "diversification": diversification,
            "total_amount": total_amount,
            "funds": funds,
            "message": "分析完成",
        }

        return {"success": True, "analysis": analysis}

    except Exception as e:
        logger.error(f"Portfolio analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis": {
                "risk_level": "未知",
                "risk_score": 0,
                "avg_return_1y": 0,
                "fund_count": 0,
                "diversification": "分析失败",
                "total_amount": 0,
                "message": f"分析失败: {str(e)}",
            },
        }


@router.get("/expected-return")
async def get_expected_return(request: Request):
    """Calculate expected return"""
    user_id = _get_user_id(request)

    if user_id:
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h.get("amount", 0) > 0]
    else:
        holdings = []

    if not holdings:
        return {"success": False, "error": "暂无持仓", "expected_return": 0}

    codes = [h.get("code") for h in holdings]

    # Fetch fund data in parallel
    funds_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_fund_data, code): code for code in codes}
        for future in as_completed(futures):
            data = future.result()
            if not data.get("error"):
                funds_data.append(data)

    result = calculate_expected_return(holdings, funds_data)
    return {"success": True, "result": result}
