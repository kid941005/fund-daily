import json
import inspect
from typing import Dict, List, Any, Optional
from flask import Blueprint, current_app
import logging

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