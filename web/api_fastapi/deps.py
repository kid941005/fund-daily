"""
Dependency Injection for FastAPI
Handles authentication (Session + JWT)
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.error import ErrorCode, create_error_response
from src.jwt_auth import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    verify_access_token,
    verify_refresh_token,
)

logger = logging.getLogger(__name__)


class AuthenticatedUser:
    """Authenticated user context"""

    def __init__(self, user_id: str, username: str, auth_method: str = "jwt"):
        self.user_id = user_id
        self.username = username
        self.auth_method = auth_method


def _get_token_from_request(request: Request) -> Optional[str]:
    """Extract token from request (header or cookie)"""
    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Fallback to cookie
    return request.cookies.get("access_token")


def _get_user_from_jwt(request: Request) -> Tuple[bool, Optional[dict], Optional[str]]:
    """Verify JWT token and return payload"""
    token = _get_token_from_request(request)
    if not token:
        return False, None, "No token provided"

    return verify_access_token(token)


def _get_user_from_session(request: Request) -> Tuple[bool, Optional[str], Optional[str]]:
    """Get user from session cookie"""
    user_id = request.cookies.get("session")
    if not user_id:
        return False, None, "No session"
    return True, user_id, None


async def get_current_user(request: Request) -> AuthenticatedUser:
    """
    Get current authenticated user.
    Supports both JWT Bearer token and Session cookie.

    Raises HTTPException if not authenticated.
    """
    # Try JWT first
    is_valid, payload, error = _get_user_from_jwt(request)
    if is_valid:
        return AuthenticatedUser(user_id=payload.get("sub"), username=payload.get("username"), auth_method="jwt")

    # Fallback to session
    is_valid, user_id, error = _get_user_from_session(request)
    if is_valid:
        # Get username from database
        from db import database_pg as db

        user = db.get_user_by_id(user_id)
        if user:
            return AuthenticatedUser(user_id=user_id, username=user.get("username"), auth_method="session")

    raise HTTPException(
        status_code=401,
        detail=create_error_response(code=ErrorCode.UNAUTHORIZED, message="请先登录", http_status=401)[0],
    )


async def get_current_user_optional(request: Request) -> Optional[AuthenticatedUser]:
    """
    Get current user if authenticated, otherwise return None.
    Does not raise exception for unauthenticated requests.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def require_auth(request: Request) -> dict:
    """
    Require authentication for an endpoint.
    Returns user info dict if authenticated.
    Raises JSONResponse with 401 if not authenticated.
    """
    # Try JWT first
    is_valid, payload, error = _get_user_from_jwt(request)
    if is_valid:
        return {"user_id": payload.get("sub"), "username": payload.get("username"), "auth_method": "jwt"}

    # Fallback to session
    is_valid, user_id, error = _get_user_from_session(request)
    if is_valid:
        from db import database_pg as db

        user = db.get_user_by_id(user_id)
        if user:
            return {"user_id": user_id, "username": user.get("username"), "auth_method": "session"}

    raise HTTPException(
        status_code=401,
        detail={"success": False, "error": "请先登录", "need_login": True, "error_code": "UNAUTHORIZED"},
    )


def create_tokens_for_user(user_id: str, username: str) -> dict:
    """Create token pair for user (JWT tokens)"""
    return create_token_pair(user_id, username)


def set_session_cookie(response: JSONResponse, user_id: str, username: str):
    """Set session cookie on response (for backward compatibility)"""
    from .config import get_fastapi_config

    config = get_fastapi_config()

    response.set_cookie(
        key="session",
        value=user_id,
        httponly=True,
        samesite="Lax",
        secure=config.security.secure_cookies,
        max_age=60 * 60 * 24 * 7,  # 7 days
    )
