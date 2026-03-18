"""
API Gateway演示
P2优化：微服务架构探索演示

这是一个简化的API网关实现，演示微服务架构概念。
在实际生产环境中，可以使用专业的API网关解决方案（如Kong、Tyk、APISIX等）。
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """微服务端点定义"""
    name: str
    path: str
    method: str = "GET"
    description: str = ""
    requires_auth: bool = False
    rate_limit: int = 100  # 每分钟请求数限制
    timeout: float = 5.0  # 超时时间（秒）
    
    def __str__(self):
        return f"{self.name}: {self.method} {self.path}"


class RateLimiter:
    """简单的速率限制器"""
    
    def __init__(self, cleanup_interval: int = 300, max_age: int = 3600):
        """
        初始化速率限制器
        
        Args:
            cleanup_interval: 清理间隔（秒），默认5分钟
            max_age: 最大保留时间（秒），默认1小时
        """
        self._requests: Dict[str, List[float]] = {}
        self._cleanup_interval = cleanup_interval
        self._max_age = max_age
        self._last_cleanup = time.time()
    
    def _cleanup_expired(self):
        """清理过期的客户端记录"""
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        expired_clients = []
        for client_id, req_times in self._requests.items():
            # 过滤出未过期的请求
            valid_times = [
                req_time for req_time in req_times
                if current_time - req_time <= self._max_age
            ]
            
            if valid_times:
                self._requests[client_id] = valid_times
            else:
                expired_clients.append(client_id)
        
        # 删除完全过期的客户端
        for client_id in expired_clients:
            del self._requests[client_id]
        
        # 更新清理时间
        self._last_cleanup = current_time
        
        if expired_clients:
            logger.debug(f"RateLimiter: cleaned up {len(expired_clients)} expired clients")
    
    def check_limit(self, client_id: str, limit: int, window_seconds: int = 60) -> Tuple[bool, float]:
        """
        检查速率限制
        
        Args:
            client_id: 客户端标识
            limit: 限制次数
            window_seconds: 时间窗口（秒）
        
        Returns:
            (是否允许, 剩余时间秒数)
        """
        # 定期清理过期记录
        self._cleanup_expired()
        
        current_time = time.time()
        
        # 清理过期请求
        if client_id in self._requests:
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if current_time - req_time <= window_seconds
            ]
        else:
            self._requests[client_id] = []
        
        # 检查限制
        if len(self._requests[client_id]) < limit:
            self._requests[client_id].append(current_time)
            return True, 0.0
        else:
            # 计算需要等待的时间
            oldest_request = min(self._requests[client_id])
            wait_time = oldest_request + window_seconds - current_time
            return False, max(0.0, wait_time)
    
    def reset(self, client_id: str = None):
        """重置速率限制"""
        if client_id is None:
            self._requests.clear()
        elif client_id in self._requests:
            del self._requests[client_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_clients": len(self._requests),
            "cleanup_interval": self._cleanup_interval,
            "max_age": self._max_age,
            "last_cleanup": self._last_cleanup
        }


class APIGateway:
    """
    API网关演示类
    
    功能：
    1. 请求路由
    2. 速率限制
    3. 认证验证
    4. 请求日志
    5. 错误处理
    6. 响应转换
    """
    
    def __init__(self):
        # 服务注册表
        self._services: Dict[str, ServiceEndpoint] = {}
        
        # 速率限制器
        self._rate_limiter = RateLimiter()
        
        # 初始化默认服务
        self._init_default_services()
        
        # 认证token（演示用）
        self._valid_tokens = {
            "admin": "admin-token-123",
            "user": "user-token-456",
            "readonly": "readonly-token-789"
        }
        
        logger.info("API Gateway 初始化完成")
    
    def _init_default_services(self):
        """初始化默认服务端点"""
        default_services = [
            ServiceEndpoint(
                name="health_check",
                path="/api/health",
                method="GET",
                description="健康检查服务",
                requires_auth=False,
                rate_limit=1000
            ),
            ServiceEndpoint(
                name="fund_list",
                path="/api/funds",
                method="GET",
                description="获取基金列表",
                requires_auth=True,
                rate_limit=100
            ),
            ServiceEndpoint(
                name="fund_detail",
                path="/api/fund-detail/{code}",
                method="GET",
                description="获取基金详情",
                requires_auth=True,
                rate_limit=50
            ),
            ServiceEndpoint(
                name="market_data",
                path="/api/market",
                method="GET",
                description="获取市场数据",
                requires_auth=True,
                rate_limit=100
            ),
            ServiceEndpoint(
                name="investment_advice",
                path="/api/advice",
                method="GET",
                description="获取投资建议",
                requires_auth=True,
                rate_limit=50
            ),
            ServiceEndpoint(
                name="performance_metrics",
                path="/api/metrics",
                method="GET",
                description="获取性能指标",
                requires_auth=True,
                rate_limit=30
            ),
            ServiceEndpoint(
                name="enhanced_metrics",
                path="/api/metrics/enhanced",
                method="GET",
                description="获取增强版性能指标",
                requires_auth=True,
                rate_limit=30
            ),
            ServiceEndpoint(
                name="api_docs",
                path="/api/docs/openapi.json",
                method="GET",
                description="获取API文档",
                requires_auth=False,
                rate_limit=100
            )
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
        # 尝试精确匹配
        service_key = f"{method}:{path}"
        if service_key in self._services:
            return self._services[service_key]
        
        # 尝试路径参数匹配（简化版）
        for key, service in self._services.items():
            if key.startswith(f"{method}:"):
                # 简单路径匹配（实际应用中需要更复杂的路由匹配）
                service_path = key.split(":", 1)[1]
                if "{code}" in service_path and path.startswith(service_path.replace("{code}", "")):
                    return service
        
        return None
    
    def validate_auth(self, token: str, service: ServiceEndpoint) -> Tuple[bool, str]:
        """
        验证认证令牌
        
        Args:
            token: 认证令牌
            service: 服务端点
        
        Returns:
            (是否有效, 错误消息)
        """
        if not service.requires_auth:
            return True, ""
        
        if not token:
            return False, "认证令牌缺失"
        
        # 简单令牌验证（演示用）
        if token in self._valid_tokens.values():
            return True, ""
        else:
            return False, "无效的认证令牌"
    
    def process_request(self, method: str, path: str, headers: Dict[str, str], 
                       body: Optional[Dict[str, Any]] = None, 
                       client_ip: str = "unknown") -> Dict[str, Any]:
        """
        处理API请求
        
        Args:
            method: HTTP方法
            path: 请求路径
            headers: 请求头
            body: 请求体
            client_ip: 客户端IP
        
        Returns:
            网关响应
        """
        start_time = time.time()
        request_id = self._generate_request_id(method, path, client_ip)
        
        logger.info(f"[{request_id}] 请求开始: {method} {path} from {client_ip}")
        
        try:
            # 1. 查找服务
            service = self.get_service(method, path)
            if not service:
                return self._create_error_response(
                    request_id, "SERVICE_NOT_FOUND", "请求的服务不存在", 404
                )
            
            # 2. 速率限制
            client_id = headers.get("X-Client-ID", client_ip)
            allowed, wait_time = self._rate_limiter.check_limit(
                client_id, service.rate_limit
            )
            
            if not allowed:
                return self._create_error_response(
                    request_id, "RATE_LIMIT_EXCEEDED",
                    f"速率限制已超过，请等待 {wait_time:.1f} 秒后重试",
                    429,
                    headers={"Retry-After": str(int(wait_time))}
                )
            
            # 3. 认证验证
            auth_token = headers.get("Authorization", "").replace("Bearer ", "")
            auth_valid, auth_error = self.validate_auth(auth_token, service)
            
            if not auth_valid:
                return self._create_error_response(
                    request_id, "AUTHENTICATION_FAILED", auth_error, 401
                )
            
            # 4. 记录请求（实际应用中会转发到后端服务）
            logger.info(f"[{request_id}] 请求验证通过: {service.name}")
            
            # 5. 模拟处理时间（实际应用中会转发请求）
            processing_time = min(service.timeout * 0.1, 0.1)  # 模拟10%的处理时间
            time.sleep(processing_time)
            
            # 6. 构建成功响应
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
                    "rate_limit_remaining": service.rate_limit - 1,  # 简化计算
                    "gateway_version": "1.0.0-demo"
                }
            }
            
        except Exception as e:
            logger.error(f"[{request_id}] 请求处理异常: {e}", exc_info=True)
            return self._create_error_response(
                request_id, "GATEWAY_ERROR", f"网关处理异常: {str(e)}", 500
            )
    
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
            "metadata": {
                "gateway_version": "1.0.0-demo"
            }
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
                "list": [str(service) for service in self._services.values()]
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


# 全局网关实例（单例模式）
_gateway_instance = None

def get_api_gateway() -> APIGateway:
    """获取API网关实例"""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = APIGateway()
    return _gateway_instance


# Flask集成示例（可选）
def create_gateway_blueprint():
    """创建API网关的Flask Blueprint（演示用）"""
    from flask import Blueprint, request, jsonify
    
    gateway_bp = Bluelogger.info("gateway", __name__, url_prefix="/gateway")
    gateway = get_api_gateway()
    
    @gateway_bp.route("/status", methods=["GET"])
    def gateway_status():
        """获取网关状态"""
        return jsonify(gateway.get_gateway_status())
    
    @gateway_bp.route("/reset", methods=["POST"])
    def reset_limits():
        """重置速率限制（需要管理员权限）"""
        gateway.reset_rate_limits()
        return jsonify({
            "success": True,
            "message": "速率限制已重置"
        })
    
    @gateway_bp.route("/proxy/<path:service_path>", methods=["GET", "POST", "PUT", "DELETE"])
    def proxy_request(service_path):
        """
        API网关代理端点（演示用）
        
        注意：这是一个简化的演示实现，实际网关需要处理：
        1. 请求转发到后端服务
        2. 负载均衡
        3. 服务发现
        4. 熔断器
        5. 请求/响应转换
        """
        # 构建完整路径
        full_path = f"/api/{service_path}" if not service_path.startswith("/") else service_path
        
        # 处理请求
        result = gateway.process_request(
            method=request.method,
            path=full_path,
            headers=dict(request.headers),
            body=request.get_json(silent=True),
            client_ip=request.remote_addr
        )
        
        # 返回响应
        status_code = 200 if result.get("success") else result.get("error", {}).get("status_code", 500)
        return jsonify(result), status_code
    
    @gateway_bp.route("/services", methods=["GET"])
    def list_services():
        """列出所有注册的服务"""
        services = []
        for service in gateway._services.values():
            services.append({
                "name": service.name,
                "path": service.path,
                "method": service.method,
                "description": service.description,
                "requires_auth": service.requires_auth,
                "rate_limit": service.rate_limit,
                "timeout": service.timeout
            })
        
        return jsonify({
            "success": True,
            "services": services,
            "count": len(services)
        })
    
    return gateway_bp


# 测试函数
def test_api_gateway():
    """测试API网关"""
    logger.info("🧪 测试API Gateway...")
    
    gateway = get_api_gateway()
    
    # 测试获取网关状态
    status = gateway.get_gateway_status()
    logger.info(f"  ✅ 网关状态: {status['status']}")
    logger.info(f"     注册服务: {status['services']['registered']}个")
    
    # 测试处理请求
    test_headers = {
        "Authorization": "Bearer admin-token-123",
        "X-Client-ID": "test-client"
    }
    
    # 测试健康检查请求（不需要认证）
    result1 = gateway.process_request("GET", "/api/health", {})
    logger.info(f"  ✅ 健康检查请求: {result1.get('success', False)}")
    
    # 测试需要认证的请求（有效令牌）
    result2 = gateway.process_request("GET", "/api/funds", test_headers)
    logger.info(f"  ✅ 基金列表请求（有效令牌）: {result2.get('success', False)}")
    
    # 测试需要认证的请求（无效令牌）
    result3 = gateway.process_request("GET", "/api/funds", {"Authorization": "Bearer invalid-token"})
    logger.info(f"  ✅ 基金列表请求（无效令牌）: {result3.get('success', False)} (预期: False)")
    
    # 测试不存在的服务
    result4 = gateway.process_request("GET", "/api/nonexistent", test_headers)
    logger.info(f"  ✅ 不存在的服务请求: {result4.get('success', False)} (预期: False)")
    
    # 测试速率限制
    logger.info("  ⚡ 测试速率限制...")
    client_id = "rate-test-client"
    test_headers["X-Client-ID"] = client_id
    
    success_count = 0
    for i in range(10):
        result = gateway.process_request("GET", "/api/funds", test_headers)
        if result.get("success"):
            success_count += 1
    
    logger.info(f"     10次请求中成功: {success_count}次")
    
    logger.info("🎉 API Gateway 测试完成")
    return True


if __name__ == "__main__":
    test_api_gateway()