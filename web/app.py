#!/usr/bin/env python3
"""
Fund Daily Web UI - Web interface for fund daily tool
With user account system
"""

import os
import sys
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import lru_cache

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from flask import Flask, session
from functools import wraps

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Secret key for sessions
app.secret_key = "fund-daily-secret-key-2026"

# Configure session
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Import fund functions - dynamic import to handle hyphenated filename
import importlib.util
import sys

def import_fund_module():
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'fund-daily.py')
    spec = importlib.util.spec_from_file_location("fund_daily", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

fund_module = import_fund_module()
fetch_fund_data_eastmoney = fund_module.fetch_fund_data_eastmoney
analyze_fund = fund_module.analyze_fund
generate_daily_report = fund_module.generate_daily_report
format_report_for_share = fund_module.format_report_for_share
fetch_market_hot_news = fund_module.fetch_market_hot_news
fetch_hot_sectors = fund_module.fetch_hot_sectors
generate_advice = fund_module.generate_advice
get_fund_detail_info = fund_module.get_fund_detail_info

# Config
DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")
USERS_FILE = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/users.json")
CONFIG_FILE = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/config/config.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

# ============== User Account System ==============

def hash_password(password):
    """Hash password with salt"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load users from file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to file"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_user_holdings(user_id):
    """Get user's holdings"""
    users = load_users()
    if user_id in users:
        return users[user_id].get('holdings', [])
    return []

def save_user_holdings(user_id, holdings):
    """Save user's holdings"""
    users = load_users()
    if user_id in users:
        users[user_id]['holdings'] = holdings
        save_users(users)

def get_current_user():
    """Get current logged in user"""
    return session.get('user_id')

def login_required(f):
    """Decorator for routes that require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({"success": False, "error": "请先登录", "need_login": True})
        return f(*args, **kwargs)
    return decorated_function

# ============== API Routes ==============

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"})
    
    if len(username) < 2 or len(username) > 20:
        return jsonify({"success": False, "error": "用户名长度需2-20个字符"})
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "密码长度至少6位"})
    
    users = load_users()
    
    # Check if username exists
    for uid, user in users.items():
        if user.get('username') == username:
            return jsonify({"success": False, "error": "用户名已存在"})
    
    # Create new user
    user_id = hashlib.sha256(username.encode()).hexdigest()[:16]
    users[user_id] = {
        'username': username,
        'password': hash_password(password),
        'holdings': [],
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)
    
    # Auto login
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": "注册成功",
        "username": username
    })

@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    users = load_users()
    
    # Find user
    user_id = None
    for uid, user in users.items():
        if user.get('username') == username:
            if user.get('password') == hash_password(password):
                user_id = uid
            break
    
    if not user_id:
        return jsonify({"success": False, "error": "用户名或密码错误"})
    
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": "登录成功",
        "username": username
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})

@app.route('/api/check-login', methods=['GET'])
def check_login():
    """Check if user is logged in"""
    user_id = session.get('user_id')
    if user_id:
        return jsonify({
            "success": True,
            "logged_in": True,
            "username": session.get('username', '')
        })
    return jsonify({
        "success": True,
        "logged_in": False
    })

@app.route('/api/funds')
def get_funds():
    """Get user's fund list"""
    user_id = session.get('user_id')
    
    # If logged in, use user's holdings
    if user_id:
        holdings = get_user_holdings(user_id)
        codes = [h['code'] for h in holdings if h.get('amount', 0) > 0]
        if not codes:
            codes = ["000001", "110022", "161725"]
    else:
        # Default funds for non-logged in users
        codes = ["000001", "110022", "161725"]
    
    funds = []
    for code in codes:
        data = fetch_fund_data_eastmoney(code)
        analysis = analyze_fund(data)
        if 'error' not in analysis:
            funds.append(analysis)
    
    return jsonify({
        "success": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "funds": funds,
        "summary": calculate_summary(funds)
    })

@app.route('/api/fund/<code>')
def get_fund_detail(code):
    """Get single fund detail"""
    data = fetch_fund_data_eastmoney(code)
    analysis = analyze_fund(data)
    return jsonify(analysis)

@app.route('/api/report')
def get_report():
    """Generate daily report"""
    user_id = session.get('user_id')
    
    if user_id:
        holdings = get_user_holdings(user_id)
        codes = [h['code'] for h in holdings if h.get('amount', 0) > 0]
        if not codes:
            codes = ["000001", "110022", "161725"]
    else:
        codes = ["000001", "110022", "161725"]
    
    report = generate_daily_report(codes)
    return jsonify(report)

@app.route('/api/history')
def get_history():
    """Get historical reports"""
    history = []
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

@app.route('/api/holdings', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_holdings():
    """Get or update user's holdings"""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        holdings = get_user_holdings(user_id)
        return jsonify({"success": True, "holdings": holdings})
    
    elif request.method == 'POST':
        data = request.json
        code = data.get('code', '').strip()
        amount = float(data.get('amount', 0))
        
        if not code or len(code) != 6:
            return jsonify({"success": False, "error": "请输入6位基金代码"})
        
        # Verify fund exists
        fund_data = fetch_fund_data_eastmoney(code)
        if 'error' in fund_data or not fund_data.get('fundcode'):
            return jsonify({"success": False, "error": "基金代码不存在"})
        
        holdings = get_user_holdings(user_id)
        
        # Check if fund already exists
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
        
        save_user_holdings(user_id, holdings)
        
        return jsonify({"success": True, "message": "持仓已保存"})
    
    elif request.method == 'DELETE':
        data = request.json
        code = data.get('code')
        
        holdings = get_user_holdings(user_id)
        holdings = [h for h in holdings if h['code'] != code]
        save_user_holdings(user_id, holdings)
        
        return jsonify({"success": True, "message": "持仓已删除"})

@app.route('/api/add-fund', methods=['POST'])
def add_fund():
    """Add fund to watchlist (legacy, for non-logged in users)"""
    code = request.json.get('code')
    if not code:
        return jsonify({"success": False, "error": "Fund code required"})
    
    data = fetch_fund_data_eastmoney(code)
    if 'error' in data or not data.get('fundcode'):
        return jsonify({"success": False, "error": "Invalid fund code"})
    
    config = load_config()
    if code not in config['default_funds']:
        config['default_funds'].append(code)
        save_config(config)
    
    return jsonify({"success": True, "fund": data})

@app.route('/api/remove-fund', methods=['POST'])
def remove_fund():
    """Remove fund from watchlist (legacy)"""
    code = request.json.get('code')
    config = load_config()
    if code in config['default_funds']:
        config['default_funds'].remove(code)
        save_config(config)
    return jsonify({"success": True})

@app.route('/api/news')
def get_news():
    """Get market hot news"""
    limit = request.args.get('limit', 8, type=int)
    news = fetch_market_hot_news(limit)
    return jsonify({
        "success": True,
        "news": news
    })

@app.route('/api/sectors')
def get_sectors():
    """Get hot sectors"""
    limit = request.args.get('limit', 10, type=int)
    sectors = fetch_hot_sectors(limit)
    return jsonify({
        "success": True,
        "sectors": sectors
    })

@app.route('/api/advice')
def get_advice():
    """Get investment advice based on user's holdings"""
    user_id = session.get('user_id')
    
    if user_id:
        holdings = get_user_holdings(user_id)
        codes = [h['code'] for h in holdings if h.get('amount', 0) > 0]
        holdings_dict = {h['code']: h for h in holdings}
        if not codes:
            return jsonify({
                "success": True,
                "advice": {
                    "action": "empty",
                    "advice": "暂无持仓，请先添加持仓",
                    "holdings": []
                }
            })
    else:
        codes = ["000001", "110022", "161725"]
        holdings_dict = {}
    
    report = generate_daily_report(codes)
    advice = generate_advice(report.get('funds', []))
    
    # Add holdings info to advice
    advice['holdings'] = []
    for fund in report.get('funds', []):
        code = fund.get('fund_code')
        h = holdings_dict.get(code, {})
        advice['holdings'].append({
            'code': code,
            'name': fund.get('fund_name'),
            'amount': h.get('amount', 0),
            'change': fund.get('daily_change', 0)
        })
    
    return jsonify({
        "success": True,
        "advice": advice
    })

@app.route('/api/fund-detail/<code>')
def get_fund_detail_full(code):
    """Get detailed fund information including risk metrics"""
    detail = get_fund_detail_info(code)
    return jsonify({
        "success": True,
        "detail": detail
    })

@app.route('/api/portfolio-analysis')
def get_portfolio_analysis():
    """Get portfolio analysis including backtest and risk metrics"""
    user_id = session.get('user_id')
    
    if user_id:
        holdings = get_user_holdings(user_id)
        holdings_dict = {h['code']: h for h in holdings}
        codes = [h['code'] for h in holdings if h.get('amount', 0) > 0]
        if not codes:
            return jsonify({
                "success": True,
                "analysis": {
                    "message": "暂无持仓，无法分析"
                }
            })
    else:
        holdings_dict = {}
        codes = ["000001", "110022", "161725"]
    
    # 获取每只基金的详细信息
    funds_detail = []
    total_amount = 0
    
    for code in codes:
        detail = get_fund_detail_info(code)
        h = holdings_dict.get(code, {})
        amount = h.get('amount', 0)
        
        if detail.get('fund_code'):
            detail['amount'] = amount
            detail['buy_nav'] = h.get('buyNav')
            detail['buy_date'] = h.get('buyDate')
            
            # 计算持有收益
            if amount > 0 and h.get('buyNav') and detail.get('nav'):
                try:
                    current_nav = float(detail['nav'])
                    buy_nav = float(h['buyNav'])
                    profit_pct = (current_nav - buy_nav) / buy_nav * 100
                    detail['holding_profit'] = round(profit_pct, 2)
                    detail['holding_profit_amount'] = round(amount * profit_pct / 100, 2)
                except:
                    pass
            
            funds_detail.append(detail)
            total_amount += amount
    
    # 计算组合风险指标
    portfolio_analysis = analyze_portfolio_risk(funds_detail, total_amount)
    
    # 资产配置建议
    allocation = suggest_allocation(funds_detail)
    
    return jsonify({
        "success": True,
        "analysis": {
            "funds": funds_detail,
            "total_amount": total_amount,
            "risk_metrics": portfolio_analysis,
            "allocation": allocation
        }
    })

def analyze_portfolio_risk(funds, total_amount):
    """Analyze portfolio risk metrics"""
    if not funds or total_amount == 0:
        return {"message": "暂无持仓数据"}
    
    # 计算持仓权重
    for fund in funds:
        fund['weight'] = round(fund['amount'] / total_amount * 100, 2) if fund.get('amount') else 0
    
    # 计算组合加权风险
    # 计算组合加权风险
    total_risk_score = sum(f.get('risk_metrics', {}).get('risk_score', 4) * f.get('weight', 0) for f in funds) / 100
    
    # 风险等级
    if total_risk_score > 6:
        risk_level = "高风险"
    elif total_risk_score > 4:
        risk_level = "中高风险"
    elif total_risk_score > 2:
        risk_level = "中等风险"
    else:
        risk_level = "中低风险"
    
    # 收益分析
    try:
        avg_return_1y = sum(float(f.get('return_1y', 0) or 0) * f.get('weight', 0) for f in funds) / 100
    except:
        avg_return_1y = 0
    
    return {
        "risk_level": risk_level,
        "risk_score": round(total_risk_score, 1),
        "avg_return_1y": round(avg_return_1y, 2),
        "fund_count": len(funds),
        "diversification": "良好" if len(funds) >= 5 else "一般" if len(funds) >= 3 else "需分散"
    }

def suggest_allocation(funds):
    """Suggest asset allocation based on risk profile"""
    if not funds:
        return {"message": "暂无持仓数据"}
    
    # 按风险等级分类
    high_risk = []
    medium_risk = []
    low_risk = []
    
    for fund in funds:
        risk = fund.get('risk_metrics', {}).get('risk_level', '中等风险')
        if '高' in risk:
            high_risk.append(fund)
        elif '低' in risk:
            low_risk.append(fund)
        else:
            medium_risk.append(fund)
    
    # 建议配置
    high_pct = len(high_risk) / len(funds) * 100 if funds else 0
    medium_pct = len(medium_risk) / len(funds) * 100 if funds else 0
    low_pct = len(low_risk) / len(funds) * 100 if funds else 0
    
    # 建议
    suggestions = []
    if high_pct > 50:
        suggestions.append("⚠️ 高风险基金占比过高，建议降低至30%以下")
    if low_pct < 20:
        suggestions.append("💡 建议增加低风险基金配置，提高组合稳定性")
    if len(funds) < 3:
        suggestions.append("📊 建议持有3-5只基金分散风险")
    
    if not suggestions:
        suggestions.append("✅ 当前配置较为合理")
    
    return {
        "high_risk_pct": round(high_pct, 1),
        "medium_risk_pct": round(medium_pct, 1),
        "low_risk_pct": round(low_pct, 1),
        "suggestions": suggestions,
        "ideal_allocation": {
            "high_risk": "20-30%",
            "medium_risk": "40-50%",
            "low_risk": "30-40%"
        }
    }

def calculate_summary(funds):
    """Calculate market summary"""
    up = sum(1 for f in funds if f['trend'] == 'up')
    down = sum(1 for f in funds if f['trend'] == 'down')
    flat = len(funds) - up - down
    
    return {
        "total": len(funds),
        "up": up,
        "down": down,
        "flat": flat,
        "sentiment": "乐观" if up > down else "谨慎" if down > up else "平稳"
    }

def load_config():
    """Load user config (legacy)"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "default_funds": ["000001", "110022", "161725"],
        "report_time": "15:00"
    }

def save_config(config):
    """Save user config (legacy)"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
