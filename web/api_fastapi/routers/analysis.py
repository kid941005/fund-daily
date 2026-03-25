"""
Analysis Router
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from db import database_pg as db
from src.jwt_auth import verify_access_token
from src.fetcher import fetch_fund_data
from src.analyzer import calculate_expected_return
from src.services.fund_service import get_fund_service
from src.error import ErrorCode, create_error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["分析"])


def _get_user_id(request: Request) -> Optional[str]:
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
            code=ErrorCode.UNAUTHORIZED,
            message="请先登录",
            http_status=401
        )
        return JSONResponse(status_code=status_code, content=error_response)
    
    holdings = db.get_holdings(user_id)
    holdings_dict = {h["code"]: h for h in holdings}
    
    try:
        # Use FundService to get holdings advice
        fund_service = get_fund_service(cache_enabled=True)
        advice_result = fund_service.calculate_holdings_advice(holdings)
        
        funds = advice_result.get("funds", [])
        total_amount = advice_result.get("total_amount", 0)
        
        # Build portfolio analysis
        if funds and total_amount > 0:
            risk_scores = []
            returns_1y = []
            
            for fund in funds:
                score_data = fund.get("score_100", {})
                risk_score = score_data.get("details", {}).get("risk_control", {}).get("score", 4)
                risk_scores.append(risk_score)
                
                fund_data = fund.get("fund_data", {})
                return_1y = float(fund_data.get("return_1y", 0) or 0)
                returns_1y.append(return_1y)
            
            weights = [fund.get("current_pct", 0) for fund in funds]
            if sum(weights) > 0:
                weighted_risk = sum(r * w for r, w in zip(risk_scores, weights)) / sum(weights)
                weighted_return = sum(r * w for r, w in zip(returns_1y, weights)) / sum(weights)
            else:
                weighted_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 4
                weighted_return = sum(returns_1y) / len(returns_1y) if returns_1y else 0
            
            # Determine risk level
            if weighted_risk > 6:
                risk_level = "高风险"
            elif weighted_risk > 4:
                risk_level = "中高风险"
            elif weighted_risk > 2:
                risk_level = "中等风险"
            else:
                risk_level = "中低风险"
            
            # Diversification assessment
            fund_count = len(funds)
            if fund_count >= 5:
                diversification = "良好"
            elif fund_count >= 3:
                diversification = "一般"
            else:
                diversification = "需分散"
            
            analysis = {
                "risk_level": risk_level,
                "risk_score": round(weighted_risk, 1),
                "avg_return_1y": round(weighted_return, 2),
                "fund_count": fund_count,
                "diversification": diversification,
                "total_amount": total_amount,
                "funds": funds,
                "message": "分析完成"
            }
        else:
            # No funds data, use basic holding info
            chart_funds = []
            for holding in holdings:
                chart_funds.append({
                    "fund_code": holding.get("code"),
                    "fund_name": holding.get("name") or f"基金{holding.get('code')}",
                    "amount": holding.get("amount", 0),
                    "score_100": {"total_score": 50}
                })
            
            analysis = {
                "risk_level": "未知",
                "risk_score": 0,
                "avg_return_1y": 0,
                "fund_count": len(holdings),
                "diversification": "无详细数据",
                "total_amount": sum(h.get("amount", 0) for h in holdings),
                "funds": chart_funds,
                "message": "使用持仓数据，基金详情待更新"
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
                "message": f"分析失败: {str(e)}"
            }
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
