"""
OpenAPI文档生成器
P2优化：API文档自动生成
"""

import json
import inspect
from typing import Dict, List, Any, Optional
from flask import Blueprint, current_app
import logging

logger = logging.getLogger(__name__)


class OpenAPIGenerator:
    """OpenAPI文档生成器"""
    
    def __init__(self, title: str = "Fund Daily API", version: str = "2.6.0"):
        self.title = title
        self.version = version
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "基金每日分析系统 API 文档",
                "contact": {
                    "name": "API Support",
                    "email": "support@example.com"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:5000",
                    "description": "开发服务器"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "session_auth": {
                        "type": "apiKey",
                        "in": "cookie",
                        "name": "session"
                    }
                }
            },
            "tags": []
        }
        
        # 预定义标签
        self._init_tags()
        
        # 预定义Schema
        self._init_schemas()
    
    def _init_tags(self):
        """初始化API标签"""
        self.openapi_spec["tags"] = [
            {"name": "认证", "description": "用户认证和会话管理"},
            {"name": "基金数据", "description": "基金信息获取和查询"},
            {"name": "市场数据", "description": "市场行情和情绪分析"},
            {"name": "投资建议", "description": "基金评分和投资建议"},
            {"name": "投资组合", "description": "用户投资组合管理"},
            {"name": "系统管理", "description": "系统状态和监控"},
            {"name": "性能监控", "description": "系统性能指标"}
        ]
    
    def _init_schemas(self):
        """初始化数据模型Schema"""
        # 错误响应Schema
        self.openapi_spec["components"]["schemas"]["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "success": {
                    "type": "boolean",
                    "example": False
                },
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "example": "VALIDATION_ERROR"},
                        "message": {"type": "string", "example": "基金代码必须为6位数字"},
                        "field": {"type": "string", "example": "code"},
                        "value": {"type": "string", "example": "00001"}
                    }
                }
            }
        }
        
        # 成功响应Schema
        self.openapi_spec["components"]["schemas"]["SuccessResponse"] = {
            "type": "object",
            "properties": {
                "success": {
                    "type": "boolean",
                    "example": True
                },
                "message": {
                    "type": "string",
                    "example": "操作成功"
                }
            }
        }
        
        # 基金数据Schema
        self.openapi_spec["components"]["schemas"]["Fund"] = {
            "type": "object",
            "properties": {
                "fund_code": {"type": "string", "example": "000001"},
                "fund_name": {"type": "string", "example": "华夏成长"},
                "net_value": {"type": "number", "example": 1.2345},
                "daily_change": {"type": "number", "example": 1.23},
                "return_1y": {"type": "number", "example": 15.5},
                "risk_level": {"type": "string", "example": "中高风险"},
                "trend": {"type": "string", "example": "up"},
                "score": {"type": "number", "example": 85.5}
            }
        }
        
        # 市场情绪Schema
        self.openapi_spec["components"]["schemas"]["MarketSentiment"] = {
            "type": "object",
            "properties": {
                "sentiment": {"type": "string", "example": "bullish"},
                "score": {"type": "number", "example": 75.0},
                "description": {"type": "string", "example": "市场情绪乐观"}
            }
        }
        
        # 评分结果Schema
        self.openapi_spec["components"]["schemas"]["ScoreResult"] = {
            "type": "object",
            "properties": {
                "total_score": {"type": "number", "example": 85.5},
                "breakdown": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                    "example": {"valuation": 20, "performance": 18, "risk": 15}
                },
                "grade": {"type": "string", "example": "B+"},
                "details": {"type": "object"}
            }
        }
    
    def add_endpoint(self, method: str, path: str, handler_func, **kwargs):
        """
        添加API端点到OpenAPI文档
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            path: API路径
            handler_func: 处理函数（用于提取文档字符串）
            **kwargs: 额外参数 (tags, summary, description, parameters, responses)
        """
        method = method.lower()
        
        # 确保路径在paths中
        if path not in self.openapi_spec["paths"]:
            self.openapi_spec["paths"][path] = {}
        
        # 从函数文档字符串中提取信息
        docstring = inspect.getdoc(handler_func) or ""
        doc_lines = docstring.strip().split('\n')
        
        # 提取摘要和描述
        summary = doc_lines[0] if doc_lines else kwargs.get("summary", "")
        description = "\n".join(doc_lines[1:]).strip() if len(doc_lines) > 1 else kwargs.get("description", "")
        
        # 构建端点定义
        endpoint_def = {
            "summary": summary,
            "description": description,
            "tags": kwargs.get("tags", []),
            "responses": kwargs.get("responses", self._get_default_responses())
        }
        
        # 添加参数
        if "parameters" in kwargs:
            endpoint_def["parameters"] = kwargs["parameters"]
        
        # 添加请求体（如果是POST/PUT）
        if method in ["post", "put", "patch"] and "requestBody" in kwargs:
            endpoint_def["requestBody"] = kwargs["requestBody"]
        
        # 添加安全性要求
        if "security" in kwargs:
            endpoint_def["security"] = kwargs["security"]
        
        self.openapi_spec["paths"][path][method] = endpoint_def
    
    def _get_default_responses(self) -> Dict[str, Any]:
        """获取默认响应定义"""
        return {
            "200": {
                "description": "成功",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": True}
                            }
                        }
                    }
                }
            },
            "400": {
                "description": "请求参数错误",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "401": {
                "description": "未授权",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "500": {
                "description": "服务器内部错误",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            }
        }
    
    def generate_from_flask_app(self, app):
        """
        从Flask应用生成OpenAPI文档
        
        Args:
            app: Flask应用实例
        """
        logger.info("开始生成OpenAPI文档...")
        
        # 这里可以自动扫描Flask路由
        # 由于时间限制，我们手动添加主要端点
        
        # 认证端点
        self._add_auth_endpoints()
        
        # 基金数据端点
        self._add_fund_endpoints()
        
        # 市场数据端点
        self._add_market_endpoints()
        
        # 系统管理端点
        self._add_system_endpoints()
        
        logger.info(f"OpenAPI文档生成完成，包含 {len(self.openapi_spec['paths'])} 个端点")
    

        # Endpoint modules
        from .endpoints.auth import add_auth_endpoints
        from .endpoints.funds import add_fund_endpoints
        from .endpoints.market import add_market_endpoints
        from .endpoints.system import add_system_endpoints

    def to_dict(self) -> Dict[str, Any]:
        """返回OpenAPI规范字典"""
        return self.openapi_spec
    
    def to_json(self, indent: int = 2) -> str:
        """返回OpenAPI规范JSON字符串"""
        return json.dumps(self.openapi_spec, indent=indent, ensure_ascii=False)
    
    def save_to_file(self, filepath: str):
        """保存OpenAPI规范到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        logger.info(f"OpenAPI文档已保存到: {filepath}")


# Flask Blueprint用于提供API文档
docs_bp = Blueprint("openapi_docs", __name__, url_prefix="/api/docs")


@docs_bp.route("/openapi.json")
def get_openapi_spec():
    """获取OpenAPI规范JSON"""
    generator = OpenAPIGenerator()
    generator.generate_from_flask_app(None)  # 简化版本
    return generator.to_dict()


@docs_bp.route("/")
def get_docs_ui():
    """返回API文档UI（重定向到Swagger UI）"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fund Daily API 文档</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css">
        <style>
            body { margin: 0; padding: 0; }
            #swagger-ui { padding: 20px; }
            .topbar { display: none; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                const ui = SwaggerUIBundle({
                    url: "/api/docs/openapi.json",
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return html


def init_openapi_docs(app):
    """
    初始化OpenAPI文档
    
    Args:
        app: Flask应用实例
    """
    # 注册文档Blueprint
    app.register_blueprint(docs_bp)
    
    # 生成并保存OpenAPI文档
    generator = OpenAPIGenerator()
    generator.generate_from_flask_app(app)
    
    # 保存到文件
    import os
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    generator.save_to_file(os.path.join(docs_dir, "openapi.json"))
    
    logger.info("OpenAPI文档已初始化")


# 测试函数
def test_openapi_generator():
    """测试OpenAPI生成器"""
    generator = OpenAPIGenerator()
    generator.generate_from_flask_app(None)
    
    spec = generator.to_dict()
    logger.info(f"✅ OpenAPI生成器测试成功")
    logger.info(f"   标题: {spec['info']['title']}")
    logger.info(f"   版本: {spec['info']['version']}")
    logger.info(f"   端点数量: {len(spec['paths'])}")
    logger.info(f"   标签数量: {len(spec['tags'])}")
    
    return True


if __name__ == "__main__":
    test_openapi_generator()