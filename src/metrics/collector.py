"""
Prometheus Metrics Collectors
"""

import time
from functools import wraps
from typing import Callable

# Lazy import to avoid hard dependency
_metrics = None


def get_metrics():
    """Get or create metrics instance"""
    global _metrics
    if _metrics is None:
        try:
            from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram

            _metrics = {
                "registry": REGISTRY,
                "request_counter": Counter(
                    "fund_daily_requests_total", "Total requests", ["method", "endpoint", "status"]
                ),
                "request_latency": Histogram(
                    "fund_daily_request_duration_seconds", "Request latency", ["method", "endpoint"]
                ),
                "cache_hits": Counter("fund_daily_cache_hits_total", "Cache hits", ["cache_type"]),
                "score_calculations": Counter(
                    "fund_daily_score_calculations_total", "Score calculations", ["fund_code"]
                ),
            }
        except ImportError:
            return None
    return _metrics


def track_request(method: str, endpoint: str):
    """Track a request"""
    metrics = get_metrics()
    if metrics:
        metrics["request_counter"].labels(method=method, endpoint=endpoint, status="success").inc()


def track_latency(method: str, endpoint: str, duration: float):
    """Track request latency"""
    metrics = get_metrics()
    if metrics:
        metrics["request_latency"].labels(method=method, endpoint=endpoint).observe(duration)


def track_cache_hit(cache_type: str):
    """Track cache hit"""
    metrics = get_metrics()
    if metrics:
        metrics["cache_hits"].labels(cache_type=cache_type).inc()


def track_score_calculation(fund_code: str):
    """Track score calculation"""
    metrics = get_metrics()
    if metrics:
        metrics["score_calculations"].labels(fund_code=fund_code).inc()


def timed(metric_name: str = "default"):
    """Decorator to time a function"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                metrics = get_metrics()
                if metrics and "request_latency" in metrics:
                    metrics["request_latency"].labels(method="INTERNAL", endpoint=metric_name).observe(duration)

        return wrapper

    return decorator
