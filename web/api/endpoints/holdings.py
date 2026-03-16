"""
Holdings API endpoints
"""

from flask import Blueprint, jsonify, request, session
from db import database as db

holdings_bp = Blueprint("holdings", __name__)


@holdings_bp.route("/holdings")
def get_holdings():
    """Get user holdings"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "请先登录", "need_login": True})
    
    holdings = db.get_holdings(user_id)
    return jsonify({"success": True, "holdings": holdings})


@holdings_bp.route("/holdings", methods=["POST"])
def manage_holdings():
    """Add/update holdings"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "请先登录", "need_login": True})
    
    data = request.json or {}
    action = data.get("action", "add")
    
    if action == "delete":
        code = data.get("code")
        if code:
            db.delete_holding(user_id, code)
        return jsonify({"success": True, "message": "删除成功"})
    
    # Add or update - 支持单条和多条格式
    funds = data.get("funds", [])
    # 如果没有 funds 数组，检查是否有单条 code/amount
    if not funds and data.get("code"):
        funds = [data]
    
    for f in funds:
        code = f.get("code")
        amount = float(f.get("amount", 0))
        
        if amount <= 0:
            if code:
                db.delete_holding(user_id, code)
        else:
            db.save_holding(user_id, code, amount)
    
    return jsonify({"success": True, "message": "保存成功"})


@holdings_bp.route("/holdings/clear", methods=["POST"])
def clear_all_holdings():
    """Clear all holdings"""
    user_id = session.get("user_id")
    if not user_id:
        # 未登录用户：尝试从 localStorage 清除
        return jsonify({"success": False, "error": "请先登录", "need_login": True}), 401
    
    db.clear_holdings(user_id)
    return jsonify({"success": True, "message": "已清空所有持仓"})


@holdings_bp.route("/import", methods=["POST"])
def import_holdings():
    """Import holdings"""
    return jsonify({"success": False, "error": "No data provided"}), 400
