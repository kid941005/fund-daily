"""
API routes for Fund Daily
HTTP endpoints separated from business logic
"""

import os
import json
import logging
from flask import Blueprint, jsonify, request, session, Response

from .services import fund_service

logger = logging.getLogger(__name__)

# Create API blueprint
api = Blueprint('api', __name__)


# ============== Auth Routes ==============
@api.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    from db import database as db
    import secrets
    
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"})
    
    if len(username) < 2 or len(username) > 20:
        return jsonify({"success": False, "error": "用户名长度需2-20个字符"})
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "密码长度至少6位"})
    
    # Check if username exists
    existing = db.get_user_by_username(username)
    if existing:
        return jsonify({"success": False, "error": "用户名已存在"})
    
    # Create user
    from .auth import hash_password
    user_id = db.create_user(username, hash_password(password))
    if not user_id:
        return jsonify({"success": False, "error": "注册失败"})
    
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({"success": True, "message": "注册成功", "username": username})


@api.route('/login', methods=['POST'])
def login():
    """User login"""
    from db import database as db
    from .auth import verify_password
    
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    user = db.get_user_by_username(username)
    if not user:
        return jsonify({"success": False, "error": "用户名或密码错误"})
    
    stored_hash = user.get('password', '')
    
    # Verify password
    user_id = None
    if '$' in stored_hash:
        if verify_password(password, stored_hash):
            user_id = user.get('user_id')
    else:
        # Legacy hash
        import hashlib
        if stored_hash == hashlib.sha256(password.encode()).hexdigest():
            user_id = user.get('user_id')
            from .auth import hash_password
            db.update_user_password(user.get('user_id'), hash_password(password))
    
    if not user_id:
        return jsonify({"success": False, "error": "用户名或密码错误"})
    
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({"success": True, "message": "登录成功", "username": username})


@api.route('/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})


@api.route('/check-login', methods=['GET'])
def check_login():
    """Check if user is logged in"""
    user_id = session.get('user_id')
    if user_id:
        return jsonify({
            "success": True,
            "logged_in": True,
            "username": session.get('username', '')
        })
    return jsonify({"success": True, "logged_in": False})


# ============== Fund Routes ==============
@api.route('/funds')
def get_funds():
    """Get user's fund list"""
    user_id = session.get('user_id')
    
    if user_id:
        from db import database as db
        holdings = db.get_holdings(user_id)
        codes = [h['code'] for h in holdings if h.get('amount', 0) > 0]
        if not codes:
            codes = ["000001", "110022", "161725"]
    else:
        codes = ["000001", "110022", "161725"]
    
    funds = fund_service.get_funds_for_user([], codes)
    
    return jsonify({
        "success": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "funds": funds,
        "summary": fund_service.calculate_summary(funds)
    })


@api.route('/fund/<code>')
def get_fund_detail(code):
    """Get single fund detail"""
    from src.fetcher import fetch_fund_data
    from src.advice import analyze_fund
    
    data = fetch_fund_data(code)
    analysis = analyze_fund(data)
    return jsonify(analysis)


@api.route('/report')
def get_report():
    """Generate daily report"""
    user_id = session.get('user_id')
    
    if user_id:
        from db import database as db
        holdings = db.get_holdings(user_id)
    else:
        holdings = []
    
    report = fund_service.get_report_for_user(holdings)
    return jsonify(report)


@api.route('/history')
def get_history():
    """Get historical reports"""
    from datetime import datetime
    DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")
    
    history = []
    if os.path.exists(DATA_DIR):
        for filename in sorted(os.listdir(DATA_DIR), reverse=True):
            if filename.startswith('fund_report_') and filename.endswith('.txt'):
                date_str = filename.replace('fund_report_', '').replace('.txt', '')
                filepath = os.path.join(DATA_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                history.append({
                    "date": date_str,
                    "filename": filename,
                    "preview": content[:200] + "..." if len(content) > 200 else content
                })
    return jsonify(history[:30])


# ============== Holdings Routes ==============
@api.route('/holdings', methods=['GET', 'POST', 'DELETE'])
def manage_holdings():
    """Get or update user's holdings"""
    from db import database as db
    from src.fetcher import fetch_fund_data
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录", "need_login": True})
    
    if request.method == 'GET':
        holdings = db.get_holdings(user_id)
        # Add daily change to each holding
        for h in holdings:
            if h.get('amount', 0) > 0:
                fund_data = fetch_fund_data(h['code'])
                daily_change = float(fund_data.get('gszzl', 0) or 0)
                h['daily_change'] = daily_change
                if daily_change != 0:
                    h['daily_profit'] = round(h.get('amount', 0) * daily_change / 100, 2)
        return jsonify({"success": True, "holdings": holdings})
    
    elif request.method == 'POST':
        data = request.json
        code = data.get('code', '').strip()
        amount = float(data.get('amount', 0))
        
        if not code or len(code) != 6:
            return jsonify({"success": False, "error": "请输入6位基金代码"})
        
        # Verify fund exists
        fund_data = fetch_fund_data(code)
        if 'error' in fund_data or not fund_data.get('fundcode'):
            return jsonify({"success": False, "error": "基金代码不存在"})
        
        holdings = db.get_holdings(user_id)
        
        # Update or add
        for h in holdings:
            if h['code'] == code:
                h['amount'] = amount
                h['name'] = fund_data.get('name', code)
                break
        else:
            holdings.append({
                'code': code,
                'name': fund_data.get('name', code),
                'amount': amount
            })
        
        db.save_holdings(user_id, holdings)
        return jsonify({"success": True, "message": "持仓已保存"})
    
    elif request.method == 'DELETE':
        data = request.json
        code = data.get('code')
        
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h['code'] != code]
        db.save_holdings(user_id, holdings)
        
        return jsonify({"success": True, "message": "持仓已删除"})


# ============== Other Routes ==============
@api.route('/news')
def get_news():
    """Get market hot news"""
    from src.fetcher import fetch_market_news
    limit = request.args.get('limit', 8, type=int)
    news = fetch_market_news(limit)
    return jsonify({"success": True, "news": news})


@api.route('/sectors')
def get_sectors():
    """Get hot sectors"""
    from src.fetcher import fetch_hot_sectors
    limit = request.args.get('limit', 10, type=int)
    sectors = fetch_hot_sectors(limit)
    return jsonify({"success": True, "sectors": sectors})


@api.route('/advice')
def get_advice():
    """Get investment advice"""
    user_id = session.get('user_id')
    
    if user_id:
        from db import database as db
        holdings = db.get_holdings(user_id)
        holdings_dict = {h['code']: h for h in holdings}
    else:
        holdings = []
        holdings_dict = {}
    
    advice = fund_service.get_advice_for_user(holdings, holdings_dict)
    return jsonify({"success": True, "advice": advice})


@api.route('/fund-detail/<code>')
def get_fund_detail_full(code):
    """Get detailed fund info"""
    from src.advice import get_fund_detail_info
    detail = get_fund_detail_info(code)
    return jsonify({"success": True, "detail": detail})


@api.route('/expected-return')
def get_expected_return():
    """Calculate expected return"""
    from src.analyzer import calculate_expected_return
    from src.fetcher import fetch_fund_data
    
    user_id = session.get('user_id')
    
    if user_id:
        from db import database as db
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h.get('amount', 0) > 0]
    else:
        holdings = []
    
    if not holdings:
        return jsonify({"success": False, "error": "暂无持仓", "expected_return": 0})
    
    codes = [h.get('code') for h in holdings]
    funds_data = []
    for code in codes:
        data = fetch_fund_data(code)
        if not data.get('error'):
            funds_data.append(data)
    
    result = calculate_expected_return(holdings, funds_data)
    return jsonify({"success": True, "result": result})


@api.route('/portfolio-analysis')
def get_portfolio_analysis():
    """Get portfolio analysis"""
    user_id = session.get('user_id')
    
    if user_id:
        from db import database as db
        holdings = db.get_holdings(user_id)
        holdings_dict = {h['code']: h for h in holdings}
    else:
        holdings = []
        holdings_dict = {}
    
    analysis = fund_service.get_portfolio_analysis(holdings, holdings_dict)
    return jsonify({"success": True, "analysis": analysis})


# Import datetime at module level
from datetime import datetime
