"""
Rate Limiter Middleware for FastAPI
Reuses logic from Flask's rate_limiter.py
"""

import threading
import time
import logging
from typing import Dict, List, Tuple, Optional

import redis
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter based on Flask's RateLimiter"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or self._create_redis_client()
        self._memory_lock = threading.Lock()  # 保护内存存储的线程安全
        self.default_limits = {
            "default": "100 per minute",
            "auth": "10 per minute",
            "funds": "30 per minute",
            "holdings": "20 per minute",
            "quant": "15 per minute",
            "import": "5 per minute",
        }
        
    def _create_redis_client(self):
        """Create Redis client"""
        try:
            import os
            redis_host = os.getenv("FUND_DAILY_REDIS_HOST", "localhost")
            redis_port = int(os.getenv("FUND_DAILY_REDIS_PORT", "6379"))
            redis_db = int(os.getenv("FUND_DAILY_REDIS_DB", "0"))
            
            return redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        except Exception as e:
            logger.warning(f"Cannot connect to Redis, using memory storage: {e}")
            return None
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip = request.client.host if request.client else '127.0.0.1'
        
        if ip.startswith('::ffff:'):
            ip = ip[7:]
        return ip
    
    def parse_limit_string(self, limit_str: str) -> Tuple[int, int]:
        """Parse limit string like '100 per minute' -> (100, 60)"""
        try:
            parts = limit_str.lower().split()
            if len(parts) != 3 or parts[1] != "per":
                raise ValueError(f"Invalid limit format: {limit_str}")
            
            count = int(parts[0])
            unit = parts[2]
            
            unit_seconds = {
                "second": 1, "seconds": 1, "sec": 1,
                "minute": 60, "minutes": 60, "min": 60,
                "hour": 3600, "hours": 3600, "hr": 3600,
                "day": 86400, "days": 86400,
                "week": 604800, "weeks": 604800,
            }
            
            if unit not in unit_seconds:
                raise ValueError(f"Unknown time unit: {unit}")
            
            return count, unit_seconds[unit]
        except Exception as e:
            logger.error(f"Failed to parse limit string {limit_str}: {e}")
            return 100, 60
    
    def get_limit_key(self, request: Request, limit_name: str = "default") -> str:
        """Get rate limit key for request"""
        client_ip = self.get_client_ip(request)
        endpoint = request.url.path
        
        # Try to get user from session cookie
        user_id = request.cookies.get("session") or "anonymous"
        
        return f"rate_limit:{limit_name}:{user_id}:{endpoint}:{client_ip}"
    
    def check_rate_limit(self, request: Request, limit_name: str = "default") -> Dict:
        """Check rate limit for request"""
        try:
            limit_str = self.default_limits.get(limit_name, self.default_limits["default"])
            max_requests, window_seconds = self.parse_limit_string(limit_str)
            
            key = self.get_limit_key(request, limit_name)
            current_time = int(time.time())
            
            if self.redis_client:
                pipeline = self.redis_client.pipeline()
                pipeline.zremrangebyscore(key, 0, current_time - window_seconds)
                pipeline.zcard(key)
                pipeline.zadd(key, {str(current_time): current_time})
                pipeline.expire(key, window_seconds)
                results = pipeline.execute()
                current_count = results[1]
            else:
                # Memory storage for development (thread-safe)
                with self._memory_lock:
                    if not hasattr(self, '_memory_store'):
                        self._memory_store = {}
                    
                    if key not in self._memory_store:
                        self._memory_store[key] = []
                    
                    # 清理过期的记录
                    self._memory_store[key] = [
                        ts for ts in self._memory_store[key]
                        if ts > current_time - window_seconds
                    ]
                    
                    current_count = len(self._memory_store[key])
                    self._memory_store[key].append(current_time)
            
            remaining = max(0, max_requests - current_count)
            reset_time = current_time + window_seconds
            
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
            logger.error(f"Rate limit check failed: {e}")
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
    
    def get_rate_limit_info(self, limit_name: str = "default") -> Dict:
        """Get rate limit info for a limit type"""
        limit_str = self.default_limits.get(limit_name, self.default_limits["default"])
        max_requests, window_seconds = self.parse_limit_string(limit_str)
        
        descriptions = {
            "default": "默认API限制",
            "auth": "认证相关接口限制",
            "funds": "基金数据查询接口限制",
            "holdings": "持仓管理接口限制",
            "quant": "量化分析接口限制",
            "import": "数据导入接口限制",
        }
        
        return {
            "name": limit_name,
            "limit": limit_str,
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "description": descriptions.get(limit_name, "API接口限制")
        }


# Global rate limiter instance
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_rate_limit(request: Request, limit_name: str = "default") -> Dict:
    """Check rate limit for a request"""
    return get_rate_limiter().check_rate_limit(request, limit_name)


def get_all_limits() -> List[Dict]:
    """Get all rate limit configurations"""
    limiter = get_rate_limiter()
    return [limiter.get_rate_limit_info(name) for name in limiter.default_limits.keys()]
