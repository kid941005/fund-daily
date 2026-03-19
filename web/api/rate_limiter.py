"""
API 速率限制模块

提供统一的API速率限制功能，防止滥用和DDoS攻击。
基于Flask-Limiter实现，支持Redis存储。
"""

import time
from typing import Dict, List, Optional, Tuple
from flask import
from src.config import get_config request, current_app
from functools import wraps
import redis
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, redis_client=None):
        """
        初始化速率限制器
        
        Args:
            redis_client: Redis客户端实例，如果为None则创建新连接
        """
        self.redis_client = redis_client or self._create_redis_client()
        self.default_limits = {
            "default": "100 per minute",  # 默认限制
            "auth": "10 per minute",      # 认证相关端点
            "funds": "30 per minute",     # 基金数据端点
            "holdings": "20 per minute",  # 持仓管理端点
            "quant": "15 per minute",     # 量化分析端点
            "import": "5 per minute",     # 数据导入端点
        }
        
    def _create_redis_client(self):
        """创建Redis客户端"""
        try:
            config = get_config()
            redis_host = config.redis.host
            redis_port = config.redis.port
            redis_db = config.redis.db
            
            return redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        except Exception as e:
            logger.warning(f"无法连接Redis，使用内存存储: {e}")
            return None
    
    def get_client_ip(self) -> str:
        """获取客户端IP地址"""
        # 优先使用X-Forwarded-For头部（代理场景）
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip = request.remote_addr or '127.0.0.1'
        
        # 处理IPv6映射的IPv4地址
        if ip.startswith('::ffff:'):
            ip = ip[7:]
            
        return ip
    
    def get_user_id(self) -> str:
        """获取用户ID（用于用户级限流）"""
        from flask import session
        user_id = session.get("user_id")
        if user_id:
            return f"user:{user_id}"
        return "anonymous"
    
    def get_endpoint_key(self) -> str:
        """获取端点标识"""
        return f"{request.endpoint or 'unknown'}"
    
    def get_limit_key(self, limit_name: str = "default") -> str:
        """
        获取限流键
        
        Args:
            limit_name: 限制名称
            
        Returns:
            限流键字符串
        """
        client_ip = self.get_client_ip()
        user_id = self.get_user_id()
        endpoint = self.get_endpoint_key()
        
        # 构建限流键: rate_limit:{limit_name}:{user_id}:{endpoint}:{ip}
        return f"rate_limit:{limit_name}:{user_id}:{endpoint}:{client_ip}"
    
    def parse_limit_string(self, limit_str: str) -> Tuple[int, int]:
        """
        解析限制字符串
        
        Args:
            limit_str: 如 "100 per minute", "10 per second"
            
        Returns:
            (限制次数, 时间窗口秒数)
        """
        try:
            parts = limit_str.lower().split()
            if len(parts) != 3 or parts[1] != "per":
                raise ValueError(f"无效的限制格式: {limit_str}")
            
            count = int(parts[0])
            unit = parts[2]
            
            # 转换为秒数
            unit_seconds = {
                "second": 1,
                "seconds": 1,
                "sec": 1,
                "minute": 60,
                "minutes": 60,
                "min": 60,
                "hour": 3600,
                "hours": 3600,
                "hr": 3600,
                "day": 86400,
                "days": 86400,
                "week": 604800,
                "weeks": 604800,
                "month": 2592000,  # 30天
                "months": 2592000,
                "year": 31536000,  # 365天
                "years": 31536000,
            }
            
            if unit not in unit_seconds:
                raise ValueError(f"未知的时间单位: {unit}")
            
            return count, unit_seconds[unit]
            
        except Exception as e:
            logger.error(f"解析限制字符串失败 {limit_str}: {e}")
            return 100, 60  # 默认: 100次/分钟
    
    def check_rate_limit(self, limit_name: str = "default") -> Dict:
        """
        检查速率限制
        
        Args:
            limit_name: 限制名称
            
        Returns:
            包含限制状态的字典
        """
        try:
            # 获取限制配置
            limit_str = self.default_limits.get(limit_name, self.default_limits["default"])
            max_requests, window_seconds = self.parse_limit_string(limit_str)
            
            # 获取限流键
            key = self.get_limit_key(limit_name)
            current_time = int(time.time())
            
            if self.redis_client:
                # 使用Redis存储
                pipeline = self.redis_client.pipeline()
                
                # 移除过期的请求记录
                pipeline.zremrangebyscore(key, 0, current_time - window_seconds)
                
                # 获取当前窗口内的请求数
                pipeline.zcard(key)
                
                # 添加当前请求
                pipeline.zadd(key, {str(current_time): current_time})
                
                # 设置键的过期时间
                pipeline.expire(key, window_seconds)
                
                results = pipeline.execute()
                current_count = results[1]
                
            else:
                # 使用内存存储（仅用于开发环境）
                if not hasattr(self, '_memory_store'):
                    self._memory_store = {}
                
                if key not in self._memory_store:
                    self._memory_store[key] = []
                
                # 清理过期记录
                self._memory_store[key] = [
                    ts for ts in self._memory_store[key]
                    if ts > current_time - window_seconds
                ]
                
                current_count = len(self._memory_store[key])
                self._memory_store[key].append(current_time)
                
                # 清理过期的键（简单实现）
                for k in list(self._memory_store.keys()):
                    if all(ts < current_time - window_seconds for ts in self._memory_store[k]):
                        del self._memory_store[k]
            
            # 计算剩余请求数
            remaining = max(0, max_requests - current_count)
            
            # 计算重置时间
            reset_time = current_time + window_seconds
            
            # 检查是否超过限制
            if current_count >= max_requests:
                return {
                    "allowed": False,
                    "limit": max_requests,
                    "remaining": 0,
                    "reset": reset_time,
                    "retry_after": window_seconds,
                    "current": current_count,
                    "window": window_seconds,
                }
            else:
                return {
                    "allowed": True,
                    "limit": max_requests,
                    "remaining": remaining,
                    "reset": reset_time,
                    "retry_after": 0,
                    "current": current_count,
                    "window": window_seconds,
                }
                
        except Exception as e:
            logger.error(f"速率限制检查失败: {e}")
            # 出错时允许请求通过
            return {
                "allowed": True,
                "limit": 100,
                "remaining": 99,
                "reset": int(time.time()) + 60,
                "retry_after": 0,
                "current": 1,
                "window": 60,
                "error": str(e)
            }
    
    def limit(self, limit_str: str = "100 per minute", key_func=None):
        """
        速率限制装饰器
        
        Args:
            limit_str: 限制字符串，如 "100 per minute"
            key_func: 自定义键函数
            
        Returns:
            装饰器函数
        """
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    # 确定限制名称
                    limit_name = "default"
                    for name, pattern in self.default_limits.items():
                        if limit_str == pattern:
                            limit_name = name
                            break
                    
                    # 检查速率限制
                    result = self.check_rate_limit(limit_name)
                    
                    if not result["allowed"]:
                        from src.error import create_error_response, ErrorCode
                        
                        # 计算等待时间
                        wait_seconds = result["retry_after"]
                        
                        return create_error_response(
                            code=ErrorCode.RATE_LIMIT_EXCEEDED,
                            message=f"请求过于频繁，请等待{wait_seconds}秒后重试",
                            details={
                                "limit": result["limit"],
                                "remaining": result["remaining"],
                                "reset": result["reset"],
                                "retry_after": wait_seconds,
                                "window_seconds": result["window"]
                            },
                            http_status=429
                        )
                    
                    # 添加速率限制头部信息
                    from flask import make_response
                    response = make_response(f(*args, **kwargs))
                    
                    response.headers['X-RateLimit-Limit'] = str(result["limit"])
                    response.headers['X-RateLimit-Remaining'] = str(result["remaining"])
                    response.headers['X-RateLimit-Reset'] = str(result["reset"])
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"速率限制装饰器执行失败: {e}")
                    # 出错时允许请求通过
                    return f(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_rate_limit_info(self, limit_name: str = "default") -> Dict:
        """
        获取速率限制信息
        
        Args:
            limit_name: 限制名称
            
        Returns:
            限制信息字典
        """
        limit_str = self.default_limits.get(limit_name, self.default_limits["default"])
        max_requests, window_seconds = self.parse_limit_string(limit_str)
        
        return {
            "name": limit_name,
            "limit": limit_str,
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "description": self.get_limit_description(limit_name)
        }
    
    def get_limit_description(self, limit_name: str) -> str:
        """获取限制描述"""
        descriptions = {
            "default": "默认API限制",
            "auth": "认证相关接口限制（登录、注册等）",
            "funds": "基金数据查询接口限制",
            "holdings": "持仓管理接口限制",
            "quant": "量化分析接口限制",
            "import": "数据导入接口限制（OCR导入等）",
        }
        return descriptions.get(limit_name, "API接口限制")
    
    def get_all_limits(self) -> List[Dict]:
        """获取所有限制配置"""
        return [self.get_rate_limit_info(name) for name in self.default_limits.keys()]


# 全局速率限制器实例
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """获取速率限制器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def limit(limit_str: str = "100 per minute", key_func=None):
    """
    速率限制装饰器（简化版）
    
    Args:
        limit_str: 限制字符串
        key_func: 自定义键函数
        
    Returns:
        装饰器函数
    """
    return get_rate_limiter().limit(limit_str, key_func)


def check_rate_limit(limit_name: str = "default") -> Dict:
    """
    检查速率限制（直接调用）
    
    Args:
        limit_name: 限制名称
        
    Returns:
        限制状态字典
    """
    return get_rate_limiter().check_rate_limit(limit_name)


def get_rate_limit_info(limit_name: str = "default") -> Dict:
    """
    获取速率限制信息
    
    Args:
        limit_name: 限制名称
        
    Returns:
        限制信息字典
    """
    return get_rate_limiter().get_rate_limit_info(limit_name)


def get_all_limits() -> List[Dict]:
    """获取所有限制配置"""
    return get_rate_limiter().get_all_limits()


# 预定义的速率限制装饰器
def default_limit():
    """默认限制装饰器"""
    return limit("100 per minute")

def auth_limit():
    """认证接口限制装饰器"""
    return limit("10 per minute")

def funds_limit():
    """基金数据接口限制装饰器"""
    return limit("30 per minute")

def holdings_limit():
    """持仓接口限制装饰器"""
    return limit("20 per minute")

def quant_limit():
    """量化分析接口限制装饰器"""
    return limit("15 per minute")

def import_limit():
    """数据导入接口限制装饰器"""
    return limit("5 per minute")


# 错误码定义（添加到现有错误码中）
class RateLimitError(Exception):
    """速率限制错误"""
    pass


# 初始化函数
def init_rate_limiter(app):
    """
    初始化速率限制器
    
    Args:
        app: Flask应用实例
    """
    global _rate_limiter
    _rate_limiter = RateLimiter()
    
    # 添加速率限制信息端点
    @app.route("/rate-limit/info", methods=["GET"])
    def rate_limit_info():
        """获取速率限制配置信息"""
        try:
            limits = get_all_limits()
            current_ip = get_rate_limiter().get_client_ip()
            user_id = get_rate_limiter().get_user_id()
            
            # 检查当前限制状态
            current_status = {}
            for limit_info in limits:
                status = check_rate_limit(limit_info["name"])
                current_status[limit_info["name"]] = {
                    "allowed": status["allowed"],
                    "remaining": status["remaining"],
                    "reset": status["reset"],
                    "current": status["current"]
                }
            
            return {
                "success": True,
                "limits": limits,
                "current_status": current_status,
                "client_info": {
                    "ip": current_ip,
                    "user": user_id,
                    "timestamp": int(time.time())
                }
            }
            
        except Exception as e:
            logger.error(f"获取速率限制信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }, 500
    
    logger.info("速率限制器初始化完成")
    return _rate_limiter