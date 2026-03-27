"""
Cache Fetcher Functions
"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from src.cache.manager import get_cache_manager
from src.config import get_config

logger = logging.getLogger(__name__)

# 初始化缓存管理器
config = get_config()
_cache_manager = get_cache_manager()

# Redis支持检查
try:
    from src.cache.redis_cache import redis_clear as redis_clear
    from src.cache.redis_cache import redis_get, redis_set

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

logger.info(f"✅ 使用缓存管理器: {_cache_manager.__class__.__name__}")


def get_cache(key: str) -> Optional[Any]:
    """Get value from cache (使用缓存管理器)"""
    value = _cache_manager.get(key)

    if value is not None:
        # 检查是否是特殊标记（空值或错误）
        if value == "__NULL__":
            logger.debug(f"Cache penetration protected (null): {key}")
            return None
        elif value == "__ERROR__":
            logger.debug(f"Cache penetration protected (error): {key}")
            return None
        else:
            logger.debug(f"Cache hit: {key}")
            return value

    logger.debug(f"Cache miss: {key}")
    return None


def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Set value in cache (使用缓存管理器)"""
    if ttl is None:
        config = get_config()
        ttl = config.cache.duration

    success = _cache_manager.set(key, value, ttl)

    if success:
        logger.debug(f"Cache set: {key} (ttl={ttl}s)")
    else:
        logger.warning(f"Cache set failed: {key}")


def clear_cache() -> None:
    """Clear all cache"""
    _cache_manager.clear()
    logger.info("Cache cleared (using cache manager)")


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    stats = _cache_manager.get_stats()
    stats["has_redis"] = HAS_REDIS
    stats["cache_manager"] = _cache_manager.__class__.__name__
    return stats
