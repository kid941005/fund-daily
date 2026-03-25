"""
Error Handler Middleware for FastAPI
"""

import logging
from typing import Union

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.error import ErrorCode, create_error_response

logger = logging.getLogger(__name__)


class APIException(HTTPException):
    """Custom API exception with error code support"""
    def __init__(
        self, 
        status_code: int, 
        error_code: ErrorCode, 
        message: str, 
        details: dict = None
    ):
        self.error_code = error_code
        self.error_message = message
        self.error_details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "code": error_code.value,
                    "name": error_code.name,
                    "message": message,
                    "details": self.error_details,
                }
            }
        )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException"""
    if isinstance(exc, APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code.value,
                    "name": exc.error_code.name,
                    "message": exc.error_message,
                    "details": exc.error_details,
                }
            }
        )
    
    # Handle standard HTTPException
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "name": "HTTP_ERROR",
                "message": str(exc.detail) if hasattr(exc, 'detail') else "HTTP Error",
                "details": {}
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    error_response, status_code = create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message=f"内部服务器错误: {str(exc)}",
        http_status=500
    )
    
    return JSONResponse(status_code=status_code, content=error_response)


def create_api_error(
    status_code: int,
    error_code: ErrorCode,
    message: str,
    details: dict = None
) -> APIException:
    """Create an API exception"""
    return APIException(status_code, error_code, message, details)


def rate_limit_exceeded(limit: int, remaining: int, reset: int, retry_after: int):
    """Raise rate limit exceeded exception"""
    from src.error import ErrorCode
    raise APIException(
        status_code=429,
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message=f"请求过于频繁，请等待{retry_after}秒后重试",
        details={
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
            "retry_after": retry_after,
        }
    )
