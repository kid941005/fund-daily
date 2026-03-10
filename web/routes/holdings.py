"""
持仓蓝图
处理用户持仓管理
"""
from flask import Blueprint, request, jsonify, session
from .utils import login_required

holdings_bp = Blueprint('holdings', __name__, url_prefix='/api')

@holdings_bp.route('/holdings', methods=['GET'])
@login_required
def get_holdings():
    """获取用户持仓"""
    from db import database as db
    user_id = session.get('user_id')
    holdings = db.get_holdings(user_id)
    return jsonify({
        "success": True,
        "holdings": holdings
    })

@holdings_bp.route('/holdings', methods=['POST'])
@login_required
def add_holding():
    """添加持仓"""
    from db import database as db
    data = request.json
    user_id = session.get('user_id')
    
    code = data.get('code', '').strip()
    name = data.get('name', '').strip()
    amount = data.get('amount', 0)
    buy_nav = data.get('buy_nav', '')
    buy_date = data.get('buy_date', '')
    
    if not code:
        return jsonify({"success": False, "error": "基金代码不能为空"})
    
    # 获取基金名称
    if not name:
        from services.data_service import fetch_fund_data_eastmoney
        fund_data = fetch_fund_data_eastmoney(code)
        name = fund_data.get('name', code)
    
    # 保存持仓
    db.save_holding(user_id, code, name, amount, buy_nav, buy_date)
    
    return jsonify({
        "success": True,
        "message": "持仓添加成功"
    })

@holdings_bp.route('/holdings', methods=['DELETE'])
@login_required
def delete_holding():
    """删除持仓"""
    from db import database as db
    data = request.json
    user_id = session.get('user_id')
    code = data.get('code', '')
    
    db.delete_holding(user_id, code)
    
    return jsonify({
        "success": True,
        "message": "持仓已删除"
    })

@holdings_bp.route('/add-fund', methods=['POST'])
@login_required
def add_fund():
    """添加基金到自选"""
    from db import database as db
    data = request.json
    user_id = session.get('user_id')
    code = data.get('code', '').strip()
    name = data.get('name', '')
    
    if not code:
        return jsonify({"success": False, "error": "基金代码不能为空"})
    
    # 获取基金名称
    if not name:
        from services.data_service import fetch_fund_data_eastmoney
        fund_data = fetch_fund_data_eastmoney(code)
        name = fund_data.get('name', code)
    
    # 添加到自选
    db.add_to_watchlist(user_id, code, name)
    
    return jsonify({
        "success": True,
        "message": "已添加到自选"
    })

@holdings_bp.route('/remove-fund', methods=['POST'])
@login_required
def remove_fund():
    """移除自选基金"""
    from db import database as db
    data = request.json
    user_id = session.get('user_id')
    code = data.get('code', '')
    
    db.remove_from_watchlist(user_id, code)
    
    return jsonify({
        "success": True,
        "message": "已从自选移除"
    })
