"""
JWT Token 认证模块
支持 token 生成、验证、刷新
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

import jwt

from src.error import ErrorCode, create_error_response

logger = logging.getLogger(__name__)

# ============== Config ==============
# 优先使用配置管理器，否则使用环境变量
try:
    from src.config import get_config
    _config = get_config()
    JWT_SECRET = _config.security.jwt.secret
    JWT_ALGORITHM = _config.security.jwt.algorithm
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = _config.security.jwt.access_token_expire_minutes
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = _config.security.jwt.refresh_token_expire_days
    logger.info("JWT配置: 使用配置管理器")
except Exception:
    JWT_SECRET = os.environ.get("FUND_DAILY_JWT_SECRET", "fund-daily-jwt-secret-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("FUND_DAILY_JWT_EXPIRE_MINUTES", 60))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("FUND_DAILY_JWT_REFRESH_DAYS", 7))
    logger.info("JWT配置: 使用环境变量")


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


def _get_utc_now() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, username: str) -> str:
    """
    创建访问令牌 (Access Token)
    
    Args:
        user_id: 用户ID
        username: 用户名
        
    Returns:
        JWT token 字符串
    """
    now = _get_utc_now()
    expire = now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "username": username,
        "type": TokenType.ACCESS,
        "iat": now,
        "exp": expire,
        "iss": "fund-daily"
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.debug(f"Created access token for user {username}, expires at {expire}")
    return token


def create_refresh_token(user_id: str, username: str) -> str:
    """
    创建刷新令牌 (Refresh Token)
    有效期更长，用于获取新的 access token
    
    Args:
        user_id: 用户ID
        username: 用户名
        
    Returns:
        JWT refresh token 字符串
    """
    now = _get_utc_now()
    expire = now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": user_id,
        "username": username,
        "type": TokenType.REFRESH,
        "iat": now,
        "exp": expire,
        "iss": "fund-daily"
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.debug(f"Created refresh token for user {username}, expires at {expire}")
    return token


def create_token_pair(user_id: str, username: str) -> Dict[str, Any]:
    """
    创建令牌对 (access + refresh)
    
    Returns:
        包含 access_token, refresh_token, expires_in 的字典
    """
    return {
        "access_token": create_access_token(user_id, username),
        "refresh_token": create_refresh_token(user_id, username),
        "token_type": "Bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 秒
    }


def verify_token(token: str, expected_type: str = TokenType.ACCESS) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    验证 JWT token
    
    Args:
        token: JWT token 字符串
        expected_type: 期望的 token 类型
        
    Returns:
        (is_valid, payload, error_message)
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "exp", "iat"]}
        )
        
        # 验证 token 类型
        if payload.get("type") != expected_type:
            return False, None, f"Token type mismatch: expected {expected_type}"
        
        # 验证签发者
        if payload.get("iss") != "fund-daily":
            return False, None, "Invalid token issuer"
        
        return True, payload, None
        
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired"
    except jwt.InvalidTokenError as e:
        return False, None, f"Invalid token: {str(e)}"


def verify_access_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """验证 access token"""
    return verify_token(token, TokenType.ACCESS)


def verify_refresh_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """验证 refresh token"""
    return verify_token(token, TokenType.REFRESH)


def decode_token_unsafe(token: str) -> Optional[Dict[str, Any]]:
    """
    不验证签名，仅解析 payload（用于日志/调试）
    
    WARNING: 不要用于认证决策！
    """
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_signature": False, "verify_exp": False}
        )
    except Exception:
        return None


def get_token_from_header() -> Optional[str]:
    """
    从 Flask 请求头中提取 Bearer token
    
    Returns:
        token 字符串或 None
    """
    from flask import request
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def get_token_from_cookie() -> Optional[str]:
    """从 Cookie 中提取 JWT token"""
    from flask import request
    return request.cookies.get("access_token")


def get_user_from_token(token: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    从 token 中提取用户信息
    
    Returns:
        (is_valid, user_id, error_message)
    """
    is_valid, payload, error = verify_access_token(token)
    if not is_valid:
        return False, None, error
    
    return True, payload.get("sub"), None


# ============== Flask Decorator ==============
def jwt_required(f):
    """
    JWT 认证装饰器
    支持从 Header (Authorization: Bearer xxx) 或 Cookie 获取 token
    验证通过后将 user_id, username 注入 request
    """
    from functools import wraps
    from flask import request, g
    from flask import jsonify
    
    @wraps(f)
    def decorated(*args, **kwargs):
        # 尝试从 header 获取 token
        token = get_token_from_header()
        
        # 如果 header 没有，尝试从 cookie 获取
        if not token:
            token = get_token_from_cookie()
        
        if not token:
            return jsonify({
                "success": False,
                "error": "缺少认证令牌",
                "need_auth": True,
                "error_code": "MISSING_TOKEN"
            }), 401
        
        is_valid, payload, error = verify_access_token(token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error or "认证失败",
                "need_auth": True,
                "error_code": "INVALID_TOKEN"
            }), 401
        
        # 注入用户信息到 request context
        g.user_id = payload.get("sub")
        g.username = payload.get("username")
        g.token_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated


def jwt_optional(f):
    """
    可选的 JWT 认证装饰器
    如果提供了有效 token 则注入用户信息，否则继续执行
    """
    from functools import wraps
    from flask import request, g
    
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header() or get_token_from_cookie()
        
        if token:
            is_valid, payload, _ = verify_access_token(token)
            if is_valid:
                g.user_id = payload.get("sub")
                g.username = payload.get("username")
                g.token_payload = payload
                g.is_authenticated = True
            else:
                g.is_authenticated = False
        else:
            g.is_authenticated = False
        
        return f(*args, **kwargs)
    
    return decorated


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "verify_access_token",
    "verify_refresh_token",
    "get_user_from_token",
    "jwt_required",
    "jwt_optional",
    "get_token_from_header",
    "TokenType",
]
