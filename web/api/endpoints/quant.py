"""量化分析 API端点，调用 QuantService 提供统一逻辑"""

from flask import Blueprint, jsonify, session

from src.jwt_auth import get_token_from_header, verify_access_token
from src.services.quant_service import QuantServiceError, get_quant_service


def _get_user_id():
    """从 JWT token 或 session 获取用户ID"""
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


def _error_response(e: Exception, fallback: str, http_status: int = 500):
    """构造错误响应"""
    from src.error import ErrorCode, create_error_response

    if isinstance(e, QuantServiceError):
        code = ErrorCode.INVALID_INPUT if "validation" in str(e).lower() or "无效" in str(e) \
            else ErrorCode.INTERNAL_ERROR
        status = getattr(e, 'http_status', http_status)
        msg = str(e)
    else:
        code = ErrorCode.INTERNAL_ERROR
        status = http_status
        msg = fallback

    return jsonify(create_error_response(code=code, message=msg, http_status=status)), status


quant_bp = Blueprint("quant", __name__)
quant_service = get_quant_service()


@quant_bp.route("/timing-signals")
def get_timing_signals():
    """获取择时信号（需登录）"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    try:
        return jsonify({"success": True, "data": quant_service.timing_signals()})
    except Exception as exc:
        return _error_response(exc, "获取择时信号失败")


@quant_bp.route("/portfolio-optimize")
def get_portfolio_optimize():
    """获取组合优化建议（需登录）"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    try:
        return jsonify({"success": True, "data": quant_service.optimize_portfolio(result)})
    except Exception as exc:
        return _error_response(exc, "组合优化失败")


@quant_bp.route("/rebalancing")
def get_rebalancing():
    """获取调仓建议（需登录）"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    try:
        return jsonify({"success": True, "data": quant_service.rebalancing(result)})
    except Exception as exc:
        return _error_response(exc, "调仓建议生成失败")


@quant_bp.route("/dynamic-weights")
def get_dynamic_weights_api():
    """获取动态权重（需登录）"""
    result = _auth_required()
    if isinstance(result, tuple):
        return result
    try:
        return jsonify({"success": True, "data": quant_service.dynamic_weights()})
    except Exception as exc:
        return _error_response(exc, "动态权重获取失败")
