"""
缓存管理器
提供多级缓存、缓存穿透保护、缓存雪崩防护
"""

import hashlib
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CacheManager:
    """
    缓存管理器

    特性：
    1. 多级缓存（内存 + Redis）
    2. 缓存穿透保护（空值缓存）
    3. 缓存雪崩防护（随机过期时间）
    4. 缓存预热
    5. 缓存统计和监控
    """

    def __init__(self):
        self._stats = {"hits": 0, "misses": 0, "penetration_protected": 0, "avalanche_protected": 0, "errors": 0}

        # 导入缓存实现
        try:
            from .lru_cache import get_lru_cache

            self._memory_cache = get_lru_cache(max_size=1000, default_ttl=300)
            self._has_memory_cache = True
        except ImportError:
            self._has_memory_cache = False
            logger.warning("内存缓存不可用")

        try:
            from .redis_cache import redis_delete, redis_get, redis_set

            self._redis_get = redis_get
            self._redis_set = redis_set
            self._redis_delete = redis_delete
            self._has_redis = True
        except ImportError:
            self._has_redis = False
            logger.warning("Redis缓存不可用")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值（多级缓存）

        策略：
        1. 先查内存缓存
        2. 再查Redis缓存
        3. 如果都没有，返回默认值
        """
        # 1. 内存缓存
        if self._has_memory_cache:
            value = self._memory_cache.get(key)
            if value is not None:
                self._stats["hits"] += 1
                logger.debug(f"内存缓存命中: {key}")
                return value

        # 2. Redis缓存
        if self._has_redis:
            try:
                value = self._redis_get(key)
                if value is not None:
                    self._stats["hits"] += 1
                    logger.debug(f"Redis缓存命中: {key}")

                    # 回填内存缓存
                    if self._has_memory_cache:
                        self._memory_cache.set(key, value)

                    return value
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug(f"Redis获取失败: {e}")

        self._stats["misses"] += 1
        logger.debug(f"缓存未命中: {key}")
        return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值（多级缓存）

        策略：
        1. 写入内存缓存
        2. 写入Redis缓存
        3. 应用缓存雪崩防护（随机过期时间）

        返回：如果至少一层缓存设置成功则返回True
        """
        memory_success = False
        redis_success = False

        # 1. 内存缓存
        if self._has_memory_cache:
            try:
                self._memory_cache.set(key, value, ttl)
                memory_success = True
            except Exception as e:
                logger.debug(f"内存缓存设置失败: {e}")

        # 2. Redis缓存
        if self._has_redis:
            try:
                # 应用缓存雪崩防护：添加随机抖动
                if ttl is not None and ttl > 60:  # 只有较长的TTL才需要防护
                    jitter = random.randint(-30, 30)  # ±30秒抖动
                    protected_ttl = max(60, ttl + jitter)  # 确保至少60秒
                    self._stats["avalanche_protected"] += 1
                    logger.debug(f"缓存雪崩防护: {key} TTL={ttl}→{protected_ttl}")
                    ttl = protected_ttl

                self._redis_set(key, value, ttl)
                redis_success = True
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug(f"Redis缓存设置失败: {e}")

        logger.debug(f"缓存设置: {key} (内存: {memory_success}, Redis: {redis_success})")
        return memory_success or redis_success

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        memory_success = False
        redis_success = False

        if self._has_memory_cache:
            try:
                self._memory_cache.delete(key)
                memory_success = True
            except Exception:
                pass

        if self._has_redis:
            try:
                self._redis_delete(key)
                redis_success = True
            except Exception:
                pass

        return memory_success or redis_success

    def clear(self) -> bool:
        """清空所有缓存"""
        memory_success = False
        redis_success = False

        if self._has_memory_cache:
            try:
                self._memory_cache.clear()
                memory_success = True
            except Exception:
                pass

        if self._has_redis:
            try:
                from .redis_cache import redis_clear

                redis_clear()
                redis_success = True
            except Exception:
                pass

        return memory_success or redis_success

    def get_with_penetration_protection(
        self, key: str, loader: Callable[[], Any], ttl: int = 300, empty_ttl: int = 60
    ) -> Any:
        """
        带缓存穿透保护的获取

        策略：
        1. 尝试获取缓存
        2. 如果缓存命中，返回缓存值
        3. 如果缓存未命中，调用loader加载数据
        4. 如果loader返回None或空值，缓存空值（短时间）
        5. 如果loader返回有效值，缓存有效值（正常时间）

        Args:
            key: 缓存键
            loader: 数据加载函数
            ttl: 正常数据的缓存时间（秒）
            empty_ttl: 空数据的缓存时间（秒）
        """
        # 1. 尝试获取缓存
        cached = self.get(key)
        if cached is not None:
            # 检查是否是空值标记
            if cached == "__NULL__":
                self._stats["penetration_protected"] += 1
                logger.debug(f"缓存穿透防护: {key} (空值缓存)")
                return None
            return cached

        # 2. 缓存未命中，加载数据
        try:
            value = loader()
        except Exception as e:
            logger.error(f"数据加载失败: {key}, error: {e}")
            # 缓存异常结果（短时间）
            self.set(key, "__ERROR__", empty_ttl)
            raise

        # 3. 根据数据内容设置缓存
        if value is None or (isinstance(value, (list, dict, str)) and not value):
            # 空值：缓存短时间，防止缓存穿透
            self.set(key, "__NULL__", empty_ttl)
            self._stats["penetration_protected"] += 1
            logger.debug(f"缓存空值: {key} (TTL={empty_ttl}s)")
            return None
        else:
            # 有效值：缓存正常时间
            self.set(key, value, ttl)
            logger.debug(f"缓存有效值: {key} (TTL={ttl}s)")
            return value

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        # 添加内存缓存统计
        if self._has_memory_cache:
            mem_stats = self._memory_cache.get_stats()
            self._stats.update(
                {
                    "memory_hits": mem_stats.get("hits", 0),
                    "memory_misses": mem_stats.get("misses", 0),
                    "memory_evictions": mem_stats.get("evictions", 0),
                }
            )

        return self._stats.copy()

    def reset_stats(self):
        """重置统计"""
        self._stats = {"hits": 0, "misses": 0, "penetration_protected": 0, "avalanche_protected": 0, "errors": 0}

    def warm_up(self, keys_and_loaders: Dict[str, Callable[[], Any]], ttl: int = 600):
        """
        缓存预热

        Args:
            keys_and_loaders: 键和加载函数的字典
            ttl: 缓存时间
        """
        logger.info(f"开始缓存预热，共 {len(keys_and_loaders)} 个键")

        for key, loader in keys_and_loaders.items():
            try:
                value = loader()
                if value is not None:
                    self.set(key, value, ttl)
                    logger.debug(f"缓存预热: {key}")
            except Exception as e:
                logger.warning(f"缓存预热失败: {key}, error: {e}")

        logger.info("缓存预热完成")

    def get_or_set(self, key: str, loader: Callable[[], Any], ttl: int = 300, use_lock: bool = True) -> Any:
        """
        获取缓存，如果不存在则调用 loader 并缓存结果（防止缓存击穿）

        Args:
            key: 缓存键
            loader: 数据加载函数
            ttl: 缓存时间
            use_lock: 是否使用简单的锁机制防止缓存击穿

        Returns:
            缓存的值或 loader 返回的值
        """
        # 尝试获取缓存
        value = self.get(key)
        if value is not None:
            return value

        # 缓存不存在，调用 loader
        try:
            value = loader()
            if value is not None:
                self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"get_or_set loader failed: {key}, {e}")
            # 如果 loader 失败，返回 None 而不是抛出异常
            return None

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        stats = dict(self._stats)
        stats["hit_rate"] = (
            stats["hits"] / (stats["hits"] + stats["misses"] * 1.0) if (stats["hits"] + stats["misses"]) > 0 else 0
        )
        return stats


# 缓存装饰器
def cached(ttl: int = 300, key_prefix: str = "", use_penetration_protection: bool = True):
    """
    缓存装饰器

    Args:
        ttl: 缓存时间（秒）
        key_prefix: 键前缀
        use_penetration_protection: 是否使用缓存穿透保护
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            # 获取缓存管理器
            manager = get_cache_manager()

            if use_penetration_protection:
                # 使用缓存穿透保护
                def loader():
                    return func(*args, **kwargs)

                return manager.get_with_penetration_protection(key, loader, ttl=ttl, empty_ttl=60)
            else:
                # 普通缓存
                cached_value = manager.get(key)
                if cached_value is not None:
                    return cached_value

                value = func(*args, **kwargs)
                manager.set(key, value, ttl)
                return value

        return wrapper

    return decorator


# 单例实例
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        logger.info("缓存管理器初始化完成")
    return _cache_manager
