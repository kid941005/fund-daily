"""OpenAPI funds endpoint definitions"""
from typing import Dict, Any, List

def add_endpoint(spec, tags, method, path, handler_func, **kwargs):
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


        """添加基金数据端点"""
        # 获取基金列表
        add_endpoint(spec, tags, 
            "GET", "/api/funds",
            None,
            tags=["基金数据"],
            summary="获取基金列表",
            description="获取用户持有的基金列表或默认基金列表",
            parameters=[
                {
                    "name": "limit",
                    "in": "query",
                    "description": "返回数量限制",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10}
                }
            ],
            responses={
                "200": {
                    "description": "基金列表",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "funds": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Fund"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        )
        
        # 获取基金详情
        add_endpoint(spec, tags, 
            "GET", "/api/fund-detail/{code}",
            None,
            tags=["基金数据"],
            summary="获取基金详情",
            description="根据基金代码获取基金详细信息",
            parameters=[
                {
                    "name": "code",
                    "in": "path",
                    "description": "基金代码（6位数字）",
                    "required": True,
                    "schema": {"type": "string", "pattern": "^\\d{6}$"}
                }
            ],
            responses={
                "200": {
                    "description": "基金详情",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "detail": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            }
        )
        
        # 获取基金评分
        add_endpoint(spec, tags, 
            "GET", "/api/score/{code}",
            None,
            tags=["基金数据", "投资建议"],
            summary="获取基金评分报告",
            description="获取基金的100分制评分报告",
            parameters=[
                {
                    "name": "code",
                    "in": "path",
                    "description": "基金代码（6位数字）",
                    "required": True,
                    "schema": {"type": "string", "pattern": "^\\d{6}$"}
                }
            ],
            responses={
                "200": {
                    "description": "评分报告",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "fund_code": {"type": "string"},
                                    "fund_name": {"type": "string"},
                                    "daily_change": {"type": "number"},
                                    "scoring": {"$ref": "#/components/schemas/ScoreResult"}
                                }
                            }
                        }
                    }
                }
            }
        )
    
    def _add_market_endpoints(self):