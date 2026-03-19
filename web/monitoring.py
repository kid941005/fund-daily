"""
监控和指标收集模块
基于Prometheus标准，提供应用性能监控和业务指标
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# 检查是否安装了Prometheus客户端
try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary,
        generate_latest, CONTENT_TYPE_LATEST,
        REGISTRY
    )
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    logger.warning("Prometheus客户端未安装，监控功能受限")


@dataclass
class MetricLabels:
    """指标标签"""
    endpoint: str = ""
    method: str = ""
    status_code: str = ""
    error_type: str = ""
    cache_type: str = ""
    fund_code: str = ""
    user_id: str = ""


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, app_name: str = "fund_daily"):
        self.app_name = app_name
        self._metrics: Dict[str, Any] = {}
        self._init_metrics()
    
    def _init_metrics(self):
        """初始化指标"""
        if not HAS_PROMETHEUS:
            # 使用简单计数器和仪表
            self._metrics = {
                'http_requests_total': {'count': 0, 'labels': {}},
                'http_request_duration_seconds': {'count': 0, 'sum': 0.0},
                'http_errors_total': {'count': 0, 'labels': {}},
                'cache_hits_total': {'count': 0, 'labels': {}},
                'cache_misses_total': {'count': 0, 'labels': {}},
                'database_queries_total': {'count': 0, 'labels': {}},
                'database_query_duration_seconds': {'count': 0, 'sum': 0.0},
                'fund_data_fetches_total': {'count': 0, 'labels': {}},
                'fund_data_fetch_errors_total': {'count': 0, 'labels': {}},
                'scoring_calculations_total': {'count': 0, 'labels': {}},
                'active_users': {'value': 0},
                'memory_usage_bytes': {'value': 0},
                'cpu_usage_percent': {'value': 0.0},
            }
            return
        
        # Prometheus指标
        self._metrics = {
            # HTTP请求指标
            'http_requests_total': Counter(
                f'{self.app_name}_http_requests_total',
                'HTTP请求总数',
                ['method', 'endpoint', 'status_code']
            ),
            'http_request_duration_seconds': Histogram(
                f'{self.app_name}_http_request_duration_seconds',
                'HTTP请求耗时（秒）',
                ['method', 'endpoint'],
                buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
            ),
            'http_errors_total': Counter(
                f'{self.app_name}_http_errors_total',
                'HTTP错误总数',
                ['method', 'endpoint', 'error_type']
            ),
            
            # 缓存指标
            'cache_hits_total': Counter(
                f'{self.app_name}_cache_hits_total',
                '缓存命中总数',
                ['cache_type']
            ),
            'cache_misses_total': Counter(
                f'{self.app_name}_cache_misses_total',
                '缓存未命中总数',
                ['cache_type']
            ),
            'cache_size': Gauge(
                f'{self.app_name}_cache_size',
                '缓存大小',
                ['cache_type']
            ),
            
            # 数据库指标
            'database_queries_total': Counter(
                f'{self.app_name}_database_queries_total',
                '数据库查询总数',
                ['query_type']
            ),
            'database_query_duration_seconds': Histogram(
                f'{self.app_name}_database_query_duration_seconds',
                '数据库查询耗时（秒）',
                ['query_type'],
                buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
            ),
            'database_connections': Gauge(
                f'{self.app_name}_database_connections',
                '数据库连接数'
            ),
            
            # 业务指标
            'fund_data_fetches_total': Counter(
                f'{self.app_name}_fund_data_fetches_total',
                '基金数据获取总数',
                ['fund_code', 'status']
            ),
            'fund_data_fetch_errors_total': Counter(
                f'{self.app_name}_fund_data_fetch_errors_total',
                '基金数据获取错误总数',
                ['fund_code', 'error_type']
            ),
            'scoring_calculations_total': Counter(
                f'{self.app_name}_scoring_calculations_total',
                '评分计算总数',
                ['fund_code']
            ),
            'portfolio_analyses_total': Counter(
                f'{self.app_name}_portfolio_analyses_total',
                '投资组合分析总数'
            ),
            
            # 系统指标
            'active_users': Gauge(
                f'{self.app_name}_active_users',
                '活跃用户数'
            ),
            'memory_usage_bytes': Gauge(
                f'{self.app_name}_memory_usage_bytes',
                '内存使用量（字节）'
            ),
            'cpu_usage_percent': Gauge(
                f'{self.app_name}_cpu_usage_percent',
                'CPU使用率（百分比）'
            ),
            'uptime_seconds': Gauge(
                f'{self.app_name}_uptime_seconds',
                '应用运行时间（秒）'
            ),
        }
        
        # 初始化运行时间
        self.start_time = time.time()
        self._metrics['uptime_seconds'].set_function(
            lambda: time.time() - self.start_time
        )
    
    def record_http_request(self, method: str, endpoint: str, 
                           status_code: int, duration: float):
        """记录HTTP请求"""
        labels = MetricLabels(
            endpoint=endpoint,
            method=method,
            status_code=str(status_code)
        )
        
        if HAS_PROMETHEUS:
            self._metrics['http_requests_total'].labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            
            self._metrics['http_request_duration_seconds'].labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        else:
            key = f"{method}:{endpoint}:{status_code}"
            self._metrics['http_requests_total']['count'] += 1
            if key not in self._metrics['http_requests_total']['labels']:
                self._metrics['http_requests_total']['labels'][key] = 0
            self._metrics['http_requests_total']['labels'][key] += 1
            
            self._metrics['http_request_duration_seconds']['count'] += 1
            self._metrics['http_request_duration_seconds']['sum'] += duration
    
    def record_http_error(self, method: str, endpoint: str, 
                         error_type: str):
        """记录HTTP错误"""
        if HAS_PROMETHEUS:
            self._metrics['http_errors_total'].labels(
                method=method,
                endpoint=endpoint,
                error_type=error_type
            ).inc()
        else:
            key = f"{method}:{endpoint}:{error_type}"
            self._metrics['http_errors_total']['count'] += 1
            if key not in self._metrics['http_errors_total']['labels']:
                self._metrics['http_errors_total']['labels'][key] = 0
            self._metrics['http_errors_total']['labels'][key] += 1
    
    def record_cache_hit(self, cache_type: str = "memory"):
        """记录缓存命中"""
        if HAS_PROMETHEUS:
            self._metrics['cache_hits_total'].labels(
                cache_type=cache_type
            ).inc()
        else:
            self._metrics['cache_hits_total']['count'] += 1
            if cache_type not in self._metrics['cache_hits_total']['labels']:
                self._metrics['cache_hits_total']['labels'][cache_type] = 0
            self._metrics['cache_hits_total']['labels'][cache_type] += 1
    
    def record_cache_miss(self, cache_type: str = "memory"):
        """记录缓存未命中"""
        if HAS_PROMETHEUS:
            self._metrics['cache_misses_total'].labels(
                cache_type=cache_type
            ).inc()
        else:
            self._metrics['cache_misses_total']['count'] += 1
            if cache_type not in self._metrics['cache_misses_total']['labels']:
                self._metrics['cache_misses_total']['labels'][cache_type] = 0
            self._metrics['cache_misses_total']['labels'][cache_type] += 1
    
    def record_database_query(self, query_type: str, duration: float):
        """记录数据库查询"""
        if HAS_PROMETHEUS:
            self._metrics['database_queries_total'].labels(
                query_type=query_type
            ).inc()
            
            self._metrics['database_query_duration_seconds'].labels(
                query_type=query_type
            ).observe(duration)
        else:
            self._metrics['database_queries_total']['count'] += 1
            if query_type not in self._metrics['database_queries_total']['labels']:
                self._metrics['database_queries_total']['labels'][query_type] = 0
            self._metrics['database_queries_total']['labels'][query_type] += 1
            
            self._metrics['database_query_duration_seconds']['count'] += 1
            self._metrics['database_query_duration_seconds']['sum'] += duration
    
    def record_fund_data_fetch(self, fund_code: str, success: bool = True):
        """记录基金数据获取"""
        status = "success" if success else "error"
        
        if HAS_PROMETHEUS:
            self._metrics['fund_data_fetches_total'].labels(
                fund_code=fund_code,
                status=status
            ).inc()
            
            if not success:
                self._metrics['fund_data_fetch_errors_total'].labels(
                    fund_code=fund_code,
                    error_type="fetch_error"
                ).inc()
        else:
            key = f"{fund_code}:{status}"
            self._metrics['fund_data_fetches_total']['count'] += 1
            if key not in self._metrics['fund_data_fetches_total']['labels']:
                self._metrics['fund_data_fetches_total']['labels'][key] = 0
            self._metrics['fund_data_fetches_total']['labels'][key] += 1
    
    def record_scoring_calculation(self, fund_code: str = ""):
        """记录评分计算"""
        if HAS_PROMETHEUS:
            self._metrics['scoring_calculations_total'].labels(
                fund_code=fund_code
            ).inc()
        else:
            self._metrics['scoring_calculations_total']['count'] += 1
            if fund_code not in self._metrics['scoring_calculations_total']['labels']:
                self._metrics['scoring_calculations_total']['labels'][fund_code] = 0
            self._metrics['scoring_calculations_total']['labels'][fund_code] += 1
    
    def set_active_users(self, count: int):
        """设置活跃用户数"""
        if HAS_PROMETHEUS:
            self._metrics['active_users'].set(count)
        else:
            self._metrics['active_users']['value'] = count
    
    def set_memory_usage(self, bytes_used: int):
        """设置内存使用量"""
        if HAS_PROMETHEUS:
            self._metrics['memory_usage_bytes'].set(bytes_used)
        else:
            self._metrics['memory_usage_bytes']['value'] = bytes_used
    
    def set_cpu_usage(self, percent: float):
        """设置CPU使用率"""
        if HAS_PROMETHEUS:
            self._metrics['cpu_usage_percent'].set(percent)
        else:
            self._metrics['cpu_usage_percent']['value'] = percent
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取当前指标值"""
        if HAS_PROMETHEUS:
            # Prometheus会自动处理
            return {}
        
        # 返回简单指标
        result = {}
        for name, data in self._metrics.items():
            if 'count' in data:
                result[name] = {
                    'count': data['count'],
                    'labels': data.get('labels', {})
                }
            elif 'value' in data:
                result[name] = data['value']
            elif 'sum' in data:
                result[name] = {
                    'count': data['count'],
                    'sum': data['sum'],
                    'avg': data['sum'] / data['count'] if data['count'] > 0 else 0
                }
        
        # 添加缓存命中率
        hits = self._metrics['cache_hits_total']['count']
        misses = self._metrics['cache_misses_total']['count']
        total = hits + misses
        if total > 0:
            result['cache_hit_rate'] = hits / total
        else:
            result['cache_hit_rate'] = 0
        
        # 添加平均HTTP响应时间
        http_count = self._metrics['http_request_duration_seconds']['count']
        http_sum = self._metrics['http_request_duration_seconds']['sum']
        if http_count > 0:
            result['http_avg_duration_seconds'] = http_sum / http_count
        else:
            result['http_avg_duration_seconds'] = 0
        
        return result
    
    def get_prometheus_metrics(self) -> Optional[bytes]:
        """获取Prometheus格式的指标（如果可用）"""
        if HAS_PROMETHEUS:
            return generate_latest()
        return None


# 单例实例
_metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        logger.info("指标收集器初始化完成")
    return _metrics_collector


# 监控装饰器
def monitor_request(endpoint: str = ""):
    """
    HTTP请求监控装饰器
    
    Args:
        endpoint: 端点名称（如果不指定，使用函数名）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            collector = get_metrics_collector()
            
            # 从Flask请求上下文获取信息
            try:
                from flask import request
                method = request.method
                ep = endpoint or request.endpoint or func.__name__
            except:
                method = "UNKNOWN"
                ep = endpoint or func.__name__
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功请求
                duration = time.time() - start_time
                status_code = 200  # 假设成功
                
                # 尝试从结果获取状态码
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                elif isinstance(result, tuple) and len(result) > 1:
                    status_code = result[1]
                
                collector.record_http_request(method, ep, status_code, duration)
                return result
                
            except Exception as e:
                # 记录错误
                duration = time.time() - start_time
                error_type = type(e).__name__
                
                # 记录错误请求（状态码500）
                collector.record_http_request(method, ep, 500, duration)
                collector.record_http_error(method, ep, error_type)
                raise
        
        return wrapper
    return decorator


def monitor_cache(cache_type: str = "memory"):
    """
    缓存监控装饰器
    
    Args:
        cache_type: 缓存类型（memory/redis）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            
            # 检查是否是get操作
            func_name = func.__name__.lower()
            is_get = any(keyword in func_name for keyword in ['get', 'fetch', 'load'])
            
            result = func(*args, **kwargs)
            
            if is_get:
                if result is None:
                    collector.record_cache_miss(cache_type)
                else:
                    collector.record_cache_hit(cache_type)
            
            return result
        
        return wrapper
    return decorator


def monitor_database(query_type: str = "generic"):
    """
    数据库操作监控装饰器
    
    Args:
        query_type: 查询类型（select/insert/update/delete）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            collector = get_metrics_collector()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                collector.record_database_query(query_type, duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                collector.record_database_query(f"{query_type}_error", duration)
                raise
        
        return wrapper
    return decorator