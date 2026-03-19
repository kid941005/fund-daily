"""API Gateway core logic"""
import time
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .models import ServiceEndpoint, RateLimiter

logger = logging.getLogger(__name__)


class APIGateway:
    """
    API网关核心类

    功能：
    1. 请求路由
    2. 速率限制
    3. 认证验证
    4. 请求日志
    5. 错误处理
    6. 响应转换
    """

    def __init__(self):
        self._services: Dict[str, ServiceEndpoint] = {}
        self._rate_limiter = RateLimiter()
        self._init_default_services()
        
        # 使用配置管理器读取配置
        from src.config import get_config
        config = get_config()
        
        # 从配置读取令牌
        self.env = config.env
        admin_token = config.admin_token
        user_token = config.user_token
        readonly_token = config.readonly_token
        
        if self.env == "production":
            # 生产环境必须设置令牌
            if not admin_token or not user_token or not readonly_token:
                raise ValueError(
                    "生产环境必须设置API网关令牌！请设置环境变量：\n"
                    "FUND_DAILY_ADMIN_TOKEN\n"
                    "FUND_DAILY_USER_TOKEN\n"
                    "FUND_DAILY_READONLY_TOKEN"
                )
        else:
            # 开发环境使用默认值（带警告）
            if not admin_token:
                admin_token = "dev-admin-token-change-in-production"
            user_token = os.getenv("FUND_DAILY_USER_TOKEN", "dev-user-token-change-in-production")
            if not user_token:
                user_token = "dev-user-token-change-in-production"
            if not readonly_token:
                readonly_token = "dev-readonly-token-change-in-production"
            
            if self.env == "development":
                logger.warning("开发环境使用默认API网关令牌，生产环境必须设置强令牌！")
        
        self._valid_tokens = {
            "admin": admin_token,
            "user": user_token,
            "readonly": readonly_token
        }
        logger.info("API Gateway 初始化完成")

    def _init_default_services(self):
        """初始化默认服务端点"""
        default_services = [
            ServiceEndpoint("health_check", "/api/health", "GET",
                            "健康检查服务", False, 1000),
            ServiceEndpoint("fund_list", "/api/funds", "GET",
                            "获取基金列表", True, 100),
            ServiceEndpoint("fund_detail", "/api/fund-detail/{code}", "GET",
                            "获取基金详情", True, 50),
            ServiceEndpoint("market_data", "/api/market", "GET",
                            "获取市场数据", True, 100),
            ServiceEndpoint("investment_advice", "/api/advice", "GET",
                            "获取投资建议", True, 50),
            ServiceEndpoint("performance_metrics", "/api/metrics", "GET",
                            "获取性能指标", True, 30),
            ServiceEndpoint("enhanced_metrics", "/api/metrics/enhanced", "GET",
                            "获取增强版性能指标", True, 30),
            ServiceEndpoint("api_docs", "/api/docs/openapi.json", "GET",
                            "获取API文档", False, 100),
        ]
        for service in default_services:
            self.register_service(service)

    def register_service(self, service: ServiceEndpoint):
        """注册服务端点"""
        service_key = f"{service.method}:{service.path}"
        self._services[service_key] = service
        logger.info(f"服务注册: {service.name} -> {service.method} {service.path}")

    def unregister_service(self, service_key: str):
        """注销服务端点"""
        if service_key in self._services:
            service = self._services[service_key]
            del self._services[service_key]
            logger.info(f"服务注销: {service.name}")

    def get_service(self, method: str, path: str) -> Optional[ServiceEndpoint]:
        """根据方法和路径获取服务"""
        service_key = f"{method}:{path}"
        if service_key in self._services:
            return self._services[service_key]

        # 路径参数匹配
        for key, service in self._services.items():
            if key.startswith(f"{method}:"):
                service_path = key.split(":", 1)[1]
                if "{code}" in service_path and path.startswith(service_path.replace("{code}", "")):
                    return service
        return None

    def validate_auth(self, token: str, service: ServiceEndpoint) -> Tuple[bool, str]:
        """验证认证令牌"""
        if not service.requires_auth:
            return True, ""
        if not token:
            return False, "认证令牌缺失"
        if token in self._valid_tokens.values():
            return True, ""
        return False, "无效的认证令牌"

    def process_request(self, method: str, path: str, headers: Dict[str, str],
                        body: Optional[Dict[str, Any]] = None,
                        client_ip: str = "unknown") -> Dict[str, Any]:
        """处理API请求"""
        start_time = time.time()
        request_id = self._generate_request_id(method, path, client_ip)

        logger.info(f"[{request_id}] 请求开始: {method} {path} from {client_ip}")

        try:
            service = self.get_service(method, path)
            if not service:
                return self._create_error_response(
                    request_id, "SERVICE_NOT_FOUND", "请求的服务不存在", 404)

            client_id = headers.get("X-Client-ID", client_ip)
            allowed, wait_time = self._rate_limiter.check_limit(client_id, service.rate_limit)
            if not allowed:
                return self._create_error_response(
                    request_id, "RATE_LIMIT_EXCEEDED",
                    f"速率限制已超过，请等待 {wait_time:.1f} 秒后重试",
                    429, headers={"Retry-After": str(int(wait_time))})

            auth_token = headers.get("Authorization", "").replace("Bearer ", "")
            auth_valid, auth_error = self.validate_auth(auth_token, service)
            if not auth_valid:
                return self._create_error_response(
                    request_id, "AUTHENTICATION_FAILED", auth_error, 401)

            logger.info(f"[{request_id}] 请求验证通过: {service.name}")
            time.sleep(min(service.timeout * 0.1, 0.1))

            duration = time.time() - start_time
            return {
                "request_id": request_id,
                "success": True,
                "service": service.name,
                "timestamp": datetime.now().isoformat(),
                "duration": round(duration, 3),
                "data": {
                    "message": f"请求已通过API网关验证，可以转发到服务: {service.name}",
                    "original_path": path,
                    "method": method,
                    "service_endpoint": service.path,
                    "rate_limit": service.rate_limit,
                    "requires_auth": service.requires_auth
                },
                "metadata": {
                    "client_ip": client_ip,
                    "rate_limit_remaining": service.rate_limit - 1,
                    "gateway_version": "1.0.0-demo"
                }
            }
        except Exception as e:
            logger.error(f"[{request_id}] 请求处理异常: {e}", exc_info=True)
            return self._create_error_response(
                request_id, "GATEWAY_ERROR", f"网关处理异常: {str(e)}", 500)

    def _generate_request_id(self, method: str, path: str, client_ip: str) -> str:
        """生成请求ID"""
        timestamp = int(time.time() * 1000)
        hash_input = f"{method}:{path}:{client_ip}:{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"req_{timestamp}_{hash_value}"

    def _create_error_response(self, request_id: str, error_code: str,
                              error_message: str, status_code: int,
                              headers: Dict[str, str] = None) -> Dict[str, Any]:
        """创建错误响应"""
        response = {
            "request_id": request_id,
            "success": False,
            "error": {
                "code": error_code,
                "message": error_message,
                "status_code": status_code,
                "timestamp": datetime.now().isoformat()
            },
            "metadata": {"gateway_version": "1.0.0-demo"}
        }
        if headers:
            response["error"]["headers"] = headers
        return response

    def get_gateway_status(self) -> Dict[str, Any]:
        """获取网关状态"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "registered": len(self._services),
                "list": [str(s) for s in self._services.values()]
            },
            "rate_limiter": {
                "active_clients": len(self._rate_limiter._requests)
            },
            "version": "1.0.0-demo",
            "description": "API Gateway 演示版本 (P2优化)"
        }

    def reset_rate_limits(self):
        """重置所有速率限制"""
        self._rate_limiter.reset()
        logger.info("速率限制已重置")


# 单例
_gateway_instance = None

def get_api_gateway() -> APIGateway:
    """获取API网关实例（单例）"""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = APIGateway()
    return _gateway_instance
