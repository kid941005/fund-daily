"""用户管理模块"""
from .pool import get_db, get_cursor

# 用户操作
def get_user_by_username(username):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return dict(cursor.fetchone()) if cursor.rowcount > 0 else None

def verify_user(username, password):
    """验证用户登录"""
    from src.auth import verify_password
    user = get_user_by_username(username)
    if not user:
        return None
    if verify_password(password, user.get("password", "")):
        return user
    return None

def get_user_by_id(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return dict(cursor.fetchone()) if cursor.rowcount > 0 else None

def create_user(user_id, username, password_hash):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute(
                "INSERT INTO users (user_id, username, password) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (user_id, username, password_hash)
            )
            conn.commit()

def update_user_password(user_id, new_password_hash):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("UPDATE users SET password = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", 
                         (new_password_hash, user_id))
            conn.commit()

# 持仓操作