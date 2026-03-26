"""
独立认证模块
解决数据层(db)对Web层(web)的依赖问题
"""

import hashlib
import secrets
from typing import Optional, Tuple

# PBKDF2 迭代次数 (NIST SP 800-132 建议至少 310,000)
PBKDF2_ITERATIONS = 310000


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    哈希密码

    Args:
        password: 原始密码
        salt: 盐值，如果为None则生成随机盐

    Returns:
        哈希后的密码字符串 (格式: salt$hash)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    # 使用PBKDF2-HMAC-SHA256进行密码哈希
    # NIST SP 800-132 建议至少 310,000 次迭代以防暴力破解
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)

    # 返回 salt$hash 格式（保持与原有web/api/auth.py兼容）
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        password: 待验证的密码
        hashed_password: 存储的哈希密码 (格式: salt$hash)

    Returns:
        密码是否正确
    """
    try:
        # 解析 salt 和 hash
        if "$" in hashed_password:
            # 新格式: salt$hash
            salt, stored_hash = hashed_password.split("$", 1)
        elif ":" in hashed_password:
            # 旧格式兼容: salt:hash
            salt, stored_hash = hashed_password.split(":", 1)
        else:
            return False

        # 计算输入密码的哈希
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)

        # 比较哈希值
        return key.hex() == stored_hash
    except (ValueError, AttributeError):
        # 格式错误或参数错误
        return False


def generate_salt() -> str:
    """
    生成随机盐值

    Returns:
        16字节的随机十六进制盐值
    """
    return secrets.token_hex(16)


# 保持与原有web/api/auth.py的兼容性
__all__ = ["hash_password", "verify_password", "generate_salt"]
