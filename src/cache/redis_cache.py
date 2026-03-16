# Redis 缓存层
import os
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Redis 配置
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_TTL = int(os.environ.get("REDIS_TTL", 1800))  # 默认30分钟

_redis_client = None


def get_redis_client():
    """获取 Redis 客户端（单例）"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            # 测试连接
            _redis_client.ping()
            logger.info(f"✅ Redis 连接成功: {REDIS_HOST}:{REDIS_PORT}")
        except ImportError:
            logger.warning("⚠️ redis-py 未安装，使用内存缓存")
            _redis_client = None
        except Exception as e:
            logger.warning(f"⚠️ Redis 连接失败: {e}，使用内存缓存")
            _redis_client = None
    return _redis_client


def redis_get(key: str) -> Optional[Any]:
    """从 Redis 获取值"""
    client = get_redis_client()
    if client is None:
        return None
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.debug(f"Redis get error: {e}")
    return None


def redis_set(key: str, value: Any, ttl: int = None) -> bool:
    """设置 Redis 值"""
    client = get_redis_client()
    if client is None:
        return False
    try:
        ttl = ttl or REDIS_TTL
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.debug(f"Redis set error: {e}")
        return False


def redis_delete(key: str) -> bool:
    """删除 Redis 值"""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Redis delete error: {e}")
        return False


def redis_clear() -> bool:
    """清空 Redis 缓存"""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.flushdb()
        return True
    except Exception as e:
        logger.debug(f"Redis clear error: {e}")
        return False


# 兼容原有接口
def get_cache(key: str) -> Optional[Any]:
    """获取缓存（先查 Redis，再查内存）"""
    # 优先从 Redis 获取
    value = redis_get(key)
    if value is not None:
        return value
    return None


def set_cache(key: str, value: Any) -> None:
    """设置缓存（同时写入 Redis 和内存）"""
    redis_set(key, value)


def clear_cache() -> None:
    """清空缓存"""
    redis_clear()
