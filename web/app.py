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
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Secret key for sessions - use environment variable with fallback
app.secret_key = os.environ.get('FUND_DAILY_SECRET_KEY') or secrets.token_hex(32)

# Configure session
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'

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
calculate_expected_return = fund_module.calculate_expected_return
get_fund_detail_info = fund_module.get_fund_detail_info

# Config
DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")
USERS_FILE = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/users.json")
CONFIG_FILE = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/config/config.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

# ============== User Account System ==============

def hash_password(password, salt=None):
    """Hash password with salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    # Use PBKDF2 for secure password hashing
    import hashlib
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${key.hex()}"

def verify_password(password, stored_hash):
    """Verify password against stored hash"""
    try:
        salt, key = stored_hash.split('$')
        new_hash = hash_password(password, salt)
        return new_hash == stored_hash
    except:
        return False

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
            stored_hash = user.get('password', '')
            # Support both old SHA256 (no $) and new PBKDF2 (with $) hashes
            if '$' in stored_hash:
                if verify_password(password, stored_hash):
                    user_id = uid
            else:
                # Legacy: old SHA256 hash without salt
                if stored_hash == hashlib.sha256(password.encode()).hexdigest():
                    user_id = uid
                    # Upgrade to new hash format
                    users[uid]['password'] = hash_password(password)
                    save_users(users)
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

@app.route('/api/export', methods=['GET'])
@login_required
def export_holdings():
    """Export user holdings data in CSV or JSON format"""
    import csv
    import io
    
    user_id = session.get('user_id')
    export_format = request.args.get('format', 'csv').lower()
    
    holdings = get_user_holdings(user_id)
    
    if not holdings:
        return jsonify({"success": False, "error": "暂无持仓数据"})
    
    export_data = []
    for h in holdings:
        code = h.get('code')
        fund_data = fetch_fund_data_eastmoney(code)
        detail = get_fund_detail_info(code) if code else {}
        
        row = {
            'code': code,
            'name': h.get('name', fund_data.get('name', '')),
            'amount': h.get('amount', 0),
            'buy_nav': h.get('buyNav', ''),
            'buy_date': h.get('buyDate', ''),
            'current_nav': fund_data.get('dwjz', ''),
            'estimate_nav': fund_data.get('gsz', ''),
            'daily_change': fund_data.get('gszzl', ''),
            'return_1m': detail.get('return_1m', ''),
            'return_3m': detail.get('return_3m', ''),
            'return_6m': detail.get('return_6m', ''),
            'return_1y': detail.get('return_1y', ''),
            'risk_level': detail.get('risk_metrics', {}).get('risk_level', ''),
            'sharpe_ratio': detail.get('risk_metrics', {}).get('sharpe_ratio', ''),
            'max_drawdown': detail.get('risk_metrics', {}).get('estimated_max_drawdown', ''),
            'fee_rate': detail.get('fee_rate', ''),
        }
        
        if h.get('amount', 0) > 0 and h.get('buyNav') and fund_data.get('dwjz'):
            try:
                current = float(fund_data.get('dwjz', 0))
                buy = float(h.get('buyNav'))
                if buy > 0:
                    profit_pct = (current - buy) / buy * 100
                    row['holding_profit_pct'] = round(profit_pct, 2)
                    row['holding_profit_amount'] = round(h.get('amount', 0) * profit_pct / 100, 2)
            except:
                pass
        
        export_data.append(row)
    
    if export_format == 'json':
        return jsonify({
            "success": True,
            "format": "json",
            "data": export_data,
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    header_map = {
        'code': '基金代码',
        'name': '基金名称',
        'amount': '持仓金额(元)',
        'buy_nav': '买入净值',
        'buy_date': '买入日期',
        'current_nav': '当前净值',
        'estimate_nav': '估算净值',
        'daily_change': '日涨跌幅(%)',
        'return_1m': '近1月(%)',
        'return_3m': '近3月(%)',
        'return_6m': '近6月(%)',
        'return_1y': '近1年(%)',
        'risk_level': '风险等级',
        'sharpe_ratio': '夏普比率',
        'max_drawdown': '最大回撤(%)',
        'fee_rate': '费率(%)',
        'holding_profit_pct': '持有收益(%)',
        'holding_profit_amount': '收益金额(元)'
    }
    
    output = io.StringIO()
    if export_data:
        fieldnames = list(export_data[0].keys())
        chinese_headers = [header_map.get(f, f) for f in fieldnames]
        writer = csv.writer(output)
        writer.writerow(chinese_headers)
        for row in export_data:
            writer.writerow([row.get(f, '') for f in fieldnames])
    
    from flask import Response
    filename = f"fund_holdings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'text/csv; charset=utf-8-sig'
        }
    )

@app.route('/api/import', methods=['POST'])
@login_required
def import_holdings():
    """Import holdings data from CSV file or JSON"""
    import csv
    import io
    
    user_id = session.get('user_id')
    
    # Check if file is uploaded
    if 'file' in request.files and request.files['file']:
        file = request.files['file']
        content = file.read().decode('utf-8')
        import_format = 'csv'
    else:
        # Get data from JSON request
        data = request.json
        import_format = data.get('format', 'csv').lower() if data else 'csv'
        content = None
        import_data = data.get('data', []) if data else []
    
    # Parse CSV content if file was uploaded
    if content:
        import_data = []
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Handle CSV format
            parts = line.split(',')
            if len(parts) >= 2:
                code = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else ''
                amount = 0
                if len(parts) > 2:
                    try:
                        amount = float(parts[2].strip().replace(',', ''))
                    except:
                        amount = 0
                if code and len(code) == 6:
                    import_data.append({'code': code, 'name': name, 'amount': amount})
    
    if not import_data:
        return jsonify({"success": False, "error": "没有导入数据"})
    
    # Get current holdings
    holdings = get_user_holdings(user_id)
    existing_codes = {h['code']: h for h in holdings}
    
    imported_count = 0
    errors = []
    
    # Field mapping (Chinese to English)
    field_map = {
        '基金代码': 'code',
        '基金名称': 'name',
        '持仓金额': 'amount',
        'amount': 'amount',
        'code': 'code',
    }
    
    for item in import_data:
        try:
            # Get fund code
            code = item.get('code', '')
            if not code:
                # Try Chinese field name
                code = item.get('基金代码', '')
            
            if not code:
                errors.append(f"缺少基金代码: {item}")
                continue
            
            code = str(code).strip()
            
            # Get amount
            amount = item.get('amount', 0)
            if isinstance(amount, str):
                amount = float(amount.replace(',', '')) if amount else 0
            else:
                amount = float(amount) if amount else 0
            
            # Get name (optional)
            name = item.get('name', item.get('基金名称', ''))
            
            # Validate fund exists
            fund_data = fetch_fund_data_eastmoney(code)
            if 'error' in fund_data or not fund_data.get('fundcode'):
                errors.append(f"基金代码 {code} 不存在")
                continue
            
            # Use fetched name if not provided
            if not name:
                name = fund_data.get('name', code)
            
            # Update or add
            if code in existing_codes:
                existing_codes[code]['amount'] = amount
                existing_codes[code]['name'] = name
            else:
                holdings.append({
                    'code': code,
                    'name': name,
                    'amount': amount
                })
                existing_codes[code] = holdings[-1]
            
            imported_count += 1
            
        except Exception as e:
            errors.append(f"处理失败: {item}, 错误: {str(e)}")
    
    # Save updated holdings
    save_user_holdings(user_id, holdings)
    
    return jsonify({
        "success": True,
        "imported": imported_count,
        "total": len(holdings),
        "errors": errors[:10]  # Limit error messages
    })

@app.route('/api/import-screenshot', methods=['POST'])
@login_required
def import_from_screenshot():
    """Import holdings from screenshot using OCR"""
    import re
    import subprocess
    import json
    
    user_id = session.get('user_id')
    
    # Check if image file is uploaded
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "请上传图片"})
    
    file = request.files['file']
    if not file.filename:
        return jsonify({"success": False, "error": "请选择图片文件"})
    
    # Save uploaded file temporarily
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
        filepath = tmp.name
        file.save(filepath)
    
    try:
        # Use image-vision skill to OCR
        ocr_script = os.path.expanduser("~/.openclaw/main/skills/image-vision/scripts/image_vision.py")
        
        if os.path.exists(ocr_script):
            result = subprocess.run(
                ['python3', ocr_script, 'ocr', filepath],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                try:
                    ocr_result = json.loads(result.stdout)
                    text = ocr_result.get('text', '')
                except:
                    text = result.stdout
            else:
                text = ""
        else:
            # Fallback: return error
            return jsonify({
                "success": False, 
                "error": "OCR工具未安装",
                "hint": "请安装: sudo apt install tesseract-ocr tesseract-ocr-chi-sim"
            })
        
        # Parse fund information from OCR text
        # Expected patterns:
        # - 6-digit fund codes: 000001, 110022, etc.
        # - Amounts: 10000, 10,000, etc.
        
        # Find 6-digit codes
        fund_codes = re.findall(r'\b(\d{6})\b', text)
        
        # Find amounts (with or without comma)
        amounts = re.findall(r'[￥¥]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*元?', text)
        
        # Try to match codes with amounts
        parsed = []
        
        # Simple parsing: assume each code corresponds to an amount found nearby
        # This is a heuristic and may need manual adjustment
        
        # Find lines with fund codes and try to extract amounts
        lines = text.split('\n')
        for line in lines:
            code_match = re.search(r'(\d{6})', line)
            amount_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', line)
            
            if code_match:
                code = code_match.group(1)
                amount = 0
                if amount_match:
                    amt_str = amount_match.group(1).replace(',', '')
                    amount = float(amt_str)
                
                if amount > 0:  # Only include if we found an amount
                    parsed.append({'code': code, 'amount': amount, 'source': line.strip()})
                elif len(parsed) < len(fund_codes) and fund_codes[len(parsed)] == code:
                    # Mark code for later
                    parsed.append({'code': code, 'amount': None, 'source': line.strip()})
        
        # Filter valid codes (6 digits, likely fund codes)
        valid_codes = []
        for p in parsed:
            code = p['code']
            # Check if it's a valid fund code (starts with 0, 1, 2, 3, 5, 6)
            if code[0] in ['0', '1', '2', '3', '5', '6']:
                valid_codes.append(p)
        
        return jsonify({
            "success": True,
            "ocr_text": text[:500],  # First 500 chars for preview
            "parsed": valid_codes,
            "message": f"识别到 {len(valid_codes)} 个基金代码，请确认金额后导入"
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "OCR识别超时"})
    except Exception as e:
        return jsonify({"success": False, "error": f"识别失败: {str(e)}"})
    finally:
        # Clean up temp file
        if os.path.exists(filepath):
            os.remove(filepath)

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

@app.route('/api/expected-return')
def get_expected_return():
    """Calculate expected return based on holdings and sector performance"""
    user_id = session.get('user_id')
    
    # Get holdings
    if user_id:
        holdings = get_user_holdings(user_id)
        holdings = [h for h in holdings if h.get('amount', 0) > 0]
    else:
        # Use default funds for non-logged in users
        holdings = []
    
    if not holdings:
        return jsonify({
            "success": False,
            "error": "暂无持仓，请先添加持仓",
            "expected_return": 0
        })
    
    # Get fund data for change info
    codes = [h.get('code') for h in holdings]
    funds_data = []
    for code in codes:
        data = fetch_fund_data_eastmoney(code)
        if not data.get('error'):
            funds_data.append(data)
    
    # Calculate expected return
    result = calculate_expected_return(holdings, funds_data)
    
    return jsonify({
        "success": True,
        "result": result
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
