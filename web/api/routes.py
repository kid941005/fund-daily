"""
API routes for Fund Daily
所有API端点的统一入口
"""

import os
import logging
import hashlib
import tempfile
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from web.services import fund_service
from db import database as db
from src.fetcher import fetch_fund_data, fetch_market_news, fetch_hot_sectors
from src.advice import analyze_fund, get_fund_detail_info, generate_100_score
from src.scoring import apply_ranking_bonus
from .auth import hash_password, verify_password

logger = logging.getLogger(__name__)

# Create API blueprint
api = Blueprint("api", __name__)

# 导入拆分后的端点
from .endpoints.funds import funds_bp
from .endpoints.quant import quant_bp
from .endpoints.holdings import holdings_bp
from .endpoints.analysis import analysis_bp

# 注册蓝图
api.register_blueprint(funds_bp, url_prefix="/")
api.register_blueprint(holdings_bp, url_prefix="/")
api.register_blueprint(analysis_bp, url_prefix="/")
api.register_blueprint(quant_bp, url_prefix="/")


# ============== Error Handlers ==============
def handle_error(e: Exception, message: str = "请求失败") -> tuple:
    logger.error(f"{message}: {str(e)}")
    return jsonify({"success": False, "error": message}), 500


def handle_validation_error(message: str) -> tuple:
    return jsonify({"success": False, "error": message}), 400


# ============== Auth Routes ==============
@api.route("/register", methods=["POST"])
def register():
    """Register a new user"""
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return handle_validation_error("用户名和密码不能为空")

    if len(password) < 6:
        return handle_validation_error("密码长度至少6位")

    password_hash = hash_password(password)

    try:
        user_id = db.create_user(username, password_hash)
        session["user_id"] = user_id
        session["username"] = username
        return jsonify({"success": True, "message": "注册成功", "username": username})
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            return handle_validation_error("用户名已存在")
        return handle_error(e, "注册失败")


@api.route("/login", methods=["POST"])
def login():
    """Login"""
    import sys
    print(f"DEBUG routes: request.json = {request.json}", file=sys.stderr)
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    logger.info(f"Login attempt: {username}")
    print(f"DEBUG routes: username={username}, password={password}", file=sys.stderr)
    
    user = db.verify_user(username, password)
    if not user:
        logger.warning(f"Login failed for: {username}")
        return handle_validation_error("用户名或密码错误")

    session["user_id"] = user["user_id"]
    session["username"] = user["username"]

    return jsonify({"success": True, "message": "登录成功", "username": user["username"]})


@api.route("/logout", methods=["POST"])
def logout():
    """Logout"""
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})


@api.route("/check-login")
def check_login():
    """Check login status"""
    user_id = session.get("user_id")
    username = session.get("username")
    
    if user_id:
        return jsonify({"success": True, "logged_in": True, "username": username})
    return jsonify({"success": True, "logged_in": False})


# ============== Market Routes ==============
@api.route("/news")
def get_news():
    """Get market news"""
    limit = request.args.get("limit", 8, type=int)
    news = fetch_market_news(limit)
    return jsonify({"success": True, "news": news})


@api.route("/sectors")
def get_sectors():
    """Get hot sectors"""
    limit = request.args.get("limit", 10, type=int)
    sectors = fetch_hot_sectors(limit)
    return jsonify({"success": True, "sectors": sectors})


# ============== Advice Routes ==============
@api.route("/advice")
def get_advice():
    """Get investment advice"""
    from web.services.fund_service import calculate_fund_scores_batch
    
    user_id = session.get("user_id")
    
    if user_id:
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h.get("amount", 0) > 0]
    else:
        holdings = []

    # 获取基金数据
    # 只有未登录用户才显示默认基金，登录用户无持仓时返回空
    if user_id and not holdings:
        return jsonify({"success": True, "funds": [], "message": "暂无持仓"})
    
    default_codes = ["000001", "110022", "161725"]
    codes = [h["code"] for h in holdings] if holdings else default_codes
    holdings_dict = {h["code"]: h for h in holdings}
    
    # 构建基金数据
    from src.fetcher import fetch_fund_data
    from src.advice import analyze_fund
    
    funds_data = []
    for code in codes:
        data = fetch_fund_data(code)
        if not data.get("error"):
            fund = analyze_fund(data)
            h = holdings_dict.get(code, {})
            fund["amount"] = h.get("amount", 0)
            funds_data.append(fund)
    
    # 批量计算评分（并行获取所有基金的 manager 和 scale）
    funds_data = calculate_fund_scores_batch(funds_data)

    # 计算持仓比例
    total_amount = sum(f.get("amount", 0) for f in funds_data)
    for fund in funds_data:
        amount = fund.get("amount", 0)
        fund["current_pct"] = round(amount / total_amount * 100, 1) if total_amount > 0 else 0
    
    # 计算目标持仓比例（去弱留强）
    scored_funds = [(f, f.get("score_100", {}).get("total_score", 0)) for f in funds_data]
    
    if scored_funds:
        total_score = sum(max(s, 0) for _, s in scored_funds)
        
        if total_score > 0 and total_amount > 0:
            for fund, score in scored_funds:
                score = max(score, 0)
                base_ratio = score / total_score
                if score >= 60:
                    target_ratio = base_ratio * 1.5
                elif score >= 50:
                    target_ratio = base_ratio * 1.2
                else:
                    target_ratio = base_ratio * 0.8
                
                fund["target_amount"] = round(total_amount * target_ratio, 2)
                fund["target_pct"] = round(target_ratio * 100, 1)
        else:
            for fund, _ in scored_funds:
                fund["target_pct"] = round(100 / len(scored_funds), 1)
    else:
        for fund in funds_data:
            fund["target_pct"] = 0

    funds_data = apply_ranking_bonus(funds_data)
    advice = fund_service.generate_advice(funds_data)
    advice["funds"] = funds_data
    return jsonify({"success": True, "advice": advice})


# ============== Screenshot Import ==============
@api.route("/import-screenshot", methods=["POST"])
def import_screenshot():
    """Import holdings from screenshot"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "Empty filename"})
        
        # 保存临时文件
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        # OCR 识别
        from src.ocr import parse_image_easyocr
        result = parse_image_easyocr(temp_path)
        
        # 清理临时文件
        os.remove(temp_path)
        
        # 统一返回格式，适配前端
        funds = result.get("funds", [])
        return jsonify({
            "success": result.get("success", False),
            "parsed": funds,
            "message": f"识别到 {len(funds)} 个基金"
        })
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        return jsonify({"success": False, "error": str(e)})
