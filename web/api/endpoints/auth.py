"""
认证相关 API 端点
支持 Session 和 JWT Token 两种认证方式
"""

import hashlib
from flask import Blueprint, jsonify, request, session

from db import database_pg as db
from src.auth import hash_password as _hash_password, verify_password as _verify_password
from src.jwt_auth import create_token_pair, verify_access_token, get_token_from_header
from web.api.rate_limiter import auth_limit

auth_bp = Blueprint("auth", __name__)


def _generate_user_id():
    """生成用户ID"""
    import uuid
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16]


@auth_bp.route("/register", methods=["POST"])
@auth_limit()
def register():
    """用户注册"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "密码长度至少6位"}), 400
    
    try:
        # 检查用户名是否已存在
        existing = db.get_user_by_username(username)
        if existing:
            return jsonify({"success": False, "error": "用户名已存在"}), 400
        
        # 创建新用户
        user_id = _generate_user_id()
        password_hash = _hash_password(password)
        db.create_user(user_id, username, password_hash)
        
        # 注册成功后自动登录，生成 JWT token
        tokens = create_token_pair(user_id, username)
        
        # 同时设置 session（兼容旧版）
        session["user_id"] = user_id
        session["username"] = username
        
        return jsonify({
            "success": True,
            "message": "注册成功",
            "user_id": user_id,
            "username": username,
            **tokens
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"注册失败: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
@auth_limit()
def login():
    """用户登录
    
    返回 JWT token，支持以下认证方式:
    - Header: Authorization: Bearer <token>
    - Cookie: access_token
    """
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
    
    try:
        user = db.verify_user(username, password)
        if not user:
            return jsonify({"success": False, "error": "用户名或密码错误"}), 401
        
        # 生成 JWT token pair
        tokens = create_token_pair(user["user_id"], user["username"])
        
        # 同时设置 session（兼容旧版）
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        
        return jsonify({
            "success": True,
            "message": "登录成功",
            "username": user["username"],
            **tokens
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"登录失败: {str(e)}"}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """用户登出
    
    清除 session，token 的失效由客户端处理
    """
    session.clear()
    return jsonify({"success": True, "message": "登出成功"})


@auth_bp.route("/check-login")
def check_login():
    """检查登录状态
    
    同时支持 session 和 JWT token 认证
    """
    # 优先检查 JWT token
    token = get_token_from_header()
    if token:
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return jsonify({
                "success": True,
                "logged_in": True,
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "auth_method": "jwt"
            })
    
    # 回退到 session
    user_id = session.get("user_id")
    username = session.get("username")
    
    if user_id and username:
        return jsonify({
            "success": True,
            "logged_in": True,
            "user_id": user_id,
            "username": username,
            "auth_method": "session"
        })
    else:
        return jsonify({
            "success": True,
            "logged_in": False
        })


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """刷新 Access Token
    
    使用 refresh_token 获取新的 access_token
    """
    data = request.get_json() or {}
    refresh_token_val = data.get("refresh_token")
    
    if not refresh_token_val:
        # 尝试从 cookie 获取
        refresh_token_val = request.cookies.get("refresh_token")
    
    if not refresh_token_val:
        return jsonify({"success": False, "error": "缺少 refresh_token"}), 400
    
    from src.jwt_auth import verify_refresh_token, create_access_token
    is_valid, payload, error = verify_refresh_token(refresh_token_val)
    
    if not is_valid:
        return jsonify({"success": False, "error": error or "refresh_token 无效"}), 401
    
    # 生成新的 access token
    new_access_token = create_access_token(payload.get("sub"), payload.get("username"))
    
    return jsonify({
        "success": True,
        "access_token": new_access_token,
        "token_type": "Bearer",
        "expires_in": 60 * 60  # 1小时（秒）
    })


@auth_bp.route("/password", methods=["POST"])
def change_password():
    """修改密码"""
    data = request.get_json() or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    
    # 优先从 JWT token 获取 user_id
    token = get_token_from_header()
    if token:
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            user_id = payload.get("sub")
        else:
            user_id = session.get("user_id")
    else:
        user_id = session.get("user_id")
    
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    if not old_password or not new_password:
        return jsonify({"success": False, "error": "密码不能为空"}), 400
    
    if len(new_password) < 6:
        return jsonify({"success": False, "error": "新密码长度至少6位"}), 400
    
    try:
        # 验证旧密码
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "用户不存在"}), 404
        
        if not _verify_password(old_password, user["password"]):
            return jsonify({"success": False, "error": "原密码错误"}), 400
        
        # 更新密码
        new_hash = _hash_password(new_password)
        db.update_user_password(user_id, new_hash)
        
        # 修改密码后，使旧 token 失效（通过更新序列号）
        # 当前实现：客户端需要在修改密码后重新登录
        
        return jsonify({
            "success": True,
            "message": "密码修改成功，请重新登录"
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"修改密码失败: {str(e)}"}), 500
