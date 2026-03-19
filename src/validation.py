"""
验证模块重定向文件

注意: 此模块已迁移到 web.api.validation
请更新导入语句: from web.api.validation import ...
"""

import warnings
import sys

# 显示弃用警告
warnings.warn(
    "src.validation is deprecated, use web.api.validation instead",
    DeprecationWarning,
    stacklevel=2
)

# 动态导入 web.api.validation 的所有内容
try:
    from web.api.validation import *
except ImportError as e:
    raise ImportError(
        f"无法导入 web.api.validation: {e}\n"
        "请确保 web.api.validation 模块存在"
    ) from e

# 提供向后兼容的别名
__all__ = [
    'ValidationError',
    'Validator',
    'validator',
    'validate_fund_code_simple',
    'validate_limit',
    'validate_page',
    'validate_username_simple',
    'validate_password_simple',
    'validate_fund_code_param',
    'validate_query_params',
    'validate_json_body',
    'get_validated_param',
    'get_validated_json',
    'validate_holding_data',
    'validate_fund_request',
    'validate_login_data',
    'validate_registration_data',
    'validate_batch_holdings',
    'validate_request'
]

# 向后兼容的别名
validate_fund_code = validate_fund_code_simple
validate_username = validate_username_simple
validate_password = validate_password_simple