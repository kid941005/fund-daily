"""
认证蓝图
处理用户注册、登录、登出
"""
from flask import Blueprint, request, jsonify, session
from .utils import login_required, hash_password, verify_password

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

@auth_bp.route('/register', methods=['POST'])
def register():
    """注册新用户"""
    from db import database as db
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"})
    
    if len(username) < 2 or len(username) > 20:
        return jsonify({"success": False, "error": "用户名长度需2-20个字符"})
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "密码长度至少6位"})
    
    # 检查用户名是否存在
    existing = db.get_user_by_username(username)
    if existing:
        return jsonify({"success": False, "error": "用户名已存在"})
    
    # 创建用户
    user_id = db.create_user(username, hash_password(password))
    if not user_id:
        return jsonify({"success": False, "error": "注册失败"})
    
    # 自动登录
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": "注册成功",
        "username": username
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    from db import database as db
    
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # 从数据库查找用户
    user = db.get_user_by_username(username)
    
    if not user:
        return jsonify({"success": False, "error": "用户名或密码错误"})
    
    stored_hash = user.get('password', '')
    
    # 验证密码
    user_id = None
    if '$' in stored_hash:
        if verify_password(password, stored_hash):
            user_id = user.get('user_id')
    else:
        # 旧格式：SHA256
        import hashlib
        if stored_hash == hashlib.sha256(password.encode()).hexdigest():
            user_id = user.get('user_id')
            # 升级到新格式
            db.update_user_password(user.get('user_id'), hash_password(password))
    
    if not user_id:
        return jsonify({"success": False, "error": "用户名或密码错误"})
    
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": "登录成功",
        "username": username
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})

@auth_bp.route('/check-login', methods=['GET'])
def check_login():
    """检查登录状态"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    if user_id:
        return jsonify({
            "success": True,
            "logged_in": True,
            "user_id": user_id,
            "username": username
        })
    
    return jsonify({
        "success": True,
        "logged_in": False
    })
