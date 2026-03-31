"""
Quant Router
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.error import ErrorCode, create_error_response
from src.jwt_auth import verify_access_token
from src.services.quant_service import QuantServiceError, get_quant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quant", tags=["量化"])


def _get_user_id(request: Request) -> str | None:
    """Get user_id from JWT token or session"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return request.cookies.get("session")


def _auth_required(request: Request) -> str:
    """Require authentication"""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "请先登录", "need_login": True, "error_code": "UNAUTHORIZED"},
        )
    return user_id


quant_service = get_quant_service()


@router.get("/timing-signals")
async def get_timing_signals(request: Request):
    """Get timing signals"""
    _auth_required(request)

    try:
        data = quant_service.timing_signals()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Timing signals error: {e}")
        if isinstance(e, QuantServiceError):
            error_response, status_code = create_error_response(
                ErrorCode.INVALID_INPUT if "validation" in str(e).lower() else ErrorCode.INTERNAL_ERROR,
                message=str(e),
                http_status=500,
            )
        else:
            error_response, status_code = create_error_response(
                ErrorCode.INTERNAL_ERROR, message="获取择时信号失败", http_status=500
            )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/portfolio-optimize")
async def get_portfolio_optimize(request: Request):
    """Get portfolio optimization suggestions"""
    user_id = _auth_required(request)

    try:
        data = quant_service.optimize_portfolio(user_id)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Portfolio optimize error: {e}")
        if isinstance(e, QuantServiceError):
            error_response, status_code = create_error_response(
                ErrorCode.INVALID_INPUT if "validation" in str(e).lower() else ErrorCode.INTERNAL_ERROR,
                message=str(e),
                http_status=500,
            )
        else:
            error_response, status_code = create_error_response(
                ErrorCode.INTERNAL_ERROR, message="组合优化失败", http_status=500
            )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/rebalancing")
async def get_rebalancing(request: Request):
    """Get rebalancing suggestions"""
    user_id = _auth_required(request)

    try:
        data = quant_service.rebalancing(user_id)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Rebalancing error: {e}")
        if isinstance(e, QuantServiceError):
            error_response, status_code = create_error_response(
                ErrorCode.INVALID_INPUT if "validation" in str(e).lower() else ErrorCode.INTERNAL_ERROR,
                message=str(e),
                http_status=500,
            )
        else:
            error_response, status_code = create_error_response(
                ErrorCode.INTERNAL_ERROR, message="调仓建议生成失败", http_status=500
            )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/dynamic-weights")
async def get_dynamic_weights(request: Request):
    """Get dynamic weights"""
    _auth_required(request)

    try:
        data = quant_service.dynamic_weights()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Dynamic weights error: {e}")
        if isinstance(e, QuantServiceError):
            error_response, status_code = create_error_response(
                ErrorCode.INVALID_INPUT if "validation" in str(e).lower() else ErrorCode.INTERNAL_ERROR,
                message=str(e),
                http_status=500,
            )
        else:
            error_response, status_code = create_error_response(
                ErrorCode.INTERNAL_ERROR, message="动态权重获取失败", http_status=500
            )
        return JSONResponse(status_code=status_code, content=error_response)
