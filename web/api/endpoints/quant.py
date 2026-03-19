"""量化分析 API端点，调用 QuantService 提供统一逻辑"""

from flask import Blueprint, jsonify, session

from src.jwt_auth import get_token_from_header, verify_access_token
from src.services.quant_service import QuantServiceError, get_quant_service
from web.api.routes import handle_error

quant_bp = Blueprint("quant", __name__)
quant_service = get_quant_service()


def _get_user_id():
 token = get_token_from_header()
 if token:
 is_valid, payload, _ = verify_access_token(token)
 if is_valid:
 return payload.get("sub")
 return session.get("user_id")


@quant_bp.route("/timing-signals")
def get_timing_signals():
 """获取择时信号"""
 try:
 result = quant_service.timing_signals()
 return jsonify({"success": True, "data": result})
 except QuantServiceError as exc:
 return handle_error(exc, str(exc))
 except Exception as exc:
 return handle_error(exc, "获取择时信号失败")


@quant_bp.route("/portfolio-optimize")
def get_portfolio_optimize():
 """获取组合优化建议"""
 user_id = _get_user_id()
 try:
 result = quant_service.optimize_portfolio(user_id)
 return jsonify({"success": True, "data": result})
 except QuantServiceError as exc:
 return handle_error(exc, str(exc))
 except Exception as exc:
 return handle_error(exc, "组合优化失败")


@quant_bp.route("/rebalancing")
def get_rebalancing():
 """获取调仓建议"""
 user_id = _get_user_id()
 try:
 result = quant_service.rebalancing(user_id)
 return jsonify({"success": True, "data": result})
 except QuantServiceError as exc:
 return handle_error(exc, str(exc))
 except Exception as exc:
 return handle_error(exc, "调仓建议生成失败")


@quant_bp.route("/dynamic-weights")
def get_dynamic_weights_api():
 """获取动态权重"""
 try:
 result = quant_service.dynamic_weights()
 return jsonify({"success": True, "data": result})
 except QuantServiceError as exc:
 return handle_error(exc, str(exc))
 except Exception as exc:
 return handle_error(exc, "动态权重获取失败")
