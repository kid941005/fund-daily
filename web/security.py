"""
安全 HTTP 头中间件
为 Flask 应用添加安全相关的 HTTP 头
"""

import uuid
import re
from flask import request, g


class SecurityHeaders:
    """安全 HTTP 头中间件"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用"""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
    
    def _before_request(self):
        """请求前处理"""
        # 记录请求 ID 用于追踪
        g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        
        # 检查 Content-Type（仅对 POST/PUT/PATCH）
        if request.method in ['POST', 'PUT', 'PATCH']:
            # 文件上传端点例外（需要 multipart/form-data）
            if request.path in ['/api/holdings/import-screenshot', '/api/holdings/import_screenshot',
                                '/api/import-screenshot', '/api/import_screenshot',
                                '/api/import']:
                # 允许 multipart/form-data 用于文件上传
                pass  # 允许所有 Content-Type
            else:
                # 其他端点必须使用 application/json
                content_type = request.headers.get('Content-Type', '')
                if not content_type.startswith('application/json'):
                    from flask import jsonify
                    return jsonify({
                        "error": "Content-Type 必须为 application/json",
                        "success": False
                    }), 415
    
    def _after_request(self, response):
        """响应后处理，添加安全头"""
        
        # 基础安全头
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 请求 ID 追踪
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        
        # 根据环境配置不同的安全策略
        env = 'development'  # 默认值
        try:
            if self.app and hasattr(self.app, 'config'):
                env = self.app.config.get('ENV', 'development')
        except AttributeError:
            # 如果 self.app 或 self.app.config 为 None，使用默认值
            pass
        
        if env == 'production':
            # 生产环境：严格策略
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # CSP - 内容安全策略
            csp_policy = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline'",  # Vue 需要 unsafe-inline
                "style-src 'self' 'unsafe-inline'",   # Vue 需要 unsafe-inline
                "img-src 'self' data:",
                "font-src 'self'",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "form-action 'self'",
                "base-uri 'self'",
            ]
            response.headers['Content-Security-Policy'] = '; '.join(csp_policy)
            
            # 额外的生产环境头
            response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
            
        else:
            # 开发环境：宽松策略
            response.headers['Content-Security-Policy'] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:;"
            )
        
        # 缓存控制（API 响应不缓存）
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        else:
            # 静态资源缓存
            if request.path.startswith('/assets/'):
                response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1年
            else:
                response.headers['Cache-Control'] = 'no-cache'
        
        return response
    
    @staticmethod
    def validate_origin(origin):
        """验证请求来源（CORS）"""
        if not origin:
            return False
            
        # 从配置获取允许的域名列表
        try:
            from src.config import get_config
            config = get_config()
            env = config.app.env
            
            # 开发环境允许所有来源
            if env == 'development':
                return True
                
            # 生产环境：这里应该从配置中读取允许的域名
            # 暂时使用默认列表
            allowed_origins = [
                'http://localhost:5000',
                'http://localhost:5173',
                'https://fund-daily.example.com'  # 生产域名
            ]
            
            if origin in allowed_origins:
                return True
            
            # 检查子域名
            for allowed in allowed_origins:
                if allowed.startswith('https://') and origin.startswith('https://'):
                    # 简单子域名匹配
                    if origin.endswith(allowed[8:]):  # 移除 'https://'
                        return True
            
            return False
        except Exception:
            # 如果配置系统不可用，使用保守策略
            return False


# 单例实例
_security_headers = None

def get_security_headers():
    """获取安全头中间件实例"""
    global _security_headers
    if _security_headers is None:
        _security_headers = SecurityHeaders()
    return _security_headers