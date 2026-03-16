#!/usr/bin/env python3
"""
Fund Daily Web Application
支持 Vue3 前端 + REST API
"""

import os
import sys
import uuid
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, g
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_version():
    """读取版本号"""
    VERSION_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "VERSION"
    )
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip() or "2.5.0"
    return "2.5.0"


VERSION = get_version()

# Flask app
app = Flask(__name__, static_folder='../dist/assets', template_folder='../dist')

# CORS
CORS(app, supports_credentials=True)

# Secret key
secret_key = os.environ.get("FUND_DAILY_SECRET_KEY")
if not secret_key:
    secret_key = "fund-daily-dev-key-please-change-in-production"
app.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key

# Session config - 宽松配置以确保登录状态持久
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = None
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FUND_DAILY_SECURE_COOKIES", "").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7  # 7 天

# Initialize database
from db import database as db
db.init_db()

# Register API blueprint
from web.api.routes import api as api_blueprint
app.register_blueprint(api_blueprint, url_prefix="/api")

# Config paths
DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.json")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


# ============== Config Functions ==============
def load_config():
    """Load config from file"""
    import json
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
    return {}


def save_config(config):
    """Save config to file"""
    import json
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


# ============== Middleware ==============
@app.before_request
def before_request():
    """Request logging and ID"""
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = datetime.now()
    
    # Log request (敏感信息脱敏)
    method = request.method
    path = request.path
    if '/password' in path or '/login' in path:
        logger.info(f"[{g.request_id}] {method} {path}")
    else:
        logger.info(f"[{g.request_id}] {method} {path}")


@app.after_request
def after_request(response):
    """Add request ID to response headers"""
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    
    # Add processing time
    if hasattr(g, 'start_time'):
        duration = (datetime.now() - g.start_time).total_seconds()
        response.headers['X-Process-Time'] = f"{duration:.3f}"
    
    return response


# ============== Config Routes ==============
@app.route("/api/config", methods=["GET"])
def get_config():
    """Get config"""
    config = load_config()
    safe_config = config.copy()
    if "dingtalk" in safe_config:
        safe_config["dingtalk"] = {
            **safe_config["dingtalk"],
            "webhook": "***" if safe_config["dingtalk"].get("webhook") else "",
        }
    return {"success": True, "config": safe_config}


@app.route("/api/config", methods=["POST"])
def update_config():
    """Update config"""
    from flask import request
    data = request.json or {}
    config = load_config()

    for key in ["default_funds"]:
        if key in data:
            config[key] = data[key]

    for notifier in ["dingtalk"]:
        if notifier in data:
            notifier_data = data[notifier]
            if isinstance(notifier_data, dict):
                if notifier == "dingtalk" and notifier_data.get("webhook", "").startswith("***"):
                    notifier_data["webhook"] = config.get(notifier, {}).get("webhook", "")
                config[notifier] = notifier_data

    save_config(config)
    return {"success": True}


# ============== Import/Export ==============
@app.route("/api/export", methods=["GET"])
def export_holdings():
    """Export holdings"""
    import csv
    import io
    from flask import Response
    from datetime import datetime
    from flask import session, request

    user_id = session.get("user_id")
    if not user_id:
        return {"success": False, "error": "请先登录"}

    export_format = request.args.get("format", "csv").lower()
    holdings = db.get_holdings(user_id)

    if not holdings:
        return {"success": False, "error": "暂无持仓数据"}

    export_data = []
    for h in holdings:
        code = h.get("code")
        from src.fetcher import fetch_fund_data
        fund_data = fetch_fund_data(code)
        from src.advice import get_fund_detail_info
        detail = get_fund_detail_info(code) if code else {}
        
        export_data.append({
            "code": code,
            "name": detail.get("fund_name", h.get("name", "")),
            "amount": h.get("amount", 0),
            "buy_nav": h.get("buy_nav", ""),
            "buy_date": h.get("buy_date", ""),
            "nav": detail.get("nav", ""),
            "daily_change": detail.get("daily_change", 0),
        })

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["code", "name", "amount", "buy_nav", "buy_date", "nav", "daily_change"])
        writer.writeheader()
        writer.writerows(export_data)
        
        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f"attachment; filename=holdings_{datetime.now().strftime('%Y%m%d')}.csv"},
        )
    else:
        return {"success": True, "data": export_data}


# ============== Vue App Routes ==============
@app.route('/')
def vue_app():
    """Serve Vue app"""
    return render_template('index.html')


@app.route('/<path:path>')
def serve_vue(path):
    """Serve Vue static files"""
    if path.startswith('api/'):
        from flask import jsonify
        return jsonify({'error': 'Not found'}), 404
    
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist', path)
    if os.path.exists(static_path):
        return app.send_static_file(path)
    return render_template('index.html')


# ============== Health Check ==============
@app.route("/health")
def health_check():
    """Health check endpoint"""
    import psycopg2
    import redis
    
    # Check PostgreSQL
    pg_status = "ok"
    try:
        conn = psycopg2.connect(
            host=os.environ.get("FUND_DAILY_DB_HOST", "localhost"),
            port=os.environ.get("FUND_DAILY_DB_PORT", "5432"),
            database=os.environ.get("FUND_DAILY_DB_NAME", "fund_daily"),
            user=os.environ.get("FUND_DAILY_DB_USER", "kid"),
            password=os.environ.get("FUND_DAILY_DB_PASSWORD", ""),
        )
        conn.close()
    except Exception as e:
        pg_status = str(e)
    
    # Check Redis
    redis_status = "ok"
    try:
        r = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379))
        )
        r.ping()
    except Exception as e:
        redis_status = str(e)
    
    return {
        "status": "ok" if pg_status == "ok" and redis_status == "ok" else "degraded",
        "version": VERSION,
        "postgres": pg_status,
        "redis": redis_status,
    }


# ============== Main ==============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
