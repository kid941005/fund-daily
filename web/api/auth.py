"""
Authentication helpers for Fund Daily
使用独立的src.auth模块，避免重复实现
"""

# 导入独立的认证模块
from src.auth import hash_password, verify_password, generate_salt

# 保持原有API兼容性
__all__ = ["hash_password", "verify_password", "generate_salt"]
