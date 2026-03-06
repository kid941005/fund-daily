#!/usr/bin/env python3
"""
Fund Daily Web UI - Web interface for fund daily tool
Simple Flask-based web UI for managing and viewing fund reports
"""

import os
import sys
import json
from datetime import datetime, timedelta
from functools import lru_cache

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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

# Config
DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")
CONFIG_FILE = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/config/config.json")

os.makedirs(DATA_DIR, exist_ok=True)

def load_config():
    """Load user config"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "default_funds": ["000001", "110022", "161725"],
        "report_time": "15:00"
    }

def save_config(config):
    """Save user config"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/funds')
def get_funds():
    """Get user's fund list"""
    config = load_config()
    funds = []
    
    for code in config.get('default_funds', []):
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
    config = load_config()
    codes = config.get('default_funds', [])
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
    return jsonify(history[:30])  # Last 30 days

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """Get or update config"""
    if request.method == 'POST':
        new_config = request.json
        save_config(new_config)
        return jsonify({"success": True, "message": "Config saved"})
    else:
        return jsonify(load_config())

@app.route('/api/add-fund', methods=['POST'])
def add_fund():
    """Add fund to watchlist"""
    code = request.json.get('code')
    if not code:
        return jsonify({"success": False, "error": "Fund code required"})
    
    # Verify fund exists
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
    """Remove fund from watchlist"""
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
    """Get investment advice"""
    config = load_config()
    codes = config.get('default_funds', ['000001', '110022', '161725'])
    report = generate_daily_report(codes)
    advice = generate_advice(report.get('funds', []))
    return jsonify({
        "success": True,
        "advice": advice
    })

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
