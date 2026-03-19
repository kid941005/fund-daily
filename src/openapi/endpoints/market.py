"""OpenAPI market endpoint definitions"""
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


def add_market_endpoints(spec, tags):
    """添加市场数据端点"""
    # 获取市场情绪
    add_endpoint(spec,
        "GET", "/api/market",
        None,
        tags=["市场数据"],
        summary="获取市场数据",
        description="获取市场情绪、新闻和热门板块数据",
        responses={
            "200": {
                "description": "市场数据",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "market": {"$ref": "#/components/schemas/MarketSentiment"},
                                "news": {
                                    "type": "array",
                                    "items": {"type": "object"}
                                },
                                "hot_sectors": {
                                    "type": "array",
                                    "items": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            }
        }
    )

    # 获取投资建议
    add_endpoint(spec,
        "GET", "/api/advice",
        None,
        tags=["投资建议"],
        summary="获取投资建议",
        description="获取基于市场情绪的投资建议",
        responses={
            "200": {
                "description": "投资建议",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "advice": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    )
