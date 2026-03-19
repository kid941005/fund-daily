"""
API Gateway演示
P2优化：微服务架构探索演示

⚠️  此文件已拆分为 api_gateway/ 包（models / core / routes）
⚠️  原有 import 路径保持兼容，新代码请使用：
    from src.api_gateway import APIGateway, get_api_gateway, create_gateway_blueprint
"""

# 向后兼容导出
from src.api_gateway import (
    ServiceEndpoint,
    RateLimiter,
    APIGateway,
    get_api_gateway,
    create_gateway_blueprint,
)

__all__ = [
    "ServiceEndpoint",
    "RateLimiter",
    "APIGateway",
    "get_api_gateway",
    "create_gateway_blueprint",
]
