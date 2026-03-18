"""
输入验证模块
提供统一的输入验证装饰器和工具函数
"""

import re
import functools
import logging
from typing import Callable, Any, Optional, Union
from flask import jsonify, request

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


def validate_fund_code(code: str) -> str:
    """
    验证基金代码格式
    
    Args:
        code: 基金代码
        
    Returns:
        验证后的基金代码
        
    Raises:
        ValidationError: 如果基金代码无效
    """
    if not code:
        raise ValidationError("基金代码不能为空", field="code", value=code)
    
    # 基金代码必须是6位数字
    if not isinstance(code, str) or not re.match(r'^\d{6}$', code):
        raise ValidationError(
            f"基金代码必须为6位数字，当前为: {code}",
            field="code", 
            value=code
        )
    
    # 简单的前缀检查（可选）
    valid_prefixes = ['0', '1', '5', '6']  # 常见基金代码前缀
    if code[0] not in valid_prefixes:
        logger.warning(f"基金代码 {code} 有不常见的前缀")
    
    return code


def validate_limit(limit: int, min_value: int = 1, max_value: int = 100) -> int:
    """
    验证分页限制参数
    
    Args:
        limit: 限制值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        验证后的限制值
        
    Raises:
        ValidationError: 如果限制值无效
    """
    if not isinstance(limit, int):
        raise ValidationError("limit 必须是整数", field="limit", value=limit)
    
    if limit < min_value or limit > max_value:
        raise ValidationError(
            f"limit 必须在 {min_value} 到 {max_value} 之间，当前为: {limit}",
            field="limit",
            value=limit
        )
    
    return limit


def validate_page(page: int, min_value: int = 1) -> int:
    """
    验证页码参数
    
    Args:
        page: 页码
        min_value: 最小页码
        
    Returns:
        验证后的页码
        
    Raises:
        ValidationError: 如果页码无效
    """
    if not isinstance(page, int):
        raise ValidationError("page 必须是整数", field="page", value=page)
    
    if page < min_value:
        raise ValidationError(
            f"page 必须大于等于 {min_value}，当前为: {page}",
            field="page",
            value=page
        )
    
    return page


def validate_username(username: str, min_length: int = 3, max_length: int = 50) -> str:
    """
    验证用户名
    
    Args:
        username: 用户名
        min_length: 最小长度
        max_length: 最大长度
        
    Returns:
        验证后的用户名
        
    Raises:
        ValidationError: 如果用户名无效
    """
    if not username:
        raise ValidationError("用户名不能为空", field="username", value=username)
    
    username = username.strip()
    
    if len(username) < min_length or len(username) > max_length:
        raise ValidationError(
            f"用户名长度必须在 {min_length} 到 {max_length} 字符之间，当前为: {len(username)}",
            field="username",
            value=username
        )
    
    # 只允许字母、数字、下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise ValidationError(
            "用户名只能包含字母、数字和下划线",
            field="username",
            value=username
        )
    
    return username


def validate_password(password: str, min_length: int = 6) -> str:
    """
    验证密码
    
    Args:
        password: 密码
        min_length: 最小长度
        
    Returns:
        验证后的密码
        
    Raises:
        ValidationError: 如果密码无效
    """
    if not password:
        raise ValidationError("密码不能为空", field="password", value=password)
    
    if len(password) < min_length:
        raise ValidationError(
            f"密码长度至少为 {min_length} 字符，当前为: {len(password)}",
            field="password",
            value=password
        )
    
    # 检查是否包含空格
    if ' ' in password:
        raise ValidationError("密码不能包含空格", field="password", value=password)
    
    return password


# ============== 验证装饰器 ==============

def validate_fund_code_param(param_name: str = "code"):
    """
    验证基金代码参数的装饰器
    
    Args:
        param_name: URL参数名
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 获取基金代码
                if param_name in kwargs:
                    code = kwargs[param_name]
                    validated_code = validate_fund_code(code)
                    kwargs[param_name] = validated_code
                
                return func(*args, **kwargs)
            except ValidationError as e:
                logger.warning(f"基金代码验证失败: {e.message}")
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": e.message,
                        "field": e.field,
                        "value": e.value
                    }
                }), 400
        
        return wrapper
    return decorator


def validate_query_params(**validators):
    """
    验证查询参数的装饰器
    
    Args:
        validators: 参数验证器映射，格式为 {参数名: 验证函数}
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 验证查询参数
                for param_name, validator in validators.items():
                    if param_name in request.args:
                        value = request.args.get(param_name)
                        
                        # 转换类型
                        if validator in [validate_limit, validate_page]:
                            try:
                                value = int(value)
                            except ValueError:
                                raise ValidationError(
                                    f"{param_name} 必须是整数",
                                    field=param_name,
                                    value=value
                                )
                        
                        # 应用验证
                        validated_value = validator(value)
                        
                        # 将验证后的值添加到请求上下文中
                        if not hasattr(request, 'validated_params'):
                            request.validated_params = {}
                        request.validated_params[param_name] = validated_value
                
                return func(*args, **kwargs)
            except ValidationError as e:
                logger.warning(f"查询参数验证失败: {e.message}")
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": e.message,
                        "field": e.field,
                        "value": e.value
                    }
                }), 400
        
        return wrapper
    return decorator


def validate_json_body(**validators):
    """
    验证JSON请求体的装饰器
    
    Args:
        validators: 字段验证器映射，格式为 {字段名: 验证函数}
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = request.json or {}
                
                # 验证JSON体中的字段
                for field_name, validator in validators.items():
                    if field_name in data:
                        value = data[field_name]
                        validated_value = validator(value)
                        data[field_name] = validated_value
                
                # 将验证后的数据添加到请求上下文中
                request.validated_json = data
                
                return func(*args, **kwargs)
            except ValidationError as e:
                logger.warning(f"JSON请求体验证失败: {e.message}")
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": e.message,
                        "field": e.field,
                        "value": e.value
                    }
                }), 400
            except Exception as e:
                logger.error(f"JSON解析失败: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "INVALID_JSON",
                        "message": "无效的JSON格式",
                        "details": str(e)
                    }
                }), 400
        
        return wrapper
    return decorator


# ============== 工具函数 ==============

def get_validated_param(param_name: str, default: Any = None) -> Any:
    """
    获取验证后的参数（从请求上下文）
    
    Args:
        param_name: 参数名
        default: 默认值
        
    Returns:
        验证后的参数值
    """
    if hasattr(request, 'validated_params') and param_name in request.validated_params:
        return request.validated_params[param_name]
    
    # 回退到原始请求参数
    if param_name in request.args:
        return request.args.get(param_name)
    
    return default


def get_validated_json(field_name: str, default: Any = None) -> Any:
    """
    获取验证后的JSON字段（从请求上下文）
    
    Args:
        field_name: 字段名
        default: 默认值
        
    Returns:
        验证后的字段值
    """
    if hasattr(request, 'validated_json') and field_name in request.validated_json:
        return request.validated_json[field_name]
    
    # 回退到原始JSON数据
    data = request.json or {}
    return data.get(field_name, default)


# ============== 验证器注册 ==============

# 预定义的验证器映射，便于使用
VALIDATORS = {
    "fund_code": validate_fund_code,
    "limit": validate_limit,
    "page": validate_page,
    "username": validate_username,
    "password": validate_password,
}