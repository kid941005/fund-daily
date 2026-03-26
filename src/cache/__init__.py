# Cache module - 统一缓存接口
# 注意：旧的 get_cache/set_cache/clear_cache 接口已废弃
# 请使用 CacheManager 或 cached 装饰器

from .manager import (
    CacheManager,
    cached,
    get_cache_manager,
)

# 向后兼容导出（不推荐使用）
from .redis_cache import (
    get_redis_client,
    redis_clear,
    redis_delete,
    redis_get,
    redis_set,
)


# 定义向后兼容的函数（使用新的缓存管理器）
def get_cache(key: str) -> any:
    """向后兼容：获取缓存值（使用缓存管理器）"""
    manager = get_cache_manager()
    value = manager.get(key)

    # 处理特殊标记
    if value in ("__NULL__", "__ERROR__"):
        return None
    return value


def set_cache(key: str, value: any, ttl: int = None) -> bool:
    """向后兼容：设置缓存值（使用缓存管理器）"""
    manager = get_cache_manager()
    return manager.set(key, value, ttl)


def clear_cache() -> bool:
    """向后兼容：清空缓存（使用缓存管理器）"""
    manager = get_cache_manager()
    return manager.clear()
