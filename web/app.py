#!/usr/bin/env python3
"""
Fund Daily Web UI - Simplified with modular structure
"""

VERSION = "2.0"

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Secret key
secret_key = os.environ.get('FUND_DAILY_SECRET_KEY')
if not secret_key:
    secret_key = "fund-daily-dev-key-please-change-in-production"
app.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key

# Session config
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FUND_DAILY_SECURE_COOKIES', '').lower() == 'true'

# Initialize database
from db import database as db
db.init_db()

# Register API blueprint
from web.api.routes import api as api_blueprint
app.register_blueprint(api_blueprint, url_prefix='/api')

# Config paths
DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', version=VERSION)


# ============== Config ==============
def load_config():
    """Load user config"""
    default = {
        "default_funds": os.environ.get("FUND_CODES", "000001,110022,161725").split(","),
        "dingtalk": {"enabled": bool(os.environ.get('DINGTALK_WEBHOOK')), "webhook": os.environ.get("DINGTALK_WEBHOOK", "")},
    }
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            try:
                config = json.load(f)
                for key in default:
                    if key not in config:
                        config[key] = default[key]
                return config
            except:
                return default
    return default


def save_config(config):
    """Save user config"""
    import json
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get config"""
    config = load_config()
    safe_config = config.copy()
    if 'dingtalk' in safe_config:
        safe_config['dingtalk'] = {**safe_config['dingtalk'], 'webhook': '***' if safe_config['dingtalk'].get('webhook') else ''}
    return jsonify({"success": True, "config": safe_config})


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update config"""
    from flask import request, jsonify
    data = request.json or {}
    config = load_config()
    
    for key in ['default_funds']:
        if key in data:
            config[key] = data[key]
    
    for notifier in ['dingtalk']:
        if notifier in data:
            notifier_data = data[notifier]
            if isinstance(notifier_data, dict):
                if notifier == 'dingtalk' and notifier_data.get('webhook', '').startswith('***'):
                    notifier_data['webhook'] = config.get(notifier, {}).get('webhook', '')
                config[notifier] = notifier_data
    
    save_config(config)
    return jsonify({"success": True})


# ============== Import/Export ==============
@app.route('/api/export', methods=['GET'])
def export_holdings():
    """Export holdings"""
    import csv
    import io
    from flask import Response
    from datetime import datetime
    from db import database as db
    from src.fetcher import fetch_fund_data
    from src.advice import get_fund_detail_info
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"})
    
    export_format = request.args.get('format', 'csv').lower()
    holdings = db.get_holdings(user_id)
    
    if not holdings:
        return jsonify({"success": False, "error": "暂无持仓数据"})
    
    export_data = []
    for h in holdings:
        code = h.get('code')
        fund_data = fetch_fund_data(code)
        detail = get_fund_detail_info(code) if code else {}
        
        row = {
            'code': code,
            'name': h.get('name', fund_data.get('name', '')),
            'amount': h.get('amount', 0),
            'daily_change': fund_data.get('gszzl', ''),
            'return_1m': detail.get('return_1m', ''),
            'return_3m': detail.get('return_3m', ''),
            'risk_level': detail.get('risk_metrics', {}).get('risk_level', ''),
        }
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
        'daily_change': '日涨跌幅(%)',
        'return_1m': '近1月(%)',
        'return_3m': '近3月(%)',
        'risk_level': '风险等级',
    }
    
    output = io.StringIO()
    if export_data:
        fieldnames = list(export_data[0].keys())
        chinese_headers = [header_map.get(f, f) for f in fieldnames]
        writer = csv.writer(output)
        writer.writerow(chinese_headers)
        for row in export_data:
            writer.writerow([row.get(f, '') for f in fieldnames])
    
    filename = f"fund_holdings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'text/csv; charset=utf-8-sig'
        }
    )


# Need these imports at the end to avoid circular imports
from flask import jsonify, session, request
import json


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
