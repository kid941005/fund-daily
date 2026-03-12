"""
Authentication helpers for Fund Daily
"""

import secrets
import hashlib


def hash_password(password: str, salt: str = None) -> str:
    """Hash password with salt using PBKDF2"""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash"""
    try:
        salt, key = stored_hash.split('$')
        new_hash = hash_password(password, salt)
        return new_hash == stored_hash
    except (ValueError, TypeError):
        return False
