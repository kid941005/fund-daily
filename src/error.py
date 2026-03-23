"""
统一错误处理模块

提供标准化的错误码、异常类和错误处理函数
"""

from enum import Enum
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """错误码枚举"""
    # 基金相关错误 (1000-1999)
    FUND_NOT_FOUND = 1001
    FUND_DATA_FETCH_FAILED = 1002
    FUND_SCORE_CALCULATION_FAILED = 1003
    FUND_DETAIL_FETCH_FAILED = 1004
    
    # 市场相关错误 (2000-2999)
    MARKET_DATA_FETCH_FAILED = 2001
    MARKET_SENTIMENT_ANALYSIS_FAILED = 2002
    COMMODITY_DATA_FETCH_FAILED = 2003
    HOT_SECTORS_FETCH_FAILED = 2004
    
    # 评分相关错误 (3000-3999)
    SCORE_WEIGHT_INVALID = 3001
    SCORE_DIMENSION_MISSING = 3002
    SCORE_CALCULATION_FAILED = 3003
    
    # 缓存相关错误 (4000-4999)
    CACHE_CONNECTION_FAILED = 4001
    CACHE_OPERATION_FAILED = 4002
    
    # 数据库相关错误 (5000-5999)
    DB_CONNECTION_FAILED = 5001
    DB_OPERATION_FAILED = 5002
    DB_QUERY_FAILED = 5003
    
    # 业务逻辑错误 (6000-6999)
    INVALID_INPUT = 6001
    UNAUTHORIZED = 6002
    OPERATION_NOT_ALLOWED = 6003
    RESOURCE_NOT_AVAILABLE = 6004
    RATE_LIMIT_EXCEEDED = 6005
    
    # 系统错误 (9000-9999)
    INTERNAL_ERROR = 9001
    EXTERNAL_API_FAILED = 9002
    TIMEOUT_ERROR = 9003


class ServiceError(Exception):
    """服务层异常基类"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause
        
        # 构建完整错误信息
        full_message = f"[{code.name}] {message}"
        if details:
            full_message += f" | Details: {details}"
        if cause:
            full_message += f" | Cause: {str(cause)}"
        
        super().__init__(full_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于API响应"""
        return {
            "error_code": self.code.value,
            "error_name": self.code.name,
            "message": self.message,
            "details": self.details,
        }


class FundServiceError(ServiceError):
    """基金服务异常"""
    pass


class MarketServiceError(ServiceError):
    """市场服务异常"""
    pass


class ScoreServiceError(ServiceError):
    """评分服务异常"""
    pass


class CacheServiceError(ServiceError):
    """缓存服务异常"""
    pass


def handle_service_error(error: ServiceError, logger: logging.Logger = None) -> Dict[str, Any]:
    """
    统一处理服务异常
    
    Args:
        error: 服务异常
        logger: 可选日志记录器
    
    Returns:
        错误响应字典
    """
    log = logger or logging.getLogger(__name__)
    
    # 记录错误日志
    log_level = logging.ERROR if error.code.value >= 9000 else logging.WARNING
    log.log(log_level, f"Service error: {error}")
    
    # 返回标准错误响应
    return error.to_dict()


def create_error_response(
    code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    http_status: int = 500
) -> tuple:
    """
    创建标准错误响应（用于API层）
    
    Args:
        code: 错误码
        message: 错误消息
        details: 错误详情
        http_status: HTTP状态码
    
    Returns:
        (response_dict, status_code) 元组
    """
    error_response = {
        "success": False,
        "error": {
            "code": code.value,
            "name": code.name,
            "message": message,
            "details": details or {},
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return error_response, http_status


# 便捷错误创建函数
def fund_not_found(fund_code: str) -> FundServiceError:
    return FundServiceError(
        ErrorCode.FUND_NOT_FOUND,
        f"基金 {fund_code} 未找到",
        {"fund_code": fund_code}
    )


def fund_data_fetch_failed(fund_code: str, cause: Exception = None) -> FundServiceError:
    return FundServiceError(
        ErrorCode.FUND_DATA_FETCH_FAILED,
        f"基金 {fund_code} 数据获取失败",
        {"fund_code": fund_code},
        cause
    )


def market_data_fetch_failed(cause: Exception = None) -> MarketServiceError:
    return MarketServiceError(
        ErrorCode.MARKET_DATA_FETCH_FAILED,
        "市场数据获取失败",
        cause=cause
    )


def cache_operation_failed(operation: str, key: str, cause: Exception = None) -> CacheServiceError:
    return CacheServiceError(
        ErrorCode.CACHE_OPERATION_FAILED,
        f"缓存操作失败: {operation}",
        {"operation": operation, "key": key},
        cause
    )


def rate_limit_exceeded(limit: int, remaining: int, reset: int, retry_after: int) -> ServiceError:
    """速率限制超出错误"""
    return ServiceError(
        ErrorCode.RATE_LIMIT_EXCEEDED,
        f"请求过于频繁，请等待{retry_after}秒后重试",
        {
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
            "retry_after": retry_after,
            "window_seconds": retry_after
        }
    )