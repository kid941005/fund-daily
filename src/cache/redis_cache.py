# Redis 缓存层
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 导入配置管理器
from src.config import get_config

_redis_client = None


def get_redis_client():
    """获取 Redis 客户端（单例）"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis

            config = get_config().redis

            _redis_client = redis.Redis(
                host=config.host,
                port=config.port,
                db=config.db,
                password=config.password,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            # 测试连接
            _redis_client.ping()
            logger.info(f"✅ Redis 连接成功: {config.host}:{config.port}")
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
        if ttl is None:
            config = get_config().redis
            ttl = config.ttl
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


# ============== Token 黑名单 ==============

TOKEN_BLACKLIST_PREFIX = "token:blacklist:"


def is_token_blacklisted(token: str) -> bool:
    """
    检查 Token 是否在黑名单中

    Args:
        token: JWT token

    Returns:
        True if token is blacklisted (should be rejected)
    """
    client = get_redis_client()
    if client is None:
        return False
    try:
        key = TOKEN_BLACKLIST_PREFIX + token
        return client.exists(key) == 1
    except Exception as e:
        logger.error(f"检查 Token 黑名单失败: {e}")
        return False


def add_token_to_blacklist(token: str, expires_in: int = None) -> bool:
    """
    将 Token 加入黑名单

    Args:
        token: JWT token
        expires_in: 过期时间（秒），默认使用 JWT 的剩余有效时间

    Returns:
        True if added successfully
    """
    client = get_redis_client()
    if client is None:
        return False
    try:
        key = TOKEN_BLACKLIST_PREFIX + token
        if expires_in is None:
            # 默认 24 小时
            expires_in = 86400
        client.setex(key, expires_in, "1")
        logger.info(f"Token 已加入黑名单")
        return True
    except Exception as e:
        logger.error(f"添加 Token 到黑名单失败: {e}")
        return False


def remove_token_from_blacklist(token: str) -> bool:
    """
    将 Token 从黑名单移除

    Args:
        token: JWT token

    Returns:
        True if removed successfully
    """
    client = get_redis_client()
    if client is None:
        return False
    try:
        key = TOKEN_BLACKLIST_PREFIX + token
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"从黑名单移除 Token 失败: {e}")
        return False


# ============== 登录失败次数限制 ==============

LOGIN_FAIL_PREFIX = "login:fail:"


def get_login_fail_count(username: str) -> int:
    """
    获取用户登录失败次数

    Args:
        username: 用户名

    Returns:
        失败次数
    """
    client = get_redis_client()
    if client is None:
        return 0
    try:
        key = LOGIN_FAIL_PREFIX + username
        count = client.get(key)
        return int(count) if count else 0
    except Exception as e:
        logger.error(f"获取登录失败次数失败: {e}")
        return 0


def increment_login_fail_count(username: str, lockout_seconds: int = 900) -> int:
    """
    增加登录失败次数

    Args:
        username: 用户名
        lockout_seconds: 锁定时间（默认15分钟）

    Returns:
        新的失败次数
    """
    client = get_redis_client()
    if client is None:
        # Redis 不可用时，记录严重错误并返回锁定阈值（安全优先）
        logger.critical(f"Redis 不可用，无法记录登录失败次数，用户 {username} 被锁定")
        return 999  # 返回高值以触发账户锁定
    try:
        key = LOGIN_FAIL_PREFIX + username
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, lockout_seconds)
        results = pipe.execute()
        new_count = results[0]

        # 如果达到5次失败，额外设置锁定标记
        if new_count >= 5:
            lock_key = LOGIN_FAIL_PREFIX + username + ":locked"
            client.setex(lock_key, lockout_seconds, "1")
            logger.warning(f"用户 {username} 登录失败 {new_count} 次，账户已锁定")

        return new_count
    except Exception as e:
        logger.error(f"增加登录失败次数失败: {e}")
        return 999  # 失败时返回高值（安全优先）


def reset_login_fail_count(username: str) -> bool:
    """
    重置登录失败次数（登录成功后调用）

    Args:
        username: 用户名

    Returns:
        True if reset successfully
    """
    client = get_redis_client()
    if client is None:
        # Redis 不可用时，返回 False 阻止登录（安全优先）
        logger.critical("Redis 不可用，拒绝重置登录失败计数（安全策略）")
        return False
    try:
        key = LOGIN_FAIL_PREFIX + username
        lock_key = LOGIN_FAIL_PREFIX + username + ":locked"
        client.delete(key)
        client.delete(lock_key)
        return True
    except Exception as e:
        logger.error(f"重置登录失败次数失败: {e}")
        return False


def is_account_locked(username: str) -> bool:
    """
    检查账户是否被锁定

    Args:
        username: 用户名

    Returns:
        True if locked
    """
    client = get_redis_client()
    if client is None:
        # Redis 不可用时，返回 True（锁定）以保护账户（安全优先）
        logger.critical("Redis 不可用，假定账户已锁定（安全策略）")
        return True
    try:
        key = LOGIN_FAIL_PREFIX + username + ":locked"
        return client.exists(key) == 1
    except Exception as e:
        logger.error(f"检查账户锁定状态失败: {e}")
        return True  # 失败时假定已锁定（安全优先）


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


# 注意：以下函数已废弃，请使用 CacheManager
# 保留这些函数仅用于向后兼容

import warnings


def get_cache(key: str) -> Optional[Any]:
    """【已废弃】获取缓存（请使用 CacheManager.get()）"""
    warnings.warn("get_cache() is deprecated, use CacheManager.get() instead", DeprecationWarning, stacklevel=2)
    # 优先从 Redis 获取
    value = redis_get(key)
    if value is not None:
        return value
    return None


def set_cache(key: str, value: Any) -> None:
    """【已废弃】设置缓存（请使用 CacheManager.set()）"""
    warnings.warn("set_cache() is deprecated, use CacheManager.set() instead", DeprecationWarning, stacklevel=2)
    redis_set(key, value)


def clear_cache() -> None:
    """【已废弃】清空缓存（请使用 CacheManager.clear()）"""
    warnings.warn("clear_cache() is deprecated, use CacheManager.clear() instead", DeprecationWarning, stacklevel=2)
    redis_clear()
