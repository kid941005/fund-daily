"""API Gateway Flask Blueprint integration"""
from flask import Blueprint, request, jsonify

from .core import get_api_gateway


def create_gateway_blueprint():
    """创建API网关的Flask Blueprint（演示用）"""
    gateway_bp = Blueprint("api_gateway", __name__, url_prefix="/gateway")
    gateway = get_api_gateway()

    @gateway_bp.route("/status", methods=["GET"])
    def gateway_status():
        """获取网关状态"""
        return jsonify(gateway.get_gateway_status())

    @gateway_bp.route("/reset", methods=["POST"])
    def reset_limits():
        """重置速率限制（需要管理员权限）"""
        gateway.reset_rate_limits()
        return jsonify({"success": True, "message": "速率限制已重置"})

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
        full_path = f"/api/{service_path}" if not service_path.startswith("/") else service_path
        result = gateway.process_request(
            method=request.method,
            path=full_path,
            headers=dict(request.headers),
            body=request.get_json(silent=True),
            client_ip=request.remote_addr
        )
        status_code = 200 if result.get("success") else result.get("error", {}).get("status_code", 500)
        return jsonify(result), status_code

    @gateway_bp.route("/services", methods=["GET"])
    def list_services():
        """列出所有注册的服务"""
        services = [{
            "name": s.name,
            "path": s.path,
            "method": s.method,
            "description": s.description,
            "requires_auth": s.requires_auth,
            "rate_limit": s.rate_limit,
            "timeout": s.timeout
        } for s in gateway._services.values()]
        return jsonify({"success": True, "services": services, "count": len(services)})

    return gateway_bp
