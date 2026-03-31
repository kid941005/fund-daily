"""
LRU缓存实现
防止内存泄漏，支持缓存大小限制和LRU驱逐策略
"""

import logging
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class LRUCache:
    """
    LRU (Least Recently Used) 缓存实现

    特性：
    - 最大容量限制
    - LRU驱逐策略
    - 缓存过期时间
    - 命中率统计
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 600):
        """
        初始化LRU缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: dict[str, float] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl

        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期返回None
        """
        if key not in self._cache:
            self._misses += 1
            return None

        # 检查是否过期
        timestamp = self._timestamps.get(key, 0)
        if time.time() - timestamp > self.default_ttl:
            # 已过期，删除
            self._remove(key)
            self._misses += 1
            return None

        # 移动到末尾（表示最近使用）
        self._cache.move_to_end(key)

        self._hits += 1
        return self._cache[key]

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None则使用默认值
        """
        # 如果键已存在，先删除
        if key in self._cache:
            self._remove(key)

        # 如果缓存已满，驱逐最老的条目
        while len(self._cache) >= self.max_size:
            self._evict_oldest()

        # 添加新条目
        self._cache[key] = value
        self._timestamps[key] = time.time()
        self._cache.move_to_end(key)

        logger.debug(f"LRU Cache set: {key} (size: {len(self._cache)}/{self.max_size})")

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        if key in self._cache:
            self._remove(key)
            return True
        return False

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("LRU Cache cleared")

    def _remove(self, key: str) -> None:
        """内部方法：移除指定键"""
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]

    def _evict_oldest(self) -> None:
        """内部方法：驱逐最老的条目"""
        if not self._cache:
            return

        # 驱逐最老的条目（OrderedDict的第一个元素）
        oldest_key = next(iter(self._cache))
        self._remove(oldest_key)
        self._evictions += 1

        logger.debug(f"LRU Cache evicted: {oldest_key}")

    def exists(self, key: str) -> bool:
        """
        检查键是否存在且未过期

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if key not in self._cache:
            return False

        # 检查是否过期
        timestamp = self._timestamps.get(key, 0)
        if time.time() - timestamp > self.default_ttl:
            self._remove(key)
            return False

        return True

    def size(self) -> int:
        """获取当前缓存大小"""
        return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate * 100, 2),
            "total_requests": total,
        }

    def get_stats(self) -> dict[str, int]:
        """获取统计信息"""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "size": len(self._cache),
            "max_size": self.max_size,
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def __contains__(self, key: str) -> bool:
        """支持 'in' 操作符"""
        return self.exists(key)

    def __len__(self) -> int:
        """支持 len() 函数"""
        return len(self._cache)

    def __repr__(self) -> str:
        return f"LRUCache(size={len(self._cache)}, max={self.max_size}, {self.stats()})"


# 全局LRU缓存实例
_lru_cache: LRUCache | None = None


def get_lru_cache(max_size: int = 1000, default_ttl: int = 600) -> LRUCache:
    """
    获取全局LRU缓存实例（单例模式）

    Args:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间（秒）

    Returns:
        LRUCache实例
    """
    global _lru_cache
    if _lru_cache is None:
        _lru_cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
        logger.info(f"LRU缓存初始化: max_size={max_size}, ttl={default_ttl}s")
    return _lru_cache


def create_lru_cache(max_size: int = 1000, default_ttl: int = 600) -> LRUCache:
    """
    创建新的LRU缓存实例（非单例）

    Args:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间（秒）

    Returns:
        新的LRUCache实例
    """
    return LRUCache(max_size=max_size, default_ttl=default_ttl)


# 便捷函数
def lru_get(key: str) -> Any | None:
    """从全局LRU缓存获取值"""
    return get_lru_cache().get(key)


def lru_set(key: str, value: Any, ttl: int | None = None) -> None:
    """设置全局LRU缓存值"""
    get_lru_cache().set(key, value, ttl)


def lru_delete(key: str) -> bool:
    """从全局LRU缓存删除值"""
    return get_lru_cache().delete(key)


def lru_clear() -> None:
    """清空全局LRU缓存"""
    get_lru_cache().clear()


def lru_stats() -> dict[str, Any]:
    """获取全局LRU缓存统计"""
    return get_lru_cache().stats()
