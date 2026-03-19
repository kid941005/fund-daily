"""
Holdings API endpoints
支持 Session 和 JWT Token 两种认证方式
"""

from flask import Blueprint, jsonify, request, session, g
from db import database_pg as db
from web.api.validation import validate_request, ValidationError
from src.error import create_error_response, ErrorCode
from web.api.rate_limiter import holdings_limit
from src.jwt_auth import verify_access_token, get_token_from_header

holdings_bp = Blueprint("holdings", __name__)


def _get_user_id():
    """从 JWT token 或 session 获取当前用户ID"""
    token = get_token_from_header()
    if token:
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return session.get("user_id")


def _auth_required():
    """验证用户是否已登录"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({
            "success": False,
            "error": "请先登录",
            "need_login": True,
            "error_code": "UNAUTHORIZED"
        }), 401
    return user_id


@holdings_bp.route("/holdings")
@holdings_limit()
def get_holdings():
    """Get user holdings"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    user_id = result
    
    holdings = db.get_holdings(user_id)
    return jsonify({"success": True, "holdings": holdings})


@holdings_bp.route("/holdings", methods=["POST"])
@holdings_limit()
@validate_request('batch_holdings')
def manage_holdings():
    """Add/update holdings"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    user_id = result
    
    data = request.json or {}
    action = data.get("action", "add")
    
    if action == "delete":
        fund_code = data.get("code") or data.get("fund_code")
        if fund_code:
            # 验证基金代码
            try:
                from web.api.validation import validator
                validated_fund_code = validator.validate_fund_code(fund_code, 'fund_code')
                db.delete_holding(user_id, validated_fund_code)
            except ValidationError as e:
                return create_error_response(
                    code=ErrorCode.INVALID_INPUT,
                    message=f"输入验证失败: {e.message}",
                    details={"field": e.field},
                    http_status=400
                )
        return jsonify({"success": True, "message": "删除成功"})
    
    # 使用验证后的数据
    validated_funds = request.validated_data
    
    for fund in validated_funds:
        fund_code = fund.get("code") or fund.get("fund_code")
        amount = fund.get("amount", 0)
        
        if amount <= 0:
            if fund_code:
                db.delete_holding(user_id, fund_code)
        else:
            db.save_holding(user_id, fund_code, amount)
    
    return jsonify({"success": True, "message": "保存成功"})


@holdings_bp.route("/holdings", methods=["DELETE"])
@holdings_limit()
@validate_request('holding')
def delete_holding():
    """Delete a single holding"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    user_id = result
    
    # 使用验证后的数据
    validated_data = request.validated_data
    fund_code = validated_data.get("code") or validated_data.get("fund_code")
    
    if not fund_code:
        return create_error_response(
            code=ErrorCode.INVALID_INPUT,
            message="缺少基金代码",
            http_status=400
        )
    
    # 使用数据库直接删除
    db.delete_holding(user_id, fund_code)
    
    return jsonify({"success": True, "message": "删除成功"})


@holdings_bp.route("/holdings/clear", methods=["POST"])
@holdings_limit()
def clear_all_holdings():
    """Clear all holdings"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    user_id = result
    
    # 验证用户是否有持仓（可选，但可以防止误操作）
    holdings = db.get_holdings(user_id)
    if not holdings:
        return jsonify({"success": False, "error": "当前没有持仓可清空"}), 400
    
    db.clear_holdings(user_id)
    return jsonify({"success": True, "message": "已清空所有持仓"})


@holdings_bp.route("/import", methods=["POST"])
def import_holdings():
    """Import holdings"""
    return jsonify({"success": False, "error": "No data provided"}), 400


@holdings_bp.route("/import-screenshot", methods=["POST"])
def import_screenshot():
    """OCR识别截图并导入持仓"""
    import os
    import tempfile
    
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    user_id = result
    
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "没有上传文件"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "文件名为空"})
    
    try:
        # 保存临时文件
        suffix = os.path.splitext(file.filename)[1] or '.jpg'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            file.save(tmp_path)
        
        try:
            # OCR 识别
            from src.ocr import FundOcrParser, parse_image_easyocr
            import easyocr
            
            # 使用 EasyOCR 解析图片
            results = parse_image_easyocr(tmp_path)
            parsed = results.get("funds", [])
            
            if not parsed:
                return jsonify({
                    "success": True,
                    "parsed": [],
                    "message": results.get("message", "未识别到基金数据")
                })
            
            return jsonify({
                "success": True,
                "parsed": [{"code": r.get("code", ""), "amount": r.get("amount", 0), "name": r.get("name", "")} for r in parsed]
            })
        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        import logging
        logging.error(f"OCR error: {e}")
        return create_error_response(
            ErrorCode.INVALID_INPUT,
            f"OCR处理失败: {str(e)}",
            details={"operation": "ocr_import"},
            http_status=500
        )
