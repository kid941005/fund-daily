"""
缓存实现
适配现有缓存模块到接口
"""

import logging
from typing import Optional, Any
from .interfaces import ICache
from .cache.redis_cache import redis_get, redis_set, redis_delete

logger = logging.getLogger(__name__)


class CacheImpl(ICache):
    """缓存实现类"""
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            return redis_get(key)
        except Exception as e:
            logger.error(f"获取缓存异常: {key}, {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存"""
        try:
            return redis_set(key, value, ttl)
        except Exception as e:
            logger.error(f"设置缓存异常: {key}, {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return redis_delete(key)
        except Exception as e:
            logger.error(f"删除缓存异常: {key}, {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            # 尝试获取键，如果不为None则存在
            value = redis_get(key)
            return value is not None
        except Exception as e:
            logger.error(f"检查缓存存在异常: {key}, {e}")
            return False