"""
统一错误处理中间件

为 Flask 应用提供标准化的错误处理
"""

import traceback
import logging
from typing import Dict, Any, Optional, Callable
from flask import jsonify, request, g
from werkzeug.exceptions import HTTPException

from src.error import ErrorCode, ServiceError, create_error_response

logger = logging.getLogger(__name__)


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用错误处理"""
        # 注册错误处理器
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(405, self.handle_method_not_allowed)
        app.register_error_handler(429, self.handle_rate_limit)
        app.register_error_handler(500, self.handle_internal_error)
        
        # 注册自定义异常处理器
        app.register_error_handler(ServiceError, self.handle_service_error)
        # 注意：不要注册 catch-all Exception handler，会导致 HTTPException 被意外拦截
        # 只保留特定状态码的处理器
        
        # 添加请求上下文销毁时的清理
        app.teardown_request(self.teardown_request)
    
    def teardown_request(self, exception=None):
        """请求结束时清理资源"""
        pass
    
    def _get_request_context(self) -> Dict[str, Any]:
        """获取请求上下文信息"""
        context = {
            "method": request.method,
            "path": request.path,
            "endpoint": request.endpoint,
            "remote_addr": request.remote_addr,
            "user_agent": request.user_agent.string if request.user_agent else None,
        }
        
        # 添加请求ID
        if hasattr(g, 'request_id'):
            context["request_id"] = g.request_id
        
        return context
    
    def handle_bad_request(self, error: HTTPException) -> tuple:
        """处理400错误"""
        logger.warning(f"Bad request: {error.description}", extra=self._get_request_context())
        
        response = create_error_response(
            code=ErrorCode.INVALID_INPUT,
            message=error.description or "请求参数无效",
            http_status=400,
            details={"validation_errors": getattr(error, 'validation_errors', [])}
        )
        
        return jsonify(response), 400
    
    def handle_unauthorized(self, error: HTTPException) -> tuple:
        """处理401错误"""
        logger.warning(f"Unauthorized: {error.description}", extra=self._get_request_context())
        
        response = create_error_response(
            code=ErrorCode.OPERATION_NOT_ALLOWED,
            message=error.description or "未授权访问",
            http_status=401,
            details={"auth_required": True}
        )
        
        return jsonify(response), 401
    
    def handle_forbidden(self, error: HTTPException) -> tuple:
        """处理403错误"""
        logger.warning(f"Forbidden: {error.description}", extra=self._get_request_context())
        
        response = create_error_response(
            code=ErrorCode.OPERATION_NOT_ALLOWED,
            message=error.description or "禁止访问",
            http_status=403,
            details={"permission_denied": True}
        )
        
        return jsonify(response), 403
    
    def handle_not_found(self, error: HTTPException) -> tuple:
        """处理404错误"""
        logger.info(f"Not found: {request.path}", extra=self._get_request_context())
        
        response = create_error_response(
            code=ErrorCode.RESOURCE_NOT_AVAILABLE,
            message="请求的资源不存在",
            http_status=404,
            details={"path": request.path}
        )
        
        return jsonify(response), 404
    
    def handle_method_not_allowed(self, error: HTTPException) -> tuple:
        """处理405错误"""
        logger.warning(f"Method not allowed: {request.method} {request.path}", 
                      extra=self._get_request_context())
        
        response = create_error_response(
            code=ErrorCode.OPERATION_NOT_ALLOWED,
            message=f"不支持 {request.method} 方法",
            http_status=405,
            details={
                "allowed_methods": error.valid_methods if hasattr(error, 'valid_methods') else [],
                "requested_method": request.method
            }
        )
        
        return jsonify(response), 405
    
    def handle_rate_limit(self, error: HTTPException) -> tuple:
        """处理429错误"""
        logger.warning(f"Rate limit exceeded: {request.path}", extra=self._get_request_context())
        
        response = create_error_response(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="请求过于频繁，请稍后再试",
            http_status=429,
            details={
                "retry_after": getattr(error, 'retry_after', 60),
                "limit": getattr(error, 'limit', None)
            }
        )
        
        return jsonify(response), 429
    
    def handle_service_error(self, error: ServiceError) -> tuple:
        """处理业务逻辑错误"""
        from src.error import handle_service_error
        
        logger.error(f"Service error: {error}", extra=self._get_request_context())
        
        # 使用统一的业务错误处理
        response = handle_service_error(error, logger)
        
        return jsonify(response), response.get('status', 500)
    
    def handle_internal_error(self, error: Exception) -> tuple:
        """处理500错误"""
        # 记录完整的错误堆栈
        error_traceback = traceback.format_exc()
        logger.error(f"Internal server error: {error}\n{error_traceback}", 
                    extra=self._get_request_context())
        
        # 生产环境隐藏详细错误信息
        from src.config import get_config
        config = get_config()
        
        if config.is_production():
            message = "服务器内部错误"
            details = None
        else:
            message = str(error)
            details = {
                "error_type": error.__class__.__name__,
                "traceback": error_traceback.split('\n')[-10:]  # 最后10行
            }
        
        response = create_error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message=message,
            details=details,
            http_status=500,
        )
        
        return jsonify(response), 500
    
    def handle_generic_error(self, error: Exception) -> tuple:
        """处理其他未捕获的异常"""
        # 如果是HTTP异常，交给Flask处理
        if isinstance(error, HTTPException):
            return error
        
        # 否则按内部错误处理
        return self.handle_internal_error(error)


# 单例实例
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """获取错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def init_error_handler(app):
    """初始化错误处理器"""
    handler = get_error_handler()
    handler.init_app(app)
    return handler