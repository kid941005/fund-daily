"""OpenAPI 文档路由（Flask Blueprint）"""
import os
import logging
from flask import Blueprint, jsonify

from .generator import OpenAPIGenerator

logger = logging.getLogger(__name__)

docs_bp = Blueprint("openapi_docs", __name__, url_prefix="/api/docs")


@docs_bp.route("/openapi.json")
def get_openapi_spec():
    """获取 OpenAPI 规范 JSON"""
    generator = OpenAPIGenerator()
    generator.generate_from_flask_app(None)
    return generator.to_dict()


@docs_bp.route("/")
def get_docs_ui():
    """返回 API 文档 UI（Swagger UI）"""
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
                SwaggerUIBundle({
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
    """注册 OpenAPI Blueprint 并生成文档文件"""
    app.register_blueprint(docs_bp)

    generator = OpenAPIGenerator()
    generator.generate_from_flask_app(app)

    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    generator.save_to_file(os.path.join(docs_dir, "openapi.json"))

    logger.info("OpenAPI 文档已初始化")


def test_openapi_generator():
    """测试 OpenAPI 生成器"""
    generator = OpenAPIGenerator()
    generator.generate_from_flask_app(None)

    spec = generator.to_dict()
    logger.info("✅ OpenAPI 生成器测试成功")
    logger.info(f"   标题: {spec['info']['title']}")
    logger.info(f"   版本: {spec['info']['version']}")
    logger.info(f"   端点数量: {len(spec['paths'])}")
    logger.info(f"   标签数量: {len(spec['tags'])}")
    return True
