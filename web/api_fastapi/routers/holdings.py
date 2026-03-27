"""
Holdings Router
"""

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from db import database_pg as db
from src.error import ErrorCode, create_error_response
from src.jwt_auth import verify_access_token
from web.api_fastapi.middleware.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["持仓"])


def _get_user_id(request: Request) -> Optional[str]:
    """Get user_id from JWT token or session"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return request.cookies.get("session")


def _auth_required(request: Request) -> str:
    """Require authentication, return user_id"""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "请先登录", "need_login": True, "error_code": "UNAUTHORIZED"},
        )
    return user_id


def _validate_fund_code(code: str) -> str:
    """Validate fund code format"""
    code = code.strip()
    if not re.match(r"^\d{6}[A-Z]*$", code):
        raise ValueError("基金代码格式错误，应为6位数字加可选字母后缀")
    return code


# Request Models
class HoldingItem(BaseModel):
    code: Optional[str] = Field(default=None, max_length=20)
    fund_code: Optional[str] = Field(default=None, max_length=20)
    amount: float = Field(default=0, ge=0, le=1000000000)  # 最大10亿
    cost_basis: Optional[float] = Field(default=None, ge=0)
    purchase_date: Optional[str] = Field(default=None, max_length=20)


class BatchHoldingsRequest(BaseModel):
    funds: List[HoldingItem] = Field(..., min_length=1, max_length=100)
    action: Optional[str] = Field(default="add", max_length=20)


class SingleHoldingRequest(BaseModel):
    code: Optional[str] = None
    fund_code: Optional[str] = None
    amount: float = 0


@router.get("/holdings")
async def get_holdings(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """Get user holdings with pagination"""
    # Check rate limit
    limit_result = check_rate_limit(request, "holdings")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    user_id = _auth_required(request)
    holdings = db.get_holdings(user_id)

    # 分页
    total = len(holdings)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = holdings[start:end]

    return {
        "success": True,
        "holdings": paginated,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("/holdings")
async def manage_holdings(request: Request, data: BatchHoldingsRequest):
    """Add/update holdings"""
    # Check rate limit
    limit_result = check_rate_limit(request, "holdings")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    user_id = _auth_required(request)

    action = data.action or "add"

    if action == "delete":
        fund_code = data.funds[0].code if data.funds else None
        fund_code = fund_code or data.funds[0].fund_code if data.funds else None
        if fund_code:
            try:
                fund_code = _validate_fund_code(fund_code)
                db.delete_holding(user_id, fund_code)
            except ValueError as e:
                error_response, status_code = create_error_response(
                    ErrorCode.INVALID_INPUT, f"输入验证失败: {str(e)}", http_status=400
                )
                return JSONResponse(status_code=status_code, content=error_response)
        return {"success": True, "message": "删除成功"}

    # Add/update holdings
    for fund in data.funds:
        fund_code = fund.code or fund.fund_code
        amount = fund.amount

        if not fund_code:
            continue

        try:
            fund_code = _validate_fund_code(fund_code)
        except ValueError:
            continue

        if amount <= 0:
            db.delete_holding(user_id, fund_code)
        else:
            db.save_holding(user_id, fund_code, amount)

    return {"success": True, "message": "保存成功"}


@router.delete("/holdings")
async def delete_holding(request: Request, data: SingleHoldingRequest):
    """Delete a single holding"""
    # Check rate limit
    limit_result = check_rate_limit(request, "holdings")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    user_id = _auth_required(request)

    fund_code = data.code or data.fund_code
    if not fund_code:
        error_response, status_code = create_error_response(
            ErrorCode.INVALID_INPUT, message="缺少基金代码", http_status=400
        )
        return JSONResponse(status_code=status_code, content=error_response)

    try:
        fund_code = _validate_fund_code(fund_code)
    except ValueError as e:
        error_response, status_code = create_error_response(
            ErrorCode.INVALID_INPUT, message=f"输入验证失败: {str(e)}", http_status=400
        )
        return JSONResponse(status_code=status_code, content=error_response)

    db.delete_holding(user_id, fund_code)
    return {"success": True, "message": "删除成功"}


@router.post("/holdings/clear")
async def clear_all_holdings(request: Request):
    """Clear all holdings"""
    # Check rate limit
    limit_result = check_rate_limit(request, "holdings")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    user_id = _auth_required(request)

    # Check if user has holdings
    holdings = db.get_holdings(user_id)
    if not holdings:
        return JSONResponse(status_code=400, content={"success": False, "error": "当前没有持仓可清空"})

    db.clear_holdings(user_id)
    return {"success": True, "message": "已清空所有持仓"}


@router.post("/import")
async def import_holdings(request: Request):
    """Import holdings (placeholder)"""
    return JSONResponse(status_code=400, content={"success": False, "error": "No data provided"})


@router.post("/import_screenshot")
async def import_screenshot(request: Request, file: UploadFile = File(...)):
    """OCR import holdings from screenshot"""
    import os
    import tempfile

    user_id = _auth_required(request)

    if not file.filename:
        return JSONResponse(status_code=400, content={"success": False, "error": "文件名为空"})

    try:
        # Save to temp file
        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)

        try:
            # OCR parse
            from src.ocr import parse_image_easyocr

            results = parse_image_easyocr(tmp_path)
            parsed = results.get("funds", [])

            if not parsed:
                return {"success": True, "parsed": [], "message": results.get("message", "未识别到基金数据")}

            return {
                "success": True,
                "parsed": [
                    {"code": r.get("code", ""), "amount": r.get("amount", 0), "name": r.get("name", "")} for r in parsed
                ],
            }
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        logger.error(f"OCR error: {e}")
        error_response, status_code = create_error_response(
            ErrorCode.INVALID_INPUT,
            message=f"OCR处理失败: {str(e)}",
            details={"operation": "ocr_import"},
            http_status=500,
        )
        return JSONResponse(status_code=status_code, content=error_response)
