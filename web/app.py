#!/usr/bin/env python3
"""
Fund Daily Web Application
支持 Vue3 前端 + REST API
"""

import os
import sys
import uuid
import logging
import secrets
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, g, make_response, send_file
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
            return f.read().strip() or "2.6.0"
    return "2.6.0"


VERSION = get_version()

# 导入配置管理器
from src.config import get_config
config = get_config()

# Flask app
app = Flask(__name__, static_folder=None, template_folder='../dist')

# CORS
CORS(app, supports_credentials=True)

# Secret key - 使用配置管理器
secret_key = config.security.secret_key
if not secret_key:
    # 生产环境必须设置密钥
    if config.is_production():
        raise ValueError(
            "FUND_DAILY_SECRET_KEY must be set in production environment! "
            "Please set a strong secret key via environment variable."
        )
    # 开发环境使用随机生成的密钥
    secret_key = secrets.token_hex(32)
    logger.warning(
        f"Using auto-generated secret key for development. "
        f"For production, set FUND_DAILY_SECRET_KEY environment variable."
    )

app.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key

# Session config - 使用配置管理器
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # 更安全的默认值
app.config["SESSION_COOKIE_SECURE"] = config.security.secure_cookies
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7  # 7 天

# Initialize database
from db import database_pg as db
db.init_db()

# Register API blueprint
from web.api.routes import api as api_blueprint
app.register_blueprint(api_blueprint, url_prefix="/api")

# Register API documentation blueprint (P2优化)
try:
    from src.openapi import init_openapi_docs
    init_openapi_docs(app)
    logger.info("✅ OpenAPI文档已初始化")
except Exception as e:
    logger.warning(f"⚠️ OpenAPI文档初始化失败: {e}")

# Initialize rate limiter
try:
    from web.api.rate_limiter import init_rate_limiter
    init_rate_limiter(app)
    logger.info("✅ 速率限制器已初始化")
except Exception as e:
    logger.warning(f"⚠️ 速率限制器初始化失败: {e}")

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
    """Add request ID to response headers and record metrics"""
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    
    # Add processing time
    if hasattr(g, 'start_time'):
        duration = (datetime.now() - g.start_time).total_seconds()
        response.headers['X-Process-Time'] = f"{duration:.3f}"
        
        # 记录性能指标（排除/metrics端点自身以避免循环）
        if request.path != '/api/metrics' and request.path != '/api/metrics/enhanced':
            try:
                # 记录到标准指标服务
                from src.services.metrics_service import get_metrics_service
                metrics_service = get_metrics_service()
                metrics_service.record_request(
                    method=request.method,
                    path=request.path,
                    status_code=response.status_code,
                    duration=duration
                )
                
                # 记录到增强版指标服务（P2优化）
                try:
                    from src.services.enhanced_metrics_service import get_enhanced_metrics_service
                    enhanced_metrics_service = get_enhanced_metrics_service()
                    enhanced_metrics_service.record_request(
                        method=request.method,
                        path=request.path,
                        status_code=response.status_code,
                        duration=duration
                    )
                except Exception as e2:
                    logger.debug(f"Enhanced metrics recording failed (non-critical): {e2}")
                    
            except Exception as e:
                logger.error(f"Failed to record request metrics: {e}")
    
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
    """Serve Vue app (no-cache to avoid stale chunk references after rebuild)"""
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/<path:path>')
def serve_vue(path):
    """Serve Vue static files"""
    if path.startswith('api/'):
        from flask import jsonify
        return jsonify({'error': 'Not found'}), 404

    # 对于静态资源请求，优先返回压缩版本（长期缓存）
    if path.startswith('assets/'):
        rel_path = path[len('assets/'):]
        # 手动计算静态文件目录（相对于 app.py 的 ../dist/assets）
        import os
        static_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../dist/assets'))

        # 优先级：Brotli (.br) > Gzip (.gz) > 原始
        for ext, algo in [('.br', 'br'), ('.gz', 'gzip'), ('', None)]:
            file_path = os.path.join(static_dir, rel_path + ext)
            if os.path.isfile(file_path):
                # 使用 make_response 包裹，手动控制所有 header
                with open(file_path, 'rb') as f:
                    data = f.read()
                resp = make_response(data)
                if algo:
                    resp.headers['Content-Encoding'] = algo
                    resp.headers['Vary'] = 'Accept-Encoding'
                    # 移除 Content-Length，因为压缩后大小会变
                    resp.headers.pop('Content-Length', None)
                # 设置正确的 Content-Type
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type:
                    resp.headers['Content-Type'] = mime_type
                else:
                    # 后备方案
                    if rel_path.endswith('.js'):
                        resp.headers['Content-Type'] = 'text/javascript'
                    elif rel_path.endswith('.css'):
                        resp.headers['Content-Type'] = 'text/css'
                resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                resp.headers['Content-Length'] = len(data)
                return resp

        # 文件不存在
        return jsonify({'error': 'Not found'}), 404

    # SPA fallback — 其他路径返回 index.html（禁用缓存）
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


# ============== Health Check ==============
@app.route("/health")
def health_check():
    """Health check endpoint"""
    import psycopg2
    import redis
    
    # 使用配置管理器
    from src.config import get_config
    config = get_config()
    
    # Check PostgreSQL
    pg_status = "ok"
    if config.database.type == "postgres":
        try:
            conn = psycopg2.connect(
                host=config.database.host,
                port=config.database.port,
                database=config.database.name,
                user=config.database.user,
                password=config.database.password,
            )
            conn.close()
        except Exception as e:
            pg_status = str(e)
    else:
        pg_status = "sqlite (not checked)"
    
    # Check Redis
    redis_status = "ok"
    try:
        r = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        r.ping()
    except Exception as e:
        redis_status = str(e)
    
    return {
        "status": "ok" if pg_status == "ok" and redis_status == "ok" else "degraded",
        "version": VERSION,
        "database": pg_status,
        "redis": redis_status,
        "config": {
            "env": config.app.env,
            "database_type": config.database.type,
            "cache_enabled": config.cache.duration > 0,
        }
    }


# ============== Main ==============
if __name__ == "__main__":
    # 使用配置管理器
    from src.config import get_config
    config = get_config()
    
    app.run(host=config.server.host, port=config.server.port, debug=config.server.debug)
