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
# 生产环境禁止使用不安全的默认密钥
try:
    from src.config import get_config
    _config = get_config()
    JWT_SECRET = _config.security.jwt.secret
    JWT_ALGORITHM = _config.security.jwt.algorithm
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = _config.security.jwt.access_token_expire_minutes
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = _config.security.jwt.refresh_token_expire_days
    logger.info("JWT配置: 使用配置管理器")
except Exception:
    # 回退到环境变量
    JWT_SECRET = os.environ.get("FUND_DAILY_JWT_SECRET", "")
    if not JWT_SECRET:
        # 生产环境必须配置 JWT 密钥，禁止静默使用默认密钥
        _is_production = os.environ.get("FUND_DAILY_ENV") == "production"
        if _is_production:
            raise RuntimeError(
                "FUND_DAILY_JWT_SECRET 未配置！生产环境必须设置有效的 JWT 密钥。"
                "生成命令: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        # 开发环境使用不安全默认值但记录警告
        JWT_SECRET = "fund-daily-jwt-secret-change-in-production"
        logger.warning("JWT使用不安全默认值，仅限开发环境使用！")

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
        # 检查 Token 黑名单
        from src.cache.redis_cache import is_token_blacklisted
        if is_token_blacklisted(token):
            return False, None, "Token has been revoked"
        
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


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "verify_access_token",
    "verify_refresh_token",
    "get_user_from_token",
    "TokenType",
]
