"""
OpenAPI 文档生成模块
支持自动从 Flask app 生成 OpenAPI 3.0 规范文档
"""

from .generator import OpenAPIGenerator
from .routes import (
    get_openapi_spec,
    get_docs_ui,
    init_openapi_docs,
    test_openapi_generator,
)

__all__ = [
    'OpenAPIGenerator',
    'get_openapi_spec',
    'get_docs_ui',
    'init_openapi_docs',
    'test_openapi_generator',
]
