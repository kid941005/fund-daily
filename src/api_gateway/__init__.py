"""
API Gateway 模块

拆分自 src/api_gateway.py (569行 → 4个文件)
- models.py  : ServiceEndpoint、RateLimiter
- core.py    : APIGateway 核心类、单例
- routes.py  : Flask Blueprint 集成
- __init__.py: 向后兼容导出
"""

from .models import ServiceEndpoint, RateLimiter
from .core import APIGateway, get_api_gateway
from .routes import create_gateway_blueprint

__all__ = [
    "ServiceEndpoint",
    "RateLimiter",
    "APIGateway",
    "get_api_gateway",
    "create_gateway_blueprint",
]
