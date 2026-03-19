"""OpenAPI system endpoint definitions"""
from typing import Dict, Any, List


def add_endpoint(spec, method, path, handler_func=None, **kwargs):
    import inspect
    method = method.lower()
    if path not in spec["paths"]:
        spec["paths"][path] = {}
    docstring = inspect.getdoc(handler_func) or ""
    doc_lines = docstring.strip().split('\n')
    summary = doc_lines[0] if doc_lines else kwargs.get("summary", "")
    description = "\n".join(doc_lines[1:]).strip() if len(doc_lines) > 1 else kwargs.get("description", "")
    endpoint_def = {
        "summary": summary,
        "description": description,
        "tags": kwargs.get("tags", []),
        "responses": kwargs.get("responses", {"200": {"description": "OK"}})
    }
    if "parameters" in kwargs:
        endpoint_def["parameters"] = kwargs["parameters"]
    if method in ["post", "put", "patch"] and "requestBody" in kwargs:
        endpoint_def["requestBody"] = kwargs["requestBody"]
    if "security" in kwargs:
        endpoint_def["security"] = kwargs["security"]
    spec["paths"][path][method] = endpoint_def


def add_system_endpoints(spec, tags):
    """添加系统管理端点"""
    # 健康检查
    add_endpoint(spec,
        "GET", "/api/health",
        None,
        tags=["系统管理"],
        summary="健康检查",
        description="检查系统健康状态",
        responses={
            "200": {
                "description": "健康状态",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "health": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    )

    # 性能指标（标准版）
    add_endpoint(spec,
        "GET", "/api/metrics",
        None,
        tags=["性能监控"],
        summary="获取性能指标",
        description="获取系统性能指标",
        parameters=[
            {
                "name": "reset",
                "in": "query",
                "description": "是否重置指标计数器",
                "required": False,
                "schema": {"type": "boolean", "default": False}
            },
            {
                "name": "detailed",
                "in": "query",
                "description": "是否返回详细指标",
                "required": False,
                "schema": {"type": "boolean", "default": False}
            }
        ],
        responses={
            "200": {
                "description": "性能指标",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "metrics": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    )

    # 性能指标（增强版）
    add_endpoint(spec,
        "GET", "/api/metrics/enhanced",
        None,
        tags=["性能监控"],
        summary="获取增强版性能指标",
        description="获取包含历史数据、趋势分析和告警的增强版性能指标",
        parameters=[
            {
                "name": "reset",
                "in": "query",
                "description": "是否重置历史数据",
                "required": False,
                "schema": {"type": "boolean", "default": False}
            },
            {
                "name": "detailed",
                "in": "query",
                "description": "是否返回详细数据",
                "required": False,
                "schema": {"type": "boolean", "default": False}
            }
        ],
        responses={
            "200": {
                "description": "增强版性能指标",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "metrics": {"type": "object"},
                                "version": {"type": "string"},
                                "description": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )
