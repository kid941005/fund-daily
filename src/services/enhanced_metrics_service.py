"""
增强版性能监控服务
P2优化：性能监控增强
"""

import time
import threading
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Tuple
import logging

from .metrics_service import MetricsService

logger = logging.getLogger(__name__)


class EnhancedMetricsService(MetricsService):
    """
    增强版性能监控服务

    新增功能：
    1. 历史数据存储（滑动窗口）
    2. 性能告警机制
    3. 趋势分析
    4. 资源使用监控
    """

    def __init__(self, redis_client=None, history_window_minutes: int = 60):
        """
        初始化增强版性能监控服务

        Args:
            redis_client: Redis客户端（可选）
            history_window_minutes: 历史数据窗口（分钟）
        """
        super().__init__(redis_client)

        # 历史数据存储（滑动窗口）
        self.history_window = history_window_minutes * 60  # 转换为秒
        self._history = {
            "requests": deque(maxlen=1000),
            "cache": deque(maxlen=1000),
            "external_api": deque(maxlen=1000),
            "database": deque(maxlen=1000),
            "errors": deque(maxlen=1000),
        }

        # 告警配置
        self._alerts = {
            "high_error_rate": {
                "enabled": True,
                "threshold": 0.1,  # 10%错误率
                "window_minutes": 5,
                "cooldown_minutes": 15,
                "last_triggered": 0,
            },
            "slow_response": {
                "enabled": True,
                "threshold": 2.0,  # 2秒
                "window_minutes": 5,
                "cooldown_minutes": 10,
                "last_triggered": 0,
            },
            "cache_miss_rate": {
                "enabled": True,
                "threshold": 0.5,  # 50%缓存未命中率
                "window_minutes": 5,
                "cooldown_minutes": 30,
                "last_triggered": 0,
            },
        }

        # 资源使用监控
        self._resource_metrics = {
            "memory_usage": deque(maxlen=100),
            "cpu_usage": deque(maxlen=100),
            "active_threads": deque(maxlen=100),
        }

        logger.info(f"EnhancedMetricsService initialized (history: {history_window_minutes} minutes)")

    def record_request(self, method: str, path: str, status_code: int, duration: float):
        """记录API请求指标（增强版）"""
        super().record_request(method, path, status_code, duration)

        # 记录历史数据
        timestamp = time.time()
        request_data = {
            "timestamp": timestamp,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration": duration,
            "is_error": status_code >= 400,
        }

        with self._lock:
            self._history["requests"].append(request_data)

        # 检查告警
        self._check_alerts()

    def record_cache_operation(self, operation: str, cache_key: str, hit: bool, duration: float = 0.0):
        """记录缓存操作（增强版）"""
        super().record_cache_operation(operation, cache_key, hit, duration)

        # 记录历史数据
        timestamp = time.time()
        cache_data = {
            "timestamp": timestamp,
            "operation": operation,
            "cache_key": cache_key[:50],  # 截断长键
            "hit": hit,
            "duration": duration,
        }

        with self._lock:
            self._history["cache"].append(cache_data)

    def record_external_api_call(self, service: str, endpoint: str, duration: float, success: bool):
        """记录外部API调用（增强版）"""
        super().record_external_api_call(service, endpoint, duration, success)

        # 记录历史数据
        timestamp = time.time()
        api_data = {
            "timestamp": timestamp,
            "service": service,
            "endpoint": endpoint,
            "duration": duration,
            "success": success,
        }

        with self._lock:
            self._history["external_api"].append(api_data)

    def record_database_query(self, query_type: str, duration: float):
        """记录数据库查询（增强版）"""
        super().record_database_query(query_type, duration)

        # 记录历史数据
        timestamp = time.time()
        db_data = {"timestamp": timestamp, "query_type": query_type, "duration": duration}

        with self._lock:
            self._history["database"].append(db_data)

    def record_error(self, error_type: str, message: str, context: Dict[str, Any] = None):
        """记录错误（新增）"""
        timestamp = time.time()
        error_data = {"timestamp": timestamp, "error_type": error_type, "message": message, "context": context or {}}

        with self._lock:
            self._history["errors"].append(error_data)

        logger.warning(f"Error recorded: {error_type} - {message}")

    def record_resource_usage(self, memory_mb: float, cpu_percent: float, active_threads: int):
        """记录资源使用情况（新增）"""
        timestamp = time.time()
        resource_data = {
            "timestamp": timestamp,
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "active_threads": active_threads,
        }

        with self._lock:
            self._resource_metrics["memory_usage"].append((timestamp, memory_mb))
            self._resource_metrics["cpu_usage"].append((timestamp, cpu_percent))
            self._resource_metrics["active_threads"].append((timestamp, active_threads))

    def _check_alerts(self):
        """检查告警条件"""
        current_time = time.time()

        for alert_name, alert_config in self._alerts.items():
            if not alert_config["enabled"]:
                continue

            # 检查冷却时间
            if current_time - alert_config["last_triggered"] < alert_config["cooldown_minutes"] * 60:
                continue

            # 检查告警条件
            should_trigger = False
            message = ""

            if alert_name == "high_error_rate":
                should_trigger, message = self._check_error_rate_alert(alert_config)
            elif alert_name == "slow_response":
                should_trigger, message = self._check_slow_response_alert(alert_config)
            elif alert_name == "cache_miss_rate":
                should_trigger, message = self._check_cache_miss_alert(alert_config)

            if should_trigger:
                alert_config["last_triggered"] = current_time
                self._trigger_alert(alert_name, message)

    def _check_error_rate_alert(self, alert_config: Dict[str, Any]) -> Tuple[bool, str]:
        """检查错误率告警"""
        window_seconds = alert_config["window_minutes"] * 60
        threshold = alert_config["threshold"]
        current_time = time.time()

        with self._lock:
            # 获取窗口内的请求
            recent_requests = [r for r in self._history["requests"] if current_time - r["timestamp"] <= window_seconds]

            if not recent_requests:
                return False, ""

            # 计算错误率
            total_requests = len(recent_requests)
            error_requests = len([r for r in recent_requests if r["is_error"]])
            error_rate = error_requests / total_requests if total_requests > 0 else 0

            if error_rate > threshold:
                return True, f"错误率过高: {error_rate:.1%} (阈值: {threshold:.1%})"

        return False, ""

    def _check_slow_response_alert(self, alert_config: Dict[str, Any]) -> Tuple[bool, str]:
        """检查慢响应告警"""
        window_seconds = alert_config["window_minutes"] * 60
        threshold = alert_config["threshold"]
        current_time = time.time()

        with self._lock:
            # 获取窗口内的请求
            recent_requests = [r for r in self._history["requests"] if current_time - r["timestamp"] <= window_seconds]

            if not recent_requests:
                return False, ""

            # 计算平均响应时间
            total_duration = sum(r["duration"] for r in recent_requests)
            avg_duration = total_duration / len(recent_requests)

            if avg_duration > threshold:
                return True, f"平均响应时间过长: {avg_duration:.2f}s (阈值: {threshold}s)"

        return False, ""

    def _check_cache_miss_alert(self, alert_config: Dict[str, Any]) -> Tuple[bool, str]:
        """检查缓存未命中告警"""
        window_seconds = alert_config["window_minutes"] * 60
        threshold = alert_config["threshold"]
        current_time = time.time()

        with self._lock:
            # 获取窗口内的缓存操作
            recent_cache_ops = [c for c in self._history["cache"] if current_time - c["timestamp"] <= window_seconds]

            if not recent_cache_ops:
                return False, ""

            # 计算缓存未命中率
            total_ops = len(recent_cache_ops)
            miss_ops = len([c for c in recent_cache_ops if not c["hit"]])
            miss_rate = miss_ops / total_ops if total_ops > 0 else 0

            if miss_rate > threshold:
                return True, f"缓存未命中率过高: {miss_rate:.1%} (阈值: {threshold:.1%})"

        return False, ""

    def _trigger_alert(self, alert_name: str, message: str):
        """触发告警"""
        alert_data = {"timestamp": time.time(), "alert_name": alert_name, "message": message, "severity": "warning"}

        # 记录告警
        with self._lock:
            if "alerts" not in self._history:
                self._history["alerts"] = deque(maxlen=100)
            self._history["alerts"].append(alert_data)

        # 记录日志（实际项目中可以发送邮件、短信等）
        logger.warning(f"🚨 性能告警: {alert_name} - {message}")

        # 这里可以添加告警通知逻辑（邮件、Slack、Webhook等）

    def get_enhanced_metrics(self) -> Dict[str, Any]:
        """获取增强版性能指标"""
        base_metrics = super().get_metrics_summary()

        with self._lock:
            # 计算历史统计数据
            current_time = time.time()

            # 最近5分钟的数据
            recent_window = 5 * 60  # 5分钟

            recent_requests = [r for r in self._history["requests"] if current_time - r["timestamp"] <= recent_window]

            recent_cache_ops = [c for c in self._history["cache"] if current_time - c["timestamp"] <= recent_window]

            # 计算趋势
            request_trend = self._calculate_trend(self._history["requests"], "duration")
            cache_trend = self._calculate_trend(self._history["cache"], "hit", is_boolean=True)

            # 资源使用
            resource_stats = {}
            for resource_name, data in self._resource_metrics.items():
                if data:
                    timestamps, values = zip(*data)
                    recent_data = [v for t, v in zip(timestamps, values) if current_time - t <= recent_window]
                    if recent_data:
                        resource_stats[resource_name] = {
                            "current": values[-1] if values else 0,
                            "avg": sum(recent_data) / len(recent_data) if recent_data else 0,
                            "max": max(recent_data) if recent_data else 0,
                            "min": min(recent_data) if recent_data else 0,
                        }

        enhanced_metrics = {
            **base_metrics,
            "history": {
                "requests_last_5min": len(recent_requests),
                "cache_ops_last_5min": len(recent_cache_ops),
                "request_trend": request_trend,
                "cache_trend": cache_trend,
            },
            "resources": resource_stats,
            "alerts": {
                "active_alerts": len(self._history.get("alerts", [])),
                "config": {
                    name: {"enabled": config["enabled"], "threshold": config["threshold"]}
                    for name, config in self._alerts.items()
                },
            },
        }

        return enhanced_metrics

    def _calculate_trend(self, data: deque, field: str, is_boolean: bool = False) -> str:
        """计算趋势（上升/下降/稳定）"""
        if len(data) < 10:
            return "insufficient_data"

        # 分成两半比较
        half = len(data) // 2
        first_half = list(data)[:half]
        second_half = list(data)[half:]

        if is_boolean:
            # 布尔值趋势（如缓存命中率）
            first_avg = sum(1 for d in first_half if d.get(field, False)) / len(first_half) if first_half else 0
            second_avg = sum(1 for d in second_half if d.get(field, False)) / len(second_half) if second_half else 0
        else:
            # 数值趋势
            first_avg = sum(d.get(field, 0) for d in first_half) / len(first_half) if first_half else 0
            second_avg = sum(d.get(field, 0) for d in second_half) / len(second_half) if second_half else 0

        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"

    def reset_history(self):
        """重置历史数据"""
        with self._lock:
            for key in self._history:
                self._history[key].clear()

            for key in self._resource_metrics:
                self._resource_metrics[key].clear()

            # 重置告警触发时间
            for alert_config in self._alerts.values():
                alert_config["last_triggered"] = 0

        logger.info("Enhanced metrics history reset")


# 全局单例实例
_enhanced_metrics_instance = None


def get_enhanced_metrics_service(redis_client=None) -> EnhancedMetricsService:
    """获取增强版性能监控服务实例（单例模式）"""
    global _enhanced_metrics_instance
    if _enhanced_metrics_instance is None:
        _enhanced_metrics_instance = EnhancedMetricsService(redis_client=redis_client, history_window_minutes=60)
        logger.info("EnhancedMetricsService initialized")
    return _enhanced_metrics_instance
