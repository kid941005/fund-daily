"""
统一的输入验证模块

合并了 src/validation.py 和 web/api/validation.py 的功能
提供完整的输入验证功能，防止安全漏洞和数据错误。
"""

import re
import functools
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
from flask import jsonify, request

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class Validator:
    """验证器基类"""
    
    @staticmethod
    def validate_not_empty(value: Any, field: str) -> Any:
        """验证值不为空"""
        if value is None:
            raise ValidationError(field, "不能为空")
        if isinstance(value, str) and not value.strip():
            raise ValidationError(field, "不能为空字符串")
        if isinstance(value, (list, dict, set)) and not value:
            raise ValidationError(field, "不能为空")
        return value
    
    @staticmethod
    def validate_string(value: Any, field: str, min_len: int = 1, max_len: int = 255) -> str:
        """验证字符串"""
        if not isinstance(value, str):
            raise ValidationError(field, "必须是字符串")
        
        value = value.strip()
        if len(value) < min_len:
            raise ValidationError(field, f"长度不能小于{min_len}")
        if len(value) > max_len:
            raise ValidationError(field, f"长度不能大于{max_len}")
        
        return value
    
    @staticmethod
    def validate_number(value: Any, field: str, min_val: Optional[float] = None, 
                       max_val: Optional[float] = None) -> float:
        """验证数字"""
        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValidationError(field, "必须是数字")
        
        if min_val is not None and num < min_val:
            raise ValidationError(field, f"不能小于{min_val}")
        if max_val is not None and num > max_val:
            raise ValidationError(field, f"不能大于{max_val}")
        
        return num
    
    @staticmethod
    def validate_integer(value: Any, field: str, min_val: Optional[int] = None,
                        max_val: Optional[int] = None) -> int:
        """验证整数"""
        try:
            num = int(value)
        except (ValueError, TypeError):
            raise ValidationError(field, "必须是整数")
        
        if min_val is not None and num < min_val:
            raise ValidationError(field, f"不能小于{min_val}")
        if max_val is not None and num > max_val:
            raise ValidationError(field, f"不能大于{max_val}")
        
        return num
    
    @staticmethod
    def validate_fund_code(code: str, field: str = "fund_code") -> str:
        """验证基金代码格式"""
        code = Validator.validate_string(code, field, min_len=6, max_len=10)
        
        # 基金代码通常为6位数字，但有些可能包含后缀
        if not re.match(r'^\d{6}[A-Z]*$', code):
            raise ValidationError(field, "基金代码格式错误，应为6位数字加可选字母后缀")
        
        return code
    
    @staticmethod
    def validate_amount(amount: Any, field: str = "amount") -> float:
        """验证金额"""
        amount_num = Validator.validate_number(amount, field, min_val=0)
        
        # 金额通常保留2位小数
        return round(amount_num, 2)
    
    @staticmethod
    def validate_email(email: str, field: str = "email") -> str:
        """验证邮箱格式"""
        email = Validator.validate_string(email, field, min_len=3, max_len=255)
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(field, "邮箱格式错误")
        
        return email.lower()
    
    @staticmethod
    def validate_username(username: str, field: str = "username") -> str:
        """验证用户名"""
        username = Validator.validate_string(username, field, min_len=3, max_len=50)
        
        # 用户名只能包含字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError(field, "用户名只能包含字母、数字和下划线")
        
        return username
    
    @staticmethod
    def validate_password(password: str, field: str = "password") -> str:
        """验证密码"""
        password = Validator.validate_string(password, field, min_len=6, max_len=100)
        
        # 密码强度检查（可选）
        # if len(password) < 8:
        #     raise ValidationError(field, "密码长度至少8位")
        # if not re.search(r'[A-Z]', password):
        #     raise ValidationError(field, "密码必须包含大写字母")
        # if not re.search(r'[a-z]', password):
        #     raise ValidationError(field, "密码必须包含小写字母")
        # if not re.search(r'\d', password):
        #     raise ValidationError(field, "密码必须包含数字")
        
        return password
    
    @staticmethod
    def validate_date(date_str: str, field: str = "date") -> str:
        """验证日期格式 (YYYY-MM-DD)"""
        date_str = Validator.validate_string(date_str, field, min_len=10, max_len=10)
        
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValidationError(field, "日期格式错误，应为YYYY-MM-DD")
        
        return date_str
    
    @staticmethod
    def validate_list(value: Any, field: str, min_items: int = 0, 
                     max_items: int = 1000) -> List:
        """验证列表"""
        if not isinstance(value, list):
            raise ValidationError(field, "必须是列表")
        
        if len(value) < min_items:
            raise ValidationError(field, f"至少需要{min_items}个元素")
        if len(value) > max_items:
            raise ValidationError(field, f"不能超过{max_items}个元素")
        
        return value


# 从 src/validation.py 合并的实用函数
validator = Validator()  # 创建实例以便使用


def validate_fund_code_simple(code: str) -> str:
    """
    简化版基金代码验证（向后兼容）
    从 src/validation.py 合并
    """
    return validator.validate_fund_code(code, "code")


def validate_limit(limit: int, min_value: int = 1, max_value: int = 100) -> int:
    """
    验证分页限制参数
    从 src/validation.py 合并
    """
    if not isinstance(limit, int):
        raise ValidationError("limit", "必须是整数")
    if limit < min_value:
        raise ValidationError("limit", f"不能小于{min_value}")
    if limit > max_value:
        raise ValidationError("limit", f"不能大于{max_value}")
    return limit


def validate_page(page: int, min_value: int = 1) -> int:
    """
    验证页码参数
    从 src/validation.py 合并
    """
    if not isinstance(page, int):
        raise ValidationError("page", "必须是整数")
    if page < min_value:
        raise ValidationError("page", f"不能小于{min_value}")
    return page


def validate_username_simple(username: str, min_length: int = 3, max_length: int = 50) -> str:
    """
    简化版用户名验证（向后兼容）
    从 src/validation.py 合并
    """
    return validator.validate_username(username, "username")


def validate_password_simple(password: str, min_length: int = 6) -> str:
    """
    简化版密码验证（向后兼容）
    从 src/validation.py 合并
    """
    return validator.validate_password(password, "password")


def validate_fund_code_param(param_name: str = "code"):
    """
    基金代码参数验证装饰器
    从 src/validation.py 合并
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            code = request.args.get(param_name)
            if not code:
                return jsonify({"success": False, "error": f"缺少{param_name}参数"}), 400
            
            try:
                validated_code = validator.validate_fund_code(code, param_name)
                # 将验证后的代码添加到kwargs
                kwargs[f'validated_{param_name}'] = validated_code
                return func(*args, **kwargs)
            except ValidationError as e:
                return jsonify({"success": False, "error": str(e)}), 400
        
        return wrapper
    return decorator


def validate_query_params(**validators):
    """
    查询参数验证装饰器
    从 src/validation.py 合并
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            validated_params = {}
            for param_name, validator_func in validators.items():
                value = request.args.get(param_name)
                if value is not None:
                    try:
                        validated_value = validator_func(value)
                        validated_params[param_name] = validated_value
                    except Exception as e:
                        return jsonify({"success": False, "error": f"参数{param_name}验证失败: {str(e)}"}), 400
            
            # 将验证后的参数添加到kwargs
            kwargs.update(validated_params)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_json_body(**validators):
    """
    JSON请求体验证装饰器
    从 src/validation.py 合并
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"success": False, "error": "请求体必须是有效的JSON"}), 400
            
            validated_data = {}
            for field_name, validator_func in validators.items():
                if field_name not in data:
                    return jsonify({"success": False, "error": f"缺少字段: {field_name}"}), 400
                
                try:
                    validated_value = validator_func(data[field_name])
                    validated_data[field_name] = validated_value
                except Exception as e:
                    return jsonify({"success": False, "error": f"字段{field_name}验证失败: {str(e)}"}), 400
            
            # 将验证后的数据添加到kwargs
            kwargs['validated_data'] = validated_data
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_validated_param(param_name: str, default: Any = None) -> Any:
    """
    获取验证后的查询参数
    从 src/validation.py 合并
    """
    from flask import request
    value = request.args.get(param_name, default)
    return value


def get_validated_json(field_name: str, default: Any = None) -> Any:
    """
    获取验证后的JSON字段
    从 src/validation.py 合并
    """
    from flask import request
    data = request.get_json(silent=True) or {}
    return data.get(field_name, default)


# 从 web/api/validation.py 保留的数据验证函数
def validate_holding_data(data: Dict) -> Dict:
    """
    验证持仓数据
    """
    validated = {}
    
    # 基金代码
    if 'code' in data:
        validated['code'] = validator.validate_fund_code(data['code'], 'code')
    elif 'fund_code' in data:
        validated['fund_code'] = validator.validate_fund_code(data['fund_code'], 'fund_code')
    else:
        raise ValidationError('code', '基金代码不能为空')
    
    # 金额
    if 'amount' in data:
        validated['amount'] = validator.validate_amount(data['amount'], 'amount')
    
    # 成本价（可选）
    if 'cost_basis' in data:
        validated['cost_basis'] = validator.validate_number(
            data['cost_basis'], 'cost_basis', min_val=0
        )
    
    # 购买日期（可选）
    if 'purchase_date' in data:
        validated['purchase_date'] = validator.validate_date(data['purchase_date'], 'purchase_date')
    
    return validated


def validate_fund_request(data: Dict) -> Dict:
    """
    验证基金请求数据
    """
    validated = {}
    
    # 基金代码
    if 'code' in data:
        validated['code'] = validator.validate_fund_code(data['code'], 'code')
    else:
        raise ValidationError('code', '基金代码不能为空')
    
    # 是否使用缓存（可选）
    if 'use_cache' in data:
        use_cache = data['use_cache']
        if not isinstance(use_cache, bool):
            raise ValidationError('use_cache', '必须是布尔值')
        validated['use_cache'] = use_cache
    
    return validated


def validate_login_data(data: Dict) -> Dict:
    """
    验证登录数据
    """
    validated = {}
    
    # 用户名
    if 'username' in data:
        validated['username'] = validator.validate_username(data['username'], 'username')
    else:
        raise ValidationError('username', '用户名不能为空')
    
    # 密码
    if 'password' in data:
        validated['password'] = validator.validate_password(data['password'], 'password')
    else:
        raise ValidationError('password', '密码不能为空')
    
    return validated


def validate_registration_data(data: Dict) -> Dict:
    """
    验证注册数据
    """
    validated = validate_login_data(data)  # 包含用户名和密码验证
    
    # 邮箱（可选）
    if 'email' in data and data['email']:
        validated['email'] = validator.validate_email(data['email'], 'email')
    
    return validated


def validate_batch_holdings(data: Dict) -> List[Dict]:
    """
    验证批量持仓数据
    """
    validated_list = []
    
    # 检查是否有funds数组
    if 'funds' in data:
        funds = validator.validate_list(data['funds'], 'funds', max_items=100)
        
        for i, fund in enumerate(funds):
            try:
                validated = validate_holding_data(fund)
                validated_list.append(validated)
            except ValidationError as e:
                # 添加索引信息以便定位错误
                raise ValidationError(f'funds[{i}].{e.field}', e.message)
    else:
        raise ValidationError('funds', '缺少funds数组')
    
    return validated_list


def validate_request(schema: str):
    """
    请求验证装饰器
    
    Args:
        schema: 验证模式（holding, fund, login, register, batch_holdings等）
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from src.error import create_error_response, ErrorCode
            
            data = request.get_json(silent=True)
            if data is None:
                return create_error_response(
                    ErrorCode.INVALID_REQUEST,
                    "请求体必须是有效的JSON"
                ), 400
            
            try:
                if schema == 'holding':
                    validated_data = validate_holding_data(data)
                elif schema == 'fund':
                    validated_data = validate_fund_request(data)
                elif schema == 'login':
                    validated_data = validate_login_data(data)
                elif schema == 'register':
                    validated_data = validate_registration_data(data)
                elif schema == 'batch_holdings':
                    validated_data = validate_batch_holdings(data)
                else:
                    raise ValueError(f"未知的验证模式: {schema}")
                
                # 将验证后的数据添加到请求上下文
                request.validated_data = validated_data
                
            except ValidationError as e:
                return create_error_response(
                    ErrorCode.VALIDATION_ERROR,
                    str(e),
                    details={"field": e.field}
                ), 400
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator