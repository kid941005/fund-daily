"""OpenAPI auth endpoint definitions"""
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


def add_auth_endpoints(spec, tags):
    """添加认证相关端点"""
    # 注册
    add_endpoint(spec,
        "POST", "/api/register",
        None,
        tags=["认证"],
        summary="用户注册",
        description="创建新用户账户",
        requestBody={
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string", "example": "testuser"},
                            "password": {"type": "string", "example": "password123"}
                        },
                        "required": ["username", "password"]
                    }
                }
            }
        },
        responses={
            "200": {
                "description": "注册成功",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "message": {"type": "string"},
                                "username": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )

    # 登录
    add_endpoint(spec,
        "POST", "/api/login",
        None,
        tags=["认证"],
        summary="用户登录",
        description="用户登录并创建会话",
        requestBody={
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string", "example": "testuser"},
                            "password": {"type": "string", "example": "password123"}
                        },
                        "required": ["username", "password"]
                    }
                }
            }
        },
        responses={
            "200": {
                "description": "登录成功",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "message": {"type": "string"},
                                "username": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )

    # 登出
    add_endpoint(spec,
        "POST", "/api/logout",
        None,
        tags=["认证"],
        summary="用户登出",
        description="销毁用户会话",
        responses={
            "200": {
                "description": "登出成功",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "message": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )

    # 检查登录状态
    add_endpoint(spec,
        "GET", "/api/check-login",
        None,
        tags=["认证"],
        summary="检查登录状态",
        description="检查当前用户是否已登录",
        responses={
            "200": {
                "description": "登录状态",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "logged_in": {"type": "boolean"},
                                "username": {"type": "string", "nullable": True}
                            }
                        }
                    }
                }
            }
        }
    )
