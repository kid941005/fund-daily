"""API Gateway data models"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """微服务端点定义"""
    name: str
    path: str
    method: str = "GET"
    description: str = ""
    requires_auth: bool = False
    rate_limit: int = 100  # 每分钟请求数限制
    timeout: float = 5.0  # 超时时间（秒）

    def __str__(self):
        return f"{self.name}: {self.method} {self.path}"


class RateLimiter:
    """简单的速率限制器"""

    def __init__(self, cleanup_interval: int = 300, max_age: int = 3600):
        self._requests: Dict[str, List[float]] = {}
        self._cleanup_interval = cleanup_interval
        self._max_age = max_age
        self._last_cleanup = time.time()

    def _cleanup_expired(self):
        """清理过期的客户端记录"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        expired_clients = []
        for client_id, req_times in self._requests.items():
            valid_times = [
                req_time for req_time in req_times
                if current_time - req_time <= self._max_age
            ]
            if valid_times:
                self._requests[client_id] = valid_times
            else:
                expired_clients.append(client_id)

        for client_id in expired_clients:
            del self._requests[client_id]

        self._last_cleanup = current_time
        if expired_clients:
            logger.debug(f"RateLimiter: cleaned up {len(expired_clients)} expired clients")

    def check_limit(self, client_id: str, limit: int, window_seconds: int = 60) -> Tuple[bool, float]:
        """检查速率限制，返回 (是否允许, 剩余等待秒数)"""
        self._cleanup_expired()
        current_time = time.time()

        if client_id in self._requests:
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if current_time - req_time <= window_seconds
            ]
        else:
            self._requests[client_id] = []

        if len(self._requests[client_id]) < limit:
            self._requests[client_id].append(current_time)
            return True, 0.0
        else:
            oldest_request = min(self._requests[client_id])
            wait_time = oldest_request + window_seconds - current_time
            return False, max(0.0, wait_time)

    def reset(self, client_id: str = None):
        """重置速率限制"""
        if client_id is None:
            self._requests.clear()
        elif client_id in self._requests:
            del self._requests[client_id]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_clients": len(self._requests),
            "cleanup_interval": self._cleanup_interval,
            "max_age": self._max_age,
            "last_cleanup": self._last_cleanup
        }
