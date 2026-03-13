"""
API routes for Fund Daily
HTTP endpoints separated from business logic
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
from src.advice import analyze_fund, get_fund_detail_info
from src.analyzer import calculate_expected_return
from src.ocr import parse_image_easyocr, EASYOCR_AVAILABLE
from .auth import hash_password, verify_password

logger = logging.getLogger(__name__)


# ============== Error Handlers ==============


def handle_error(e: Exception, message: str = "请求失败") -> tuple:
    """统一错误处理"""
    logger.error(f"{message}: {str(e)}")
    return jsonify({"success": False, "error": message}), 500


def handle_validation_error(message: str) -> tuple:
    """验证错误处理"""
    return jsonify({"success": False, "error": message}), 400


# Create API blueprint

# Create API blueprint
api = Blueprint("api", __name__)


# ============== Auth Routes ==============
@api.route("/register", methods=["POST"])
def register():
    """Register a new user"""
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")

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
    user_id = db.create_user(username, hash_password(password))
    if not user_id:
        return jsonify({"success": False, "error": "注册失败"})

    session["user_id"] = user_id
    session["username"] = username

    return jsonify({"success": True, "message": "注册成功", "username": username})


@api.route("/login", methods=["POST"])
def login():
    """User login"""
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = db.get_user_by_username(username)
    if not user:
        return jsonify({"success": False, "error": "用户名或密码错误"})

    stored_hash = user.get("password", "")

    # Verify password
    user_id = None
    if "$" in stored_hash:
        if verify_password(password, stored_hash):
            user_id = user.get("user_id")
    else:
        # Legacy hash - migrate to new format
        if stored_hash == hashlib.sha256(password.encode()).hexdigest():
            user_id = user.get("user_id")
            db.update_user_password(user.get("user_id"), hash_password(password))

    if not user_id:
        return jsonify({"success": False, "error": "用户名或密码错误"})

    session["user_id"] = user_id
    session["username"] = username

    return jsonify({"success": True, "message": "登录成功", "username": username})


@api.route("/logout", methods=["POST"])
def logout():
    """User logout"""
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})


@api.route("/check-login", methods=["GET"])
def check_login():
    """Check if user is logged in"""
    user_id = session.get("user_id")
    if user_id:
        return jsonify({"success": True, "logged_in": True, "username": session.get("username", "")})
    return jsonify({"success": True, "logged_in": False})


# ============== Fund Routes ==============
@api.route("/funds")
def get_funds():
    """Get user's fund list"""
    user_id = session.get("user_id")

    if user_id:
        holdings = db.get_holdings(user_id)
        codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
        if not codes:
            codes = []
    else:
        codes = []

    funds = fund_service.get_funds_for_user([], codes)

    return jsonify(
        {
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "funds": funds,
            "summary": fund_service.calculate_summary(funds),
        }
    )


@api.route("/fund/<code>")
def get_fund_detail(code):
    """Get single fund detail"""
    data = fetch_fund_data(code)
    analysis = analyze_fund(data)
    return jsonify(analysis)


@api.route("/report")
def get_report():
    """Generate daily report"""
    user_id = session.get("user_id")

    if user_id:
        holdings = db.get_holdings(user_id)
    else:
        holdings = []

    report = fund_service.get_report_for_user(holdings)
    return jsonify(report)


@api.route("/history")
def get_history():
    """Get historical reports"""
    DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")

    history = []
    if os.path.exists(DATA_DIR):
        for filename in sorted(os.listdir(DATA_DIR), reverse=True):
            if filename.startswith("fund_report_") and filename.endswith(".txt"):
                date_str = filename.replace("fund_report_", "").replace(".txt", "")
                filepath = os.path.join(DATA_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                history.append(
                    {
                        "date": date_str,
                        "filename": filename,
                        "preview": content[:200] + "..." if len(content) > 200 else content,
                    }
                )
    return jsonify(history[:30])


# ============== Holdings Routes ==============
@api.route("/holdings", methods=["GET", "POST", "DELETE"])
def manage_holdings():
    """Get or update user's holdings"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "请先登录", "need_login": True})

    if request.method == "GET":
        holdings = db.get_holdings(user_id)
        # Add daily change to each holding
        for h in holdings:
            if h.get("amount", 0) > 0:
                fund_data = fetch_fund_data(h["code"])
                daily_change = float(fund_data.get("gszzl", 0) or 0)
                h["daily_change"] = daily_change
                if daily_change != 0:
                    h["daily_profit"] = round(h.get("amount", 0) * daily_change / 100, 2)
        return jsonify({"success": True, "holdings": holdings})

    elif request.method == "POST":
        data = request.json
        code = data.get("code", "").strip()
        amount = float(data.get("amount", 0))

        if not code or len(code) != 6:
            return jsonify({"success": False, "error": "请输入6位基金代码"})

        # Validate amount
        if amount < 0:
            return jsonify({"success": False, "error": "持仓金额不能为负数"})
        
        # Zero amount = delete holding (sell all)
        if amount == 0:
            holdings = db.get_holdings(user_id)
            holdings = [h for h in holdings if h["code"] != code]
            db.save_holdings(user_id, holdings)
            return jsonify({"success": True, "message": "已清空该基金持仓"})

        # Verify fund exists
        fund_data = fetch_fund_data(code)
        if "error" in fund_data or not fund_data.get("fundcode"):
            return jsonify({"success": False, "error": "基金代码不存在"})

        holdings = db.get_holdings(user_id)

        # Update or add
        for h in holdings:
            if h["code"] == code:
                h["amount"] = amount
                h["name"] = fund_data.get("name", code)
                break
        else:
            holdings.append({"code": code, "name": fund_data.get("name", code), "amount": amount})

        db.save_holdings(user_id, holdings)
        return jsonify({"success": True, "message": "持仓已保存"})

    elif request.method == "DELETE":
        data = request.json
        code = data.get("code")

        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h["code"] != code]
        db.save_holdings(user_id, holdings)

        return jsonify({"success": True, "message": "持仓已删除"})


@api.route("/holdings/clear-all", methods=["POST"])
def clear_all_holdings():
    """Clear all holdings for current user or anonymous user"""
    # Get anonymous user identifier from header or body
    user_id = session.get("user_id")
    
    # If not logged in, try to get from header or body
    if not user_id:
        user_id = request.headers.get("X-User-ID")
    
    if not user_id:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
    
    # If still no user_id, return error
    if not user_id:
        return jsonify({"success": False, "error": "需要登录或提供用户ID"}), 400
    
    # Clear all holdings for this user
    conn = db.get_db()
    conn.execute("DELETE FROM holdings WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "所有持仓已清空"})


# ============== Other Routes ==============
@api.route("/news")
def get_news():
    """Get market hot news"""
    limit = request.args.get("limit", 8, type=int)
    news = fetch_market_news(limit)
    return jsonify({"success": True, "news": news})


@api.route("/sectors")
def get_sectors():
    """Get hot sectors"""
    limit = request.args.get("limit", 10, type=int)
    sectors = fetch_hot_sectors(limit)
    return jsonify({"success": True, "sectors": sectors})


@api.route("/advice")
def get_advice():
    """Get investment advice"""
    # 优先从数据库获取持仓，不依赖session
    from db import database
    db_instance = database
    user_id = session.get("user_id")
    
    if user_id:
        holdings = db_instance.get_holdings(user_id)
    else:
        # 如果没有session，尝试获取第一个用户的数据
        try:
            all_holdings = db_instance.get_all_holdings()
            if all_holdings:
                # 获取任意一个用户的持仓
                first_user = all_holdings[0].get("user_id")
                if first_user:
                    holdings = db_instance.get_holdings(first_user)
                else:
                    holdings = []
            else:
                holdings = []
        except Exception:
            holdings = []
    
    holdings_dict = {h["code"]: h for h in holdings}

    advice = fund_service.get_advice_for_user(holdings, holdings_dict)
    return jsonify({"success": True, "advice": advice})


@api.route("/fund-detail/<code>")
def get_fund_detail_full(code):
    """Get detailed fund info"""
    detail = get_fund_detail_info(code)
    return jsonify({"success": True, "detail": detail})


@api.route("/expected-return")
def get_expected_return():
    """Calculate expected return"""
    user_id = session.get("user_id")

    if user_id:
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h.get("amount", 0) > 0]
    else:
        holdings = []

    if not holdings:
        return jsonify({"success": False, "error": "暂无持仓", "expected_return": 0})

    codes = [h.get("code") for h in holdings]
    funds_data = []
    for code in codes:
        data = fetch_fund_data(code)
        if not data.get("error"):
            funds_data.append(data)

    result = calculate_expected_return(holdings, funds_data)
    return jsonify({"success": True, "result": result})


@api.route("/portfolio-analysis")
def get_portfolio_analysis():
    """Get portfolio analysis"""
    user_id = session.get("user_id")

    if user_id:
        holdings = db.get_holdings(user_id)
        holdings_dict = {h["code"]: h for h in holdings}
    else:
        holdings = []
        holdings_dict = {}

    analysis = fund_service.get_portfolio_analysis(holdings, holdings_dict)
    return jsonify({"success": True, "analysis": analysis})


@api.route("/import-screenshot", methods=["POST"])
def import_screenshot():
    """Import holdings from screenshot using OCR"""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        file.save(tmp_path)

    try:
        if EASYOCR_AVAILABLE:
            result = parse_image_easyocr(tmp_path)
            if result.get("success") and result.get("funds"):
                return jsonify({"success": True, "parsed": result["funds"], "method": "easyocr"})

        # Fall back to rule-based parsing
        return jsonify({"success": False, "error": "OCR failed", "message": "请手动输入基金代码和金额", "parsed": []})

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return jsonify({"success": False, "error": str(e), "parsed": []})
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@api.route("/import", methods=["POST"])
def import_holdings():
    """Import holdings from CSV/file or screenshot"""
    # Check if it's a file upload
    if "file" in request.files and request.files["file"]:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "Empty filename"}), 400

        # Save uploaded file temporarily
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            file.save(tmp_path)

        try:
            if EASYOCR_AVAILABLE:
                result = parse_image_easyocr(tmp_path)
                if result.get("success") and result.get("funds"):
                    return jsonify({"success": True, "parsed": result["funds"], "method": "easyocr"})

            return jsonify({"success": False, "error": "OCR failed", "parsed": []})
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return jsonify({"success": False, "error": str(e), "parsed": []})
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # Check if it's JSON data with format
    data = request.get_json()
    if data:
        if "data" in data and "format" in data:
            return jsonify({"success": True, "imported": len(data.get("data", []))})
        if "holdings" in data:
            return jsonify({"success": True, "imported": len(data.get("holdings", []))})

    return jsonify({"success": False, "error": "No data provided"}), 400
