"""
线程安全的速率限制器
"""

import time
import threading
import logging
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    线程安全的速率限制器

    特性：
    1. 基于键的速率限制（如IP、用户ID、API端点）
    2. 滑动窗口算法
    3. 线程安全
    4. 可配置的限制和窗口大小
    """

    def __init__(self, default_limit: int = 10, default_window: int = 60):
        """
        初始化速率限制器

        Args:
            default_limit: 默认请求限制数
            default_window: 默认时间窗口（秒）
        """
        self.default_limit = default_limit
        self.default_window = default_window

        # 存储每个键的请求时间戳
        self._requests = defaultdict(list)
        self._lock = threading.RLock()

    def is_allowed(self, key: str, limit: Optional[int] = None, window: Optional[int] = None) -> bool:
        """
        检查是否允许请求

        Args:
            key: 限制键（如IP、用户ID）
            limit: 请求限制数（使用默认值如果为None）
            window: 时间窗口（秒，使用默认值如果为None）

        Returns:
            bool: 是否允许请求
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        current_time = time.time()
        window_start = current_time - window

        with self._lock:
            # 获取该键的请求记录
            timestamps = self._requests[key]

            # 移除窗口外的旧记录
            while timestamps and timestamps[0] < window_start:
                timestamps.pop(0)

            # 检查是否超过限制
            if len(timestamps) >= limit:
                logger.debug(f"速率限制: key={key}, 请求数={len(timestamps)}, 限制={limit}")
                return False

            # 添加当前请求时间戳
            timestamps.append(current_time)

            # 保持列表有序（已经是，因为时间递增）
            return True

    def get_remaining(self, key: str, limit: Optional[int] = None, window: Optional[int] = None) -> int:
        """
        获取剩余请求次数

        Args:
            key: 限制键
            limit: 请求限制数
            window: 时间窗口（秒）

        Returns:
            int: 剩余请求次数
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        current_time = time.time()
        window_start = current_time - window

        with self._lock:
            timestamps = self._requests[key]

            # 移除窗口外的旧记录
            while timestamps and timestamps[0] < window_start:
                timestamps.pop(0)

            return max(0, limit - len(timestamps))

    def get_reset_time(self, key: str, window: Optional[int] = None) -> float:
        """
        获取限制重置时间

        Args:
            key: 限制键
            window: 时间窗口（秒）

        Returns:
            float: 重置时间戳（Unix时间）
        """
        window = window or self.default_window

        with self._lock:
            timestamps = self._requests[key]

            if not timestamps:
                return time.time()

            # 最旧的请求时间 + 窗口大小
            oldest = timestamps[0]
            return oldest + window

    def clear(self, key: Optional[str] = None):
        """
        清除限制记录

        Args:
            key: 要清除的键，如果为None则清除所有
        """
        with self._lock:
            if key is None:
                self._requests.clear()
            elif key in self._requests:
                del self._requests[key]

    def get_stats(self, key: str) -> dict:
        """
        获取键的统计信息

        Args:
            key: 限制键

        Returns:
            dict: 统计信息
        """
        with self._lock:
            timestamps = self._requests[key]
            current_time = time.time()

            # 计算最近1分钟、5分钟、1小时的请求数
            stats = {
                "total_requests": len(timestamps),
                "last_request": timestamps[-1] if timestamps else None,
                "recent_1m": len([t for t in timestamps if t > current_time - 60]),
                "recent_5m": len([t for t in timestamps if t > current_time - 300]),
                "recent_1h": len([t for t in timestamps if t > current_time - 3600]),
            }

            return stats


# 全局实例（用于fetcher模块）
_fetcher_rate_limiter = RateLimiter(default_limit=1, default_window=0.5)


def wait_if_needed():
    """等待直到允许下一个请求（用于fetcher模块）"""
    # 从配置获取请求间隔
    from src.config import get_config

    config = get_config()
    request_interval = config.cache.request_interval

    # 更新速率限制器配置
    if request_interval > 0:
        # 计算限制：1个请求 / request_interval秒
        limit = 1
        window = request_interval
        _fetcher_rate_limiter.default_limit = limit
        _fetcher_rate_limiter.default_window = window

    key = "fetcher_global"  # 全局限制键

    while not _fetcher_rate_limiter.is_allowed(key):
        # 计算需要等待的时间
        reset_time = _fetcher_rate_limiter.get_reset_time(key)
        wait_time = max(0, reset_time - time.time())

        if wait_time > 0:
            logger.debug(f"速率限制: 等待 {wait_time:.2f}s")
            time.sleep(min(wait_time, 0.1))  # 最多睡眠0.1秒，然后重试

    return True


def update_fetcher_config(limit: int, window: float):
    """更新fetcher速率限制配置"""
    _fetcher_rate_limiter.default_limit = limit
    _fetcher_rate_limiter.default_window = window
