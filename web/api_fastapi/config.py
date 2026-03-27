"""
FastAPI Configuration Dependencies
"""

import os
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import get_config

_config = None


def get_fastapi_config():
    """Get FastAPI configuration from Flask's config manager"""
    global _config
    if _config is None:
        _config = get_config()
    return _config


# Re-export commonly used config attributes
def get_database_config():
    """Get database configuration"""
    config = get_fastapi_config()
    return {
        "type": "postgres",
        "host": config.database.host,
        "port": config.database.port,
        "name": config.database.name,
        "user": config.database.user,
        "password": config.database.password,
    }


def get_redis_config():
    """Get Redis configuration"""
    config = get_fastapi_config()
    return {
        "host": config.redis.host,
        "port": config.redis.port,
        "db": config.redis.db,
        "password": config.redis.password,
        "ttl": config.redis.ttl,
    }


def get_security_config():
    """Get security configuration"""
    config = get_fastapi_config()
    return config.security


def get_jwt_config():
    """Get JWT configuration"""
    config = get_fastapi_config()
    return config.security.jwt


def get_cache_config():
    """Get cache configuration"""
    config = get_fastapi_config()
    return config.cache


def get_server_config():
    """Get server configuration"""
    config = get_fastapi_config()
    return config.server


def get_app_config():
    """Get app configuration"""
    config = get_fastapi_config()
    return config.app
