"""
Authentication Router
"""

import hashlib
import logging
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from db import database_pg as db
from src.auth import hash_password as _hash_password
from src.auth import verify_password as _verify_password
from src.error import ErrorCode
from src.jwt_auth import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    verify_access_token,
    verify_refresh_token,
)
from web.api_fastapi.deps import AuthenticatedUser, get_current_user
from web.api_fastapi.middleware.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["认证"])


# Request/Response Models
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: Optional[str] = Field(default=None, max_length=100)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = Field(default=None, max_length=500)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    验证密码强度

    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "密码长度至少8位"

    if len(password) > 128:
        return False, "密码长度不能超过128位"

    # 检查是否包含数字
    if not any(c.isdigit() for c in password):
        return False, "密码必须包含数字"

    # 检查是否包含小写字母
    if not any(c.islower() for c in password):
        return False, "密码必须包含小写字母"

    # 检查是否包含大写字母
    if not any(c.isupper() for c in password):
        return False, "密码必须包含大写字母"

    # 检查常见弱密码（扩展列表）
    weak_passwords = [
        # 纯数字
        "123456",
        "12345678",
        "123456789",
        "1234567890",
        "111111",
        "222222",
        "333333",
        "444444",
        "555555",
        "666666",
        "777777",
        "888888",
        "999999",
        "000000",
        "012345",
        "0123456",
        "01234567",
        # 键盘序列
        "qwerty",
        "qwertyuiop",
        "asdfgh",
        "zxcvbn",
        "qwerty123",
        "qwerty123456",
        "abcdef",
        "abcdefg",
        "abcdefgh",
        "password",
        "password1",
        "password123",
        "password1234",
        "password12345",
        "passw0rd",
        "P@ssw0rd",
        "P@ssword",
        # 常见单词
        "admin",
        "admin123",
        "administrator",
        "root",
        "root123",
        "welcome",
        "welcome123",
        "welcome1",
        "login",
        "login123",
        "master",
        "master123",
        "letmein",
        "abc123",
        "abcd1234",
        "iloveyou",
        "princess",
        "football",
        "monkey",
        "dragon",
        "shadow",
        "sunshine",
        "123123",
        "654321",
        "666666",
        "696969",
        "superman",
        "batman",
        "spiderman",
        "harleyquinn",
        # 用户名相关
        "username",
        "user123",
        "test123",
        "guest",
        "guest123",
        # 日期相关
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2020pass",
        "2021pass",
        "2022pass",
        # 简短密码
        "pass",
        "pass1",
        "pass12",
        "pass123",
        "temp",
        "temp123",
        "test",
        "test123",
        "demo",
        "demo123",
    ]
    if password.lower() in weak_passwords:
        return False, "密码过于简单，请使用更复杂的密码"

    return True, ""


def _generate_user_id():
    """Generate user ID"""
    import uuid

    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16]


@router.post("/login")
async def login(request: Request, response: Response, data: LoginRequest):
    """User login - supports both session and JWT"""
    # Check rate limit
    limit_result = check_rate_limit(request, "auth")
    if not limit_result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "error": f"请求过于频繁，请等待{limit_result['retry_after']}秒后重试",
                "limit": limit_result["limit"],
                "remaining": limit_result["remaining"],
                "reset": limit_result["reset"],
                "retry_after": limit_result["retry_after"],
            },
        )

    username = data.username.strip()
    password = data.password

    if not username or not password:
        return JSONResponse(status_code=400, content={"success": False, "error": "用户名和密码不能为空"})

    # 检查账户是否被锁定
    from src.cache.redis_cache import get_login_fail_count, increment_login_fail_count, is_account_locked

    if is_account_locked(username):
        fail_count = get_login_fail_count(username)
        return JSONResponse(
            status_code=429,
            content={"success": False, "error": f"登录失败次数过多，账户已锁定15分钟。请{fail_count}秒后重试。"},
        )

    try:
        user = db.verify_user(username, password)
        if not user:
            # 登录失败，增加失败次数
            fail_count = increment_login_fail_count(username)
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "用户名或密码错误",
                    "fail_count": fail_count,
                    "remaining_attempts": max(0, 5 - fail_count),
                },
            )

        # Generate JWT tokens
        tokens = create_token_pair(user["user_id"], user["username"])

        # 登录成功，重置失败次数
        from src.cache.redis_cache import reset_login_fail_count

        reset_login_fail_count(username)

        # Set session cookie (for backward compatibility)
        response.set_cookie(
            key="session", value=user["user_id"], httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7
        )

        return {"success": True, "message": "登录成功", "username": user["username"], **tokens}
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"登录失败: {str(e)}"})


@router.post("/logout")
async def logout(request: Request, response: Response):
    """User logout - clear session and revoke JWT token"""
    # 获取 token 并加入黑名单
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        from src.cache.redis_cache import add_token_to_blacklist

        add_token_to_blacklist(token)

    # 清除 session cookie
    response.delete_cookie("session")

    return {"success": True, "message": "登出成功，已撤销 Token"}


@router.get("/check-login")
async def check_login(request: Request):
    """Check login status - supports both session and JWT"""
    # Try JWT first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, error = verify_access_token(token)
        if is_valid:
            return {
                "success": True,
                "logged_in": True,
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "auth_method": "jwt",
            }

    # Fallback to session
    user_id = request.cookies.get("session")
    if user_id:
        user = db.get_user_by_id(user_id)
        if user:
            return {
                "success": True,
                "logged_in": True,
                "user_id": user_id,
                "username": user.get("username"),
                "auth_method": "session",
            }

    return {"success": True, "logged_in": False}


@router.post("/register")
async def register(request: Request, response: Response, data: RegisterRequest):
    """User registration"""
    # Check rate limit
    limit_result = check_rate_limit(request, "auth")
    if not limit_result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={"success": False, "error": f"请求过于频繁，请等待{limit_result['retry_after']}秒后重试"},
        )

    username = data.username.strip()
    password = data.password

    if not username or not password:
        return JSONResponse(status_code=400, content={"success": False, "error": "用户名和密码不能为空"})

    # 密码强度校验
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        return JSONResponse(status_code=400, content={"success": False, "error": error_msg})

    try:
        # Check if username exists
        existing = db.get_user_by_username(username)
        if existing:
            return JSONResponse(status_code=400, content={"success": False, "error": "用户名已存在"})

        # Create new user
        user_id = _generate_user_id()
        password_hash = _hash_password(password)
        db.create_user(user_id, username, password_hash)

        # Generate tokens
        tokens = create_token_pair(user_id, username)

        # Set session cookie
        response.set_cookie(key="session", value=user_id, httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7)

        return {"success": True, "message": "注册成功", "user_id": user_id, "username": username, **tokens}
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"注册失败: {str(e)}"})


@router.post("/refresh")
async def refresh_token(request: Request, data: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    refresh_token_val = data.refresh_token

    if not refresh_token_val:
        # Try to get from cookie
        refresh_token_val = request.cookies.get("refresh_token")

    if not refresh_token_val:
        return JSONResponse(status_code=400, content={"success": False, "error": "缺少 refresh_token"})

    is_valid, payload, error = verify_refresh_token(refresh_token_val)

    if not is_valid:
        return JSONResponse(status_code=401, content={"success": False, "error": error or "refresh_token 无效"})

    # Create new access token
    new_access_token = create_access_token(payload.get("sub"), payload.get("username"))

    return {"success": True, "access_token": new_access_token, "token_type": "Bearer", "expires_in": 60 * 60}  # 1 hour


@router.post("/password")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: dict = Depends(lambda request: _get_user_from_request(request)),
):
    """Change user password"""
    old_password = data.old_password
    new_password = data.new_password

    # Get user_id from request (JWT or session)
    user_id = _get_user_from_request(request)

    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "error": "请先登录"})

    if not old_password or not new_password:
        return JSONResponse(status_code=400, content={"success": False, "error": "密码不能为空"})

    # 新密码强度校验
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        return JSONResponse(status_code=400, content={"success": False, "error": error_msg})

    try:
        # Verify old password
        user = db.get_user_by_id(user_id)
        if not user:
            return JSONResponse(status_code=404, content={"success": False, "error": "用户不存在"})

        if not _verify_password(old_password, user["password"]):
            return JSONResponse(status_code=400, content={"success": False, "error": "原密码错误"})

        # Update password
        new_hash = _hash_password(new_password)
        db.update_user_password(user_id, new_hash)

        return {"success": True, "message": "密码修改成功，请重新登录"}
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"修改密码失败: {str(e)}"})


def _get_user_from_request(request: Request) -> Optional[str]:
    """Extract user_id from request (JWT or session)"""
    # Try JWT first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, error = verify_access_token(token)
        if is_valid:
            return payload.get("sub")

    # Fallback to session
    return request.cookies.get("session")
