"""
性能监控服务
收集和存储系统性能指标
"""

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class MetricsService:
    """性能监控服务"""

    def __init__(self, redis_client=None):
        """
        初始化性能监控服务

        Args:
            redis_client: Redis客户端（可选），如果提供则使用Redis存储指标
        """
        self.redis_client = redis_client
        self.use_redis = redis_client is not None

        # 内存中的性能指标（如果不用Redis）
        self._metrics = {
            "requests": defaultdict(lambda: {"count": 0, "total_time": 0.0, "errors": 0}),
            "cache": defaultdict(lambda: {"hits": 0, "misses": 0}),
            "external_api": defaultdict(lambda: {"calls": 0, "total_time": 0.0, "errors": 0}),
            "database": defaultdict(lambda: {"queries": 0, "total_time": 0.0}),
        }

        # 锁用于线程安全
        self._lock = threading.RLock()

        # 清理过期数据的时间戳
        self._last_cleanup = time.time()

        logger.info("MetricsService initialized")

    def record_request(self, method: str, path: str, status_code: int, duration: float):
        """
        记录API请求指标

        Args:
            method: HTTP方法 (GET, POST, etc.)
            path: 请求路径
            status_code: HTTP状态码
            duration: 请求处理时间（秒）
        """
        with self._lock:
            key = f"{method} {path}"
            metric = self._metrics["requests"][key]
            metric["count"] += 1
            metric["total_time"] += duration

            if status_code >= 400:
                metric["errors"] += 1

            # 更新最近时间戳
            metric["last_request"] = datetime.now().isoformat()

    def record_cache_hit(self, cache_key: str, hit: bool = True):
        """
        记录缓存命中/未命中

        Args:
            cache_key: 缓存键（或类别）
            hit: 是否命中
        """
        with self._lock:
            metric = self._metrics["cache"][cache_key]
            if hit:
                metric["hits"] += 1
            else:
                metric["misses"] += 1

    def record_external_api_call(self, api_name: str, duration: float, success: bool = True):
        """
        记录外部API调用

        Args:
            api_name: API名称（如"天天基金", "东方财富"）
            duration: 调用耗时（秒）
            success: 是否成功
        """
        with self._lock:
            metric = self._metrics["external_api"][api_name]
            metric["calls"] += 1
            metric["total_time"] += duration

            if not success:
                metric["errors"] += 1

            # 更新最近时间戳
            metric["last_call"] = datetime.now().isoformat()

    def record_database_query(self, query_type: str, duration: float):
        """
        记录数据库查询

        Args:
            query_type: 查询类型（如"SELECT", "INSERT", "UPDATE"）
            duration: 查询耗时（秒）
        """
        with self._lock:
            metric = self._metrics["database"][query_type]
            metric["queries"] += 1
            metric["total_time"] += duration

    def get_metrics_summary(self, reset: bool = False) -> dict[str, Any]:
        """
        获取性能指标摘要

        Args:
            reset: 是否重置指标计数器（用于定期报告）

        Returns:
            性能指标摘要字典
        """
        with self._lock:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "requests": {},
                "cache": {},
                "external_api": {},
                "database": {},
            }

            # 计算请求指标
            total_requests = 0
            total_request_time = 0.0
            total_errors = 0

            for key, metric in self._metrics["requests"].items():
                count = metric["count"]
                total_time = metric["total_time"]
                errors = metric["errors"]

                summary["requests"][key] = {
                    "count": count,
                    "avg_time": total_time / count if count > 0 else 0,
                    "error_rate": errors / count if count > 0 else 0,
                    "last_request": metric.get("last_request"),
                }

                total_requests += count
                total_request_time += total_time
                total_errors += errors

            summary["requests"]["_total"] = {
                "count": total_requests,
                "avg_time": total_request_time / total_requests if total_requests > 0 else 0,
                "error_rate": total_errors / total_requests if total_requests > 0 else 0,
            }

            # 计算缓存指标
            total_hits = 0
            total_misses = 0

            for key, metric in self._metrics["cache"].items():
                hits = metric["hits"]
                misses = metric["misses"]
                total = hits + misses

                summary["cache"][key] = {
                    "hits": hits,
                    "misses": misses,
                    "hit_rate": hits / total if total > 0 else 0,
                }

                total_hits += hits
                total_misses += misses

            total_cache_access = total_hits + total_misses
            summary["cache"]["_total"] = {
                "hits": total_hits,
                "misses": total_misses,
                "hit_rate": total_hits / total_cache_access if total_cache_access > 0 else 0,
            }

            # 计算外部API指标
            total_api_calls = 0
            total_api_time = 0.0
            total_api_errors = 0

            for key, metric in self._metrics["external_api"].items():
                calls = metric["calls"]
                total_time = metric["total_time"]
                errors = metric["errors"]

                summary["external_api"][key] = {
                    "calls": calls,
                    "avg_time": total_time / calls if calls > 0 else 0,
                    "error_rate": errors / calls if calls > 0 else 0,
                    "last_call": metric.get("last_call"),
                }

                total_api_calls += calls
                total_api_time += total_time
                total_api_errors += errors

            summary["external_api"]["_total"] = {
                "calls": total_api_calls,
                "avg_time": total_api_time / total_api_calls if total_api_calls > 0 else 0,
                "error_rate": total_api_errors / total_api_calls if total_api_calls > 0 else 0,
            }

            # 计算数据库指标
            total_queries = 0
            total_query_time = 0.0

            for key, metric in self._metrics["database"].items():
                queries = metric["queries"]
                total_time = metric["total_time"]

                summary["database"][key] = {
                    "queries": queries,
                    "avg_time": total_time / queries if queries > 0 else 0,
                }

                total_queries += queries
                total_query_time += total_time

            summary["database"]["_total"] = {
                "queries": total_queries,
                "avg_time": total_query_time / total_queries if total_queries > 0 else 0,
            }

            # 如果要求重置，则清空指标
            if reset:
                self._reset_metrics()

            return summary

    def _reset_metrics(self):
        """重置所有指标计数器"""
        with self._lock:
            self._metrics = {
                "requests": defaultdict(lambda: {"count": 0, "total_time": 0.0, "errors": 0}),
                "cache": defaultdict(lambda: {"hits": 0, "misses": 0}),
                "external_api": defaultdict(lambda: {"calls": 0, "total_time": 0.0, "errors": 0}),
                "database": defaultdict(lambda: {"queries": 0, "total_time": 0.0}),
            }

    def get_current_metrics(self) -> dict[str, Any]:
        """获取当前指标（不清零）"""
        return self.get_metrics_summary(reset=False)


# 全局性能监控服务实例
_metrics_service_instance = None


def get_metrics_service() -> MetricsService:
    """
    获取全局性能监控服务实例（单例模式）

    Returns:
        MetricsService实例
    """
    global _metrics_service_instance

    if _metrics_service_instance is None:
        # 尝试使用Redis（如果可用）
        redis_client = None
        try:
            from src.cache.redis_cache import get_redis_client

            redis_client = get_redis_client()
            logger.info("MetricsService using Redis for storage")
        except Exception as e:
            logger.info(f"MetricsService using in-memory storage (Redis not available: {e})")

        _metrics_service_instance = MetricsService(redis_client=redis_client)

    return _metrics_service_instance


# 便捷装饰器，用于记录函数执行时间
def timed_metric(metric_type: str = "external_api", name: str = None):
    """
    装饰器：记录函数执行时间作为性能指标

    Args:
        metric_type: 指标类型（"external_api", "database", "cache"等）
        name: 指标名称，如果为None则使用函数名
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            service = get_metrics_service()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                metric_name = name or func.__name__

                if metric_type == "external_api":
                    service.record_external_api_call(metric_name, duration, success)
                elif metric_type == "database":
                    service.record_database_query(metric_name, duration)
                # 其他类型可以根据需要扩展

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
