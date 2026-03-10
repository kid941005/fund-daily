"""
共享工具模块
提供通用函数，避免重复导入
"""
from functools import wraps
from flask import jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({"success": False, "error": "请先登录"}), 401
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    """密码哈希"""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(password, password_hash):
    """验证密码"""
    return check_password_hash(password_hash, password)

def get_current_user_id():
    """获取当前用户ID"""
    return session.get('user_id')

def get_current_username():
    """获取当前用户名"""
    return session.get('username')
