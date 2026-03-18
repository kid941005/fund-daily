"""
认证相关 API 端点
"""

import hashlib
from flask import Blueprint, jsonify, request, session

from db import database_pg as db
from src.auth import hash_password as _hash_password, verify_password as _verify_password

auth_bp = Blueprint("auth", __name__)


def _generate_user_id():
    """生成用户ID"""
    import uuid
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16]


@auth_bp.route("/register", methods=["POST"])
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
        
        return jsonify({
            "success": True,
            "message": "注册成功",
            "user_id": user_id,
            "username": username
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"注册失败: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
    
    try:
        user = db.verify_user(username, password)
        if not user:
            return jsonify({"success": False, "error": "用户名或密码错误"}), 401
        
        # 设置 session
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        
        return jsonify({
            "success": True,
            "message": "登录成功",
            "username": user["username"]
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"登录失败: {str(e)}"}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({"success": True, "message": "登出成功"})


@auth_bp.route("/check-login")
def check_login():
    """检查登录状态"""
    user_id = session.get("user_id")
    username = session.get("username")
    
    if user_id and username:
        return jsonify({
            "success": True,
            "logged_in": True,
            "user_id": user_id,
            "username": username
        })
    else:
        return jsonify({
            "success": True,
            "logged_in": False
        })


@auth_bp.route("/password", methods=["POST"])
def change_password():
    """修改密码"""
    data = request.get_json() or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
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
        
        return jsonify({
            "success": True,
            "message": "密码修改成功"
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"修改密码失败: {str(e)}"}), 500
