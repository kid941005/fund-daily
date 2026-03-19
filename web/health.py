"""
增强版健康检查模块
提供应用、数据库、缓存、外部依赖的健康状态检查
"""

import time
import logging
import psutil
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus:
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """健康检查基类"""
    
    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical
    
    def check(self) -> Dict[str, Any]:
        """执行健康检查"""
        raise NotImplementedError


class ApplicationHealthCheck(HealthCheck):
    """应用健康检查"""
    
    def __init__(self):
        super().__init__("application", critical=True)
        self.start_time = time.time()
    
    def check(self) -> Dict[str, Any]:
        """检查应用状态"""
        try:
            # 检查内存使用
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # 检查线程数
            thread_count = process.num_threads()
            
            # 检查CPU使用率
            cpu_percent = process.cpu_percent(interval=0.1)
            
            uptime = time.time() - self.start_time
            
            return {
                "status": HealthStatus.HEALTHY,
                "details": {
                    "uptime_seconds": uptime,
                    "memory_rss_bytes": memory_info.rss,
                    "memory_vms_bytes": memory_info.vms,
                    "thread_count": thread_count,
                    "cpu_percent": cpu_percent,
                    "pid": process.pid,
                }
            }
        except Exception as e:
            logger.error(f"应用健康检查失败: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "details": {"error": str(e)}
            }


class DatabaseHealthCheck(HealthCheck):
    """数据库健康检查"""
    
    def __init__(self):
        super().__init__("database", critical=True)
    
    def check(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            from db import database_pg as db
            
            start_time = time.time()
            
            # 测试连接
            with db.get_db() as conn:
                with db.get_cursor(conn) as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
            
            latency = time.time() - start_time
            
            if result and result[0] == 1:
                return {
                    "status": HealthStatus.HEALTHY,
                    "details": {
                        "latency_seconds": latency,
                        "test_query": "SELECT 1"
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "details": {
                        "error": f"数据库查询返回异常结果: {result}",
                        "latency_seconds": latency
                    }
                }
                
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "details": {"error": str(e)}
            }


class RedisHealthCheck(HealthCheck):
    """Redis健康检查"""
    
    def __init__(self):
        super().__init__("redis", critical=False)  # Redis不是关键依赖
    
    def check(self) -> Dict[str, Any]:
        """检查Redis连接"""
        try:
            from src.cache.redis_cache import get_redis_client
            
            start_time = time.time()
            
            client = get_redis_client()
            if client is None:
                return {
                    "status": HealthStatus.DEGRADED,
                    "details": {"error": "Redis客户端未初始化"}
                }
            
            # 测试连接
            result = client.ping()
            latency = time.time() - start_time
            
            if result:
                # 获取Redis信息
                info = client.info()
                return {
                    "status": HealthStatus.HEALTHY,
                    "details": {
                        "latency_seconds": latency,
                        "version": info.get('redis_version', 'unknown'),
                        "used_memory": info.get('used_memory', 0),
                        "connected_clients": info.get('connected_clients', 0),
                        "total_commands_processed": info.get('total_commands_processed', 0),
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "details": {
                        "error": "Redis ping失败",
                        "latency_seconds": latency
                    }
                }
                
        except ImportError:
            return {
                "status": HealthStatus.DEGRADED,
                "details": {"error": "Redis模块不可用"}
            }
        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return {
                "status": HealthStatus.DEGRADED,
                "details": {"error": str(e)}
            }


class CacheHealthCheck(HealthCheck):
    """缓存健康检查"""
    
    def __init__(self):
        super().__init__("cache", critical=False)
    
    def check(self) -> Dict[str, Any]:
        """检查缓存系统"""
        try:
            from src.cache.manager import get_cache_manager
            
            start_time = time.time()
            
            manager = get_cache_manager()
            
            # 测试缓存
            test_key = f"health_check_{int(time.time())}"
            test_value = "test_value"
            
            # 写入缓存
            success = manager.set(test_key, test_value, 10)
            
            # 读取缓存
            if success:
                retrieved = manager.get(test_key)
                cache_working = retrieved == test_value
            else:
                cache_working = False
            
            latency = time.time() - start_time
            
            # 获取缓存统计
            stats = manager.get_stats()
            
            if cache_working:
                return {
                    "status": HealthStatus.HEALTHY,
                    "details": {
                        "latency_seconds": latency,
                        "hits": stats.get('hits', 0),
                        "misses": stats.get('misses', 0),
                        "hit_rate": stats.get('hits', 0) / max(stats.get('hits', 0) + stats.get('misses', 0), 1),
                        "penetration_protected": stats.get('penetration_protected', 0),
                        "avalanche_protected": stats.get('avalanche_protected', 0),
                    }
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "details": {
                        "error": "缓存读写测试失败",
                        "latency_seconds": latency,
                        "stats": stats
                    }
                }
                
        except Exception as e:
            logger.error(f"缓存健康检查失败: {e}")
            return {
                "status": HealthStatus.DEGRADED,
                "details": {"error": str(e)}
            }


class ExternalServiceHealthCheck(HealthCheck):
    """外部服务健康检查（东方财富API）"""
    
    def __init__(self):
        super().__init__("external_api", critical=False)
    
    def check(self) -> Dict[str, Any]:
        """检查外部API可用性"""
        try:
            from src.fetcher import fetch_fund_data
            
            start_time = time.time()
            
            # 测试一个简单的基金数据获取
            # 使用一个常见的基金代码
            test_fund_code = "000001"  # 华夏成长
            
            result = fetch_fund_data(test_fund_code)
            latency = time.time() - start_time
            
            if result and isinstance(result, dict):
                return {
                    "status": HealthStatus.HEALTHY,
                    "details": {
                        "latency_seconds": latency,
                        "test_fund_code": test_fund_code,
                        "has_data": bool(result.get('data') or result.get('name'))
                    }
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "details": {
                        "error": "外部API返回空数据",
                        "latency_seconds": latency,
                        "test_fund_code": test_fund_code
                    }
                }
                
        except Exception as e:
            logger.error(f"外部API健康检查失败: {e}")
            return {
                "status": HealthStatus.DEGRADED,
                "details": {"error": str(e)}
            }


class DiskSpaceHealthCheck(HealthCheck):
    """磁盘空间健康检查"""
    
    def __init__(self, path: str = "/", warning_threshold: float = 0.8, 
                 critical_threshold: float = 0.9):
        super().__init__("disk_space", critical=True)
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def check(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            usage = psutil.disk_usage(self.path)
            
            used_percent = usage.used / usage.total
            
            if used_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
            elif used_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                "status": status,
                "details": {
                    "path": self.path,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "used_percent": used_percent,
                    "warning_threshold": self.warning_threshold,
                    "critical_threshold": self.critical_threshold,
                }
            }
        except Exception as e:
            logger.error(f"磁盘空间健康检查失败: {e}")
            return {
                "status": HealthStatus.UNKNOWN,
                "details": {"error": str(e)}
            }


class HealthChecker:
    """健康检查管理器"""
    
    def __init__(self):
        self.checks: List[HealthCheck] = [
            ApplicationHealthCheck(),
            DatabaseHealthCheck(),
            RedisHealthCheck(),
            CacheHealthCheck(),
            ExternalServiceHealthCheck(),
            DiskSpaceHealthCheck(),
        ]
    
    def add_check(self, check: HealthCheck):
        """添加健康检查"""
        self.checks.append(check)
    
    def run_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        overall_status = HealthStatus.HEALTHY
        critical_failures = 0
        
        for check in self.checks:
            try:
                check_result = check.check()
                results[check.name] = check_result
                
                # 更新整体状态
                if check_result["status"] == HealthStatus.UNHEALTHY:
                    if check.critical:
                        critical_failures += 1
                        overall_status = HealthStatus.UNHEALTHY
                    elif overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                elif check_result["status"] == HealthStatus.DEGRADED:
                    if overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                        
            except Exception as e:
                logger.error(f"健康检查 {check.name} 执行失败: {e}")
                results[check.name] = {
                    "status": HealthStatus.UNKNOWN,
                    "details": {"error": str(e)}
                }
                
                if check.critical:
                    critical_failures += 1
                    overall_status = HealthStatus.UNHEALTHY
        
        # 汇总信息
        timestamp = datetime.now().isoformat()
        
        return {
            "status": overall_status,
            "timestamp": timestamp,
            "critical_failures": critical_failures,
            "checks": results,
            "summary": {
                "total_checks": len(self.checks),
                "healthy": sum(1 for r in results.values() 
                              if r.get("status") == HealthStatus.HEALTHY),
                "degraded": sum(1 for r in results.values() 
                               if r.get("status") == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for r in results.values() 
                                if r.get("status") == HealthStatus.UNHEALTHY),
                "unknown": sum(1 for r in results.values() 
                              if r.get("status") == HealthStatus.UNKNOWN),
            }
        }
    
    def get_health_status(self) -> Tuple[str, Dict[str, Any]]:
        """获取健康状态（用于HTTP响应）"""
        result = self.run_checks()
        
        # 根据状态确定HTTP状态码
        if result["status"] == HealthStatus.HEALTHY:
            http_status = 200
        elif result["status"] == HealthStatus.DEGRADED:
            http_status = 206  # Partial Content
        else:
            http_status = 503  # Service Unavailable
        
        return http_status, result


# 单例实例
_health_checker = None

def get_health_checker() -> HealthChecker:
    """获取健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        logger.info("健康检查器初始化完成")
    return _health_checker


def create_health_response():
    """创建健康检查响应（用于Flask路由）"""
    checker = get_health_checker()
    status_code, health_data = checker.get_health_status()
    
    return health_data, status_code