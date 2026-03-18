"""
API 输入验证模块

提供统一的输入验证功能，防止安全漏洞和数据错误。
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


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
            raise ValidationError(field, "基金代码格式无效")
        
        return code
    
    @staticmethod
    def validate_amount(amount: Any, field: str = "amount") -> float:
        """验证金额"""
        amount_num = Validator.validate_number(amount, field, min_val=0)
        
        # 金额上限：1000万
        if amount_num > 10000000:
            raise ValidationError(field, "金额过大")
        
        # 金额精度：最多2位小数
        if abs(amount_num - round(amount_num, 2)) > 0.001:
            raise ValidationError(field, "金额最多保留2位小数")
        
        return round(amount_num, 2)
    
    @staticmethod
    def validate_email(email: str, field: str = "email") -> str:
        """验证邮箱格式"""
        email = Validator.validate_string(email, field, min_len=3, max_len=100)
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(field, "邮箱格式无效")
        
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
        """验证密码强度"""
        password = Validator.validate_string(password, field, min_len=6, max_len=100)
        
        # 密码强度要求
        if len(password) < 8:
            raise ValidationError(field, "密码长度至少8位")
        
        # 检查是否包含数字
        if not re.search(r'\d', password):
            raise ValidationError(field, "密码必须包含数字")
        
        # 检查是否包含字母
        if not re.search(r'[a-zA-Z]', password):
            raise ValidationError(field, "密码必须包含字母")
        
        return password
    
    @staticmethod
    def validate_date(date_str: str, field: str = "date") -> str:
        """验证日期格式"""
        date_str = Validator.validate_string(date_str, field, min_len=8, max_len=10)
        
        try:
            # 尝试解析日期
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            raise ValidationError(field, "日期格式无效，应为YYYY-MM-DD")
        
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
            raise ValidationError(field, f"最多允许{max_items}个元素")
        
        return value


# 验证器实例
validator = Validator()


def validate_holding_data(data: Dict) -> Dict:
    """
    验证持仓数据
    
    Args:
        data: 持仓数据字典
        
    Returns:
        验证后的数据
        
    Raises:
        ValidationError: 验证失败
    """
    validated = {}
    
    # 验证基金代码
    if 'code' in data:
        validated['code'] = validator.validate_fund_code(data['code'])
    
    # 验证金额
    if 'amount' in data:
        validated['amount'] = validator.validate_amount(data['amount'])
    
    # 验证基金名称（可选）
    if 'name' in data and data['name']:
        validated['name'] = validator.validate_string(data['name'], 'name', max_len=200)
    
    return validated


def validate_fund_request(data: Dict) -> Dict:
    """
    验证基金请求数据
    
    Args:
        data: 基金请求数据
        
    Returns:
        验证后的数据
    """
    validated = {}
    
    # 验证基金代码
    if 'fund_code' in data:
        validated['fund_code'] = validator.validate_fund_code(data['fund_code'])
    elif 'code' in data:
        validated['fund_code'] = validator.validate_fund_code(data['code'])
    else:
        raise ValidationError('fund_code', '基金代码不能为空')
    
    # 验证是否强制刷新
    if 'force' in data:
        if not isinstance(data['force'], bool):
            raise ValidationError('force', '必须是布尔值')
        validated['force'] = data['force']
    
    return validated


def validate_login_data(data: Dict) -> Dict:
    """
    验证登录数据
    
    Args:
        data: 登录数据
        
    Returns:
        验证后的数据
    """
    validated = {}
    
    # 验证用户名
    if 'username' in data:
        validated['username'] = validator.validate_username(data['username'])
    else:
        raise ValidationError('username', '用户名不能为空')
    
    # 验证密码
    if 'password' in data:
        validated['password'] = validator.validate_string(data['password'], 'password', min_len=1)
    else:
        raise ValidationError('password', '密码不能为空')
    
    return validated


def validate_registration_data(data: Dict) -> Dict:
    """
    验证注册数据
    
    Args:
        data: 注册数据
        
    Returns:
        验证后的数据
    """
    validated = validate_login_data(data)
    
    # 验证邮箱（可选）
    if 'email' in data and data['email']:
        validated['email'] = validator.validate_email(data['email'])
    
    return validated


def validate_batch_holdings(data: Dict) -> List[Dict]:
    """
    验证批量持仓数据
    
    Args:
        data: 批量持仓数据
        
    Returns:
        验证后的持仓列表
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
                # 添加索引信息
                raise ValidationError(f'funds[{i}].{e.field}', e.message)
    
    # 也支持单条数据格式
    elif 'code' in data:
        validated = validate_holding_data(data)
        validated_list.append(validated)
    
    else:
        raise ValidationError('funds', '缺少持仓数据')
    
    return validated_list


# 装饰器函数
def validate_request(schema: str):
    """
    请求验证装饰器
    
    Args:
        schema: 验证模式（holding, fund, login, register等）
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request
            
            # 获取请求数据
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.get_json(silent=True) or {}
            else:
                data = request.args.to_dict()
            
            try:
                # 根据schema选择验证函数
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
                from src.error import create_error_response, ErrorCode
                return create_error_response(
                    code=ErrorCode.INVALID_INPUT,
                    message=f"输入验证失败: {e.message}",
                    details={"field": e.field},
                    http_status=400
                )
            
            return func(*args, **kwargs)
        
        # 保持函数名和文档字符串
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        return wrapper
    
    return decorator