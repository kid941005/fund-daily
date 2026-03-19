#!/usr/bin/env python3
"""
环境检查脚本
检查Fund Daily运行所需的所有环境和配置
"""

import os
import sys
import logging
from typing import List, Dict, Any, Tuple

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class EnvironmentChecker:
    """环境检查器"""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
    
    def check(self, name: str, condition: bool, message: str, critical: bool = False):
        """执行检查并记录结果"""
        status = "✅" if condition else "❌"
        if not condition and critical:
            status = "🚨"
        
        self.results.append({
            "name": name,
            "status": status,
            "condition": condition,
            "message": message,
            "critical": critical
        })
        
        if condition:
            logger.info(f"{status} {name}: {message}")
        else:
            if critical:
                logger.error(f"{status} {name}: {message}")
            else:
                logger.warning(f"{status} {name}: {message}")
        
        return condition
    
    def check_python_version(self) -> bool:
        """检查Python版本"""
        import platform
        version = platform.python_version()
        major, minor, _ = map(int, version.split('.'))
        
        return self.check(
            "Python版本",
            major == 3 and minor >= 11,
            f"当前版本: {version} (需要 >= 3.11)",
            critical=True
        )
    
    def check_required_modules(self) -> bool:
        """检查必需的Python模块"""
        required_modules = [
            ("flask", "Flask框架"),
            ("psycopg2", "PostgreSQL驱动"),
            ("requests", "HTTP请求库"),
            ("numpy", "数值计算库"),
        ]
        
        all_passed = True
        for module, description in required_modules:
            try:
                __import__(module)
                self.check(
                    f"模块: {module}",
                    True,
                    f"{description} - 已安装"
                )
            except ImportError:
                all_passed = self.check(
                    f"模块: {module}",
                    False,
                    f"{description} - 未安装",
                    critical=True
                )
        
        # 可选模块
        optional_modules = [
            ("redis", "Redis缓存"),
            ("prometheus_client", "监控指标"),
            ("psutil", "系统监控"),
        ]
        
        for module, description in optional_modules:
            try:
                __import__(module)
                self.check(
                    f"模块: {module} (可选)",
                    True,
                    f"{description} - 已安装"
                )
            except ImportError:
                self.check(
                    f"模块: {module} (可选)",
                    False,
                    f"{description} - 未安装，某些功能受限"
                )
        
        return all_passed
    
    def check_environment_variables(self) -> bool:
        """检查环境变量"""
        env_vars = [
            ("FUND_DAILY_DB_HOST", "数据库主机", False),
            ("FUND_DAILY_DB_PASSWORD", "数据库密码", True),
            ("FUND_DAILY_SECRET_KEY", "Flask密钥", False),
            ("REDIS_HOST", "Redis主机", False),
        ]
        
        all_passed = True
        for var, description, required in env_vars:
            value = os.getenv(var)
            
            if required and not value:
                all_passed = self.check(
                    f"环境变量: {var}",
                    False,
                    f"{description} - 未设置（必需）",
                    critical=True
                )
            elif value:
                # 敏感信息隐藏
                display_value = value
                if "PASSWORD" in var or "SECRET" in var or "KEY" in var:
                    if len(value) > 8:
                        display_value = f"{value[:4]}...{value[-4:]}"
                    else:
                        display_value = "***"
                
                self.check(
                    f"环境变量: {var}",
                    True,
                    f"{description} - 已设置 ({display_value})"
                )
            else:
                self.check(
                    f"环境变量: {var}",
                    False,
                    f"{description} - 未设置"
                )
        
        return all_passed
    
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            import psycopg2
            
            host = os.getenv("FUND_DAILY_DB_HOST", "localhost")
            password = os.getenv("FUND_DAILY_DB_PASSWORD")
            
            if not password:
                return self.check(
                    "数据库连接",
                    False,
                    "数据库密码未设置，无法测试连接",
                    critical=True
                )
            
            try:
                conn = psycopg2.connect(
                    host=host,
                    port=os.getenv("FUND_DAILY_DB_PORT", "5432"),
                    database=os.getenv("FUND_DAILY_DB_NAME", "fund_daily"),
                    user=os.getenv("FUND_DAILY_DB_USER", "kid"),
                    password=password,
                    connect_timeout=5
                )
                conn.close()
                
                return self.check(
                    "数据库连接",
                    True,
                    f"成功连接到 {host}"
                )
            except Exception as e:
                return self.check(
                    "数据库连接",
                    False,
                    f"连接失败: {str(e)}",
                    critical=True
                )
                
        except ImportError:
            return self.check(
                "数据库连接",
                False,
                "psycopg2模块未安装，无法测试连接",
                critical=True
            )
    
    def check_redis_connection(self) -> bool:
        """检查Redis连接"""
        try:
            import redis
            
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            
            try:
                r = redis.Redis(
                    host=host,
                    port=port,
                    db=int(os.getenv("REDIS_DB", "0")),
                    password=os.getenv("REDIS_PASSWORD"),
                    socket_connect_timeout=3,
                    socket_timeout=3
                )
                if r.ping():
                    return self.check(
                        "Redis连接",
                        True,
                        f"成功连接到 {host}:{port}"
                    )
                else:
                    return self.check(
                        "Redis连接",
                        False,
                        f"连接到 {host}:{port} 但ping失败"
                    )
            except Exception as e:
                return self.check(
                    "Redis连接",
                    False,
                    f"连接失败: {str(e)}"
                )
                
        except ImportError:
            return self.check(
                "Redis连接",
                False,
                "redis模块未安装，Redis功能不可用"
            )
    
    def check_config_file(self) -> bool:
        """检查配置文件"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "config.json")
        
        if os.path.exists(config_path):
            import json
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                return self.check(
                    "配置文件",
                    True,
                    f"配置文件存在，包含 {len(config)} 个配置项"
                )
            except Exception as e:
                return self.check(
                    "配置文件",
                    False,
                    f"配置文件损坏: {str(e)}",
                    critical=True
                )
        else:
            return self.check(
                "配置文件",
                False,
                "配置文件不存在，将使用环境变量和默认值"
            )
    
    def check_directory_permissions(self) -> bool:
        """检查目录权限"""
        directories = [
            ("项目根目录", os.path.dirname(os.path.abspath(__file__))),
            ("数据目录", os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")),
            ("日志目录", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")),
        ]
        
        all_passed = True
        for name, path in directories:
            if os.path.exists(path):
                # 检查可写权限
                if os.access(path, os.W_OK):
                    self.check(
                        f"目录权限: {name}",
                        True,
                        f"{path} - 可写"
                    )
                else:
                    all_passed = self.check(
                        f"目录权限: {name}",
                        False,
                        f"{path} - 不可写",
                        critical=True
                    )
            else:
                # 检查父目录权限
                parent_dir = os.path.dirname(path)
                if os.path.exists(parent_dir) and os.access(parent_dir, os.W_OK):
                    self.check(
                        f"目录权限: {name}",
                        True,
                        f"{path} - 目录不存在但可以创建"
                    )
                else:
                    all_passed = self.check(
                        f"目录权限: {name}",
                        False,
                        f"{path} - 目录不存在且父目录不可写",
                        critical=True
                    )
        
        return all_passed
    
    def check_security(self) -> bool:
        """检查安全配置"""
        all_passed = True
        
        # 检查密钥长度
        secret_key = os.getenv("FUND_DAILY_SECRET_KEY")
        if secret_key:
            if len(secret_key) >= 32:
                self.check(
                    "密钥强度",
                    True,
                    "Flask密钥长度足够（>=32字符）"
                )
            else:
                all_passed = self.check(
                    "密钥强度",
                    False,
                    f"Flask密钥长度不足: {len(secret_key)}字符（需要>=32）",
                    critical=True
                )
        else:
            self.check(
                "密钥强度",
                False,
                "Flask密钥未设置，将使用临时密钥（仅适用于开发）"
            )
        
        # 检查JWT密钥
        jwt_secret = os.getenv("FUND_DAILY_JWT_SECRET")
        if jwt_secret:
            if len(jwt_secret) >= 32:
                self.check(
                    "JWT密钥强度",
                    True,
                    "JWT密钥长度足够（>=32字符）"
                )
            else:
                all_passed = self.check(
                    "JWT密钥强度",
                    False,
                    f"JWT密钥长度不足: {len(jwt_secret)}字符（需要>=32）",
                    critical=True
                )
        
        return all_passed
    
    def run_all_checks(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """运行所有检查"""
        logger.info("=" * 60)
        logger.info("Fund Daily 环境检查")
        logger.info("=" * 60)
        
        checks = [
            self.check_python_version,
            self.check_required_modules,
            self.check_environment_variables,
            self.check_database_connection,
            self.check_redis_connection,
            self.check_config_file,
            self.check_directory_permissions,
            self.check_security,
        ]
        
        all_passed = True
        for check_func in checks:
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                logger.error(f"检查失败: {check_func.__name__}: {e}")
                all_passed = False
        
        # 汇总结果
        logger.info("\n" + "=" * 60)
        logger.info("检查结果汇总")
        logger.info("=" * 60)
        
        critical_failures = sum(1 for r in self.results if not r["condition"] and r["critical"])
        warnings = sum(1 for r in self.results if not r["condition"] and not r["critical"])
        successes = sum(1 for r in self.results if r["condition"])
        
        logger.info(f"✅ 成功: {successes}")
        logger.info(f"⚠️  警告: {warnings}")
        logger.info(f"🚨 严重错误: {critical_failures}")
        
        if critical_failures > 0:
            logger.error(f"\n🚨 发现 {critical_failures} 个严重错误，应用可能无法正常运行:")
            for result in self.results:
                if not result["condition"] and result["critical"]:
                    logger.error(f"  - {result['name']}: {result['message']}")
        
        if warnings > 0:
            logger.warning(f"\n⚠️  发现 {warnings} 个警告:")
            for result in self.results:
                if not result["condition"] and not result["critical"]:
                    logger.warning(f"  - {result['name']}: {result['message']}")
        
        if all_passed and critical_failures == 0:
            logger.info("\n🎉 所有检查通过！应用可以正常运行。")
        else:
            logger.info("\n🔧 请根据以上检查结果修复问题。")
        
        return all_passed and critical_failures == 0, self.results


def main():
    """主函数"""
    checker = EnvironmentChecker()
    success, results = checker.run_all_checks()
    
    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())