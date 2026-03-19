"""
统一配置管理器
解决配置分散问题，提供类型安全和验证
"""

import os
import logging
from typing import Any, Optional, Dict, Union, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置（仅支持PostgreSQL）"""
    host: str = "localhost"
    port: int = 5432
    name: str = "fund_daily"
    user: str = "kid"
    password: str = ""
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """从环境变量创建配置"""
        return cls(
            host=os.getenv("FUND_DAILY_DB_HOST", "localhost"),
            port=int(os.getenv("FUND_DAILY_DB_PORT", "5432")),
            name=os.getenv("FUND_DAILY_DB_NAME", "fund_daily"),
            user=os.getenv("FUND_DAILY_DB_USER", "kid"),
            password=os.getenv("FUND_DAILY_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        )
    
    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        if not self.host:
            errors.append("PostgreSQL 主机地址不能为空")
        if not self.name:
            errors.append("数据库名称不能为空")
        if not self.user:
            errors.append("数据库用户不能为空")
        
        return errors


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ttl: int = 1800  # 默认30分钟
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        """从环境变量创建配置"""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            ttl=int(os.getenv("REDIS_TTL", "1800")),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.host:
            errors.append("Redis 主机地址不能为空")
        
        if self.port <= 0 or self.port > 65535:
            errors.append(f"Redis 端口无效: {self.port}")
        
        if self.db < 0 or self.db > 15:
            errors.append(f"Redis 数据库编号无效: {self.db}")
        
        if self.ttl <= 0:
            errors.append(f"Redis TTL 必须为正数: {self.ttl}")
        
        return errors


@dataclass
class JwtConfig:
    secret: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    @classmethod
    def from_env(cls) -> "JwtConfig":
        secret = os.getenv("FUND_DAILY_JWT_SECRET", "")
        env = os.getenv("FUND_DAILY_ENV", "development")
        
        # 生产环境强制要求强密钥
        if env == "production" and (not secret or secret == "fund-daily-jwt-secret-change-in-production"):
            raise ValueError(
                "生产环境必须设置强JWT密钥！请设置 FUND_DAILY_JWT_SECRET 环境变量。"
                "密钥长度至少32字符，包含大小写字母、数字和特殊字符。"
            )
        
        # 开发环境使用默认值（如果未设置）
        if not secret:
            secret = "dev-jwt-secret-change-in-production"
        
        return cls(
            secret=secret,
            access_token_expire_minutes=int(os.getenv("FUND_DAILY_JWT_EXPIRE_MINUTES", "60")),
            refresh_token_expire_days=int(os.getenv("FUND_DAILY_JWT_REFRESH_DAYS", "7")),
        )
    
    def validate(self, env: str = "development") -> List[str]:
        """验证JWT配置"""
        errors = []
        
        if not self.secret:
            errors.append("JWT密钥不能为空")
        elif len(self.secret) < 32 and env == "production":
            errors.append(f"生产环境JWT密钥长度至少32字符，当前: {len(self.secret)}")
        
        if self.access_token_expire_minutes <= 0:
            errors.append(f"访问令牌过期时间必须为正数: {self.access_token_expire_minutes}")
        
        if self.refresh_token_expire_days <= 0:
            errors.append(f"刷新令牌过期时间必须为正数: {self.refresh_token_expire_days}")
        
        return errors


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: Optional[str] = None
    secure_cookies: bool = False
    ssl_verify: bool = True
    jwt: JwtConfig = field(default_factory=JwtConfig)
    
    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """从环境变量创建配置"""
        secret_key = os.getenv("FUND_DAILY_SECRET_KEY")
        secure_cookies = os.getenv("FUND_DAILY_SECURE_COOKIES", "").lower() == "true"
        ssl_verify = os.getenv("FUND_DAILY_SSL_VERIFY", "1") != "0"
        
        return cls(
            secret_key=secret_key,
            secure_cookies=secure_cookies,
            ssl_verify=ssl_verify,
            jwt=JwtConfig.from_env(),
        )
    
    def validate(self, is_production: bool = False) -> List[str]:
        """验证配置"""
        errors = []
        
        if is_production and not self.secret_key:
            errors.append("生产环境必须设置 FUND_DAILY_SECRET_KEY")
        
        if self.secret_key and len(self.secret_key) < 32:
            errors.append("Flask密钥长度至少32字符，建议使用 secrets.token_hex(32) 生成")
        
        # 验证JWT配置
        env = "production" if is_production else "development"
        errors.extend(self.jwt.validate(env))
        
        return errors


@dataclass
class CacheConfig:
    """缓存配置"""
    duration: int = 600  # 默认10分钟
    request_interval: float = 0.5  # 请求间隔秒数
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """从环境变量创建配置"""
        return cls(
            duration=int(os.getenv("FUND_DAILY_CACHE_DURATION", "600")),
            request_interval=float(os.getenv("FUND_DAILY_REQUEST_INTERVAL", "0.5")),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.duration <= 0:
            errors.append(f"缓存时间必须为正数: {self.duration}")
        
        if self.request_interval <= 0:
            errors.append(f"请求间隔必须为正数: {self.request_interval}")
        
        return errors


@dataclass
class ServerConfig:
    """服务器配置"""
    port: int = 5000
    debug: bool = False
    host: str = "0.0.0.0"
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """从环境变量创建配置"""
        return cls(
            port=int(os.getenv("FUND_DAILY_SERVER_PORT", os.getenv("PORT", "5000"))),
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
            host=os.getenv("FLASK_HOST", "0.0.0.0"),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.port <= 0 or self.port > 65535:
            errors.append(f"服务器端口无效: {self.port}")
        
        return errors


@dataclass
class AppConfig:
    """应用配置"""
    env: str = "development"  # development, production, testing
    version: str = "2.6.0"
    default_funds: List[str] = field(default_factory=lambda: ["000001", "110022", "161725"])
    admin_token: Optional[str] = None  # API网关管理员令牌
    user_token: Optional[str] = None   # API网关用户令牌
    readonly_token: Optional[str] = None  # API网关只读令牌
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量创建配置"""
        return cls(
            env=os.getenv("FUND_DAILY_ENV", "development"),
            version=os.getenv("FUND_DAILY_VERSION", "2.6.0"),
            default_funds=os.getenv("FUND_DAILY_DEFAULT_FUNDS", "000001,110022,161725").split(","),
            admin_token=os.getenv("FUND_DAILY_ADMIN_TOKEN"),
            user_token=os.getenv("FUND_DAILY_USER_TOKEN"),
            readonly_token=os.getenv("FUND_DAILY_READONLY_TOKEN"),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.env not in ["development", "production", "testing"]:
            errors.append(f"环境必须为 development/production/testing，当前为: {self.env}")
        
        for fund_code in self.default_funds:
            if not fund_code or not fund_code.isdigit() or len(fund_code) != 6:
                errors.append(f"默认基金代码无效: {fund_code}")
        
        # 生产环境必须设置API网关令牌
        if self.env == "production":
            if not self.admin_token:
                errors.append("生产环境必须设置 FUND_DAILY_ADMIN_TOKEN")
            if not self.user_token:
                errors.append("生产环境必须设置 FUND_DAILY_USER_TOKEN")
            if not self.readonly_token:
                errors.append("生产环境必须设置 FUND_DAILY_READONLY_TOKEN")
        
        return errors


class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self):
        self.database = DatabaseConfig.from_env()
        self.redis = RedisConfig.from_env()
        self.security = SecurityConfig.from_env()
        self.cache = CacheConfig.from_env()
        self.server = ServerConfig.from_env()
        self.app = AppConfig.from_env()
        
        # 验证所有配置
        self._validate_all()
    
    def _validate_all(self):
        """验证所有配置"""
        all_errors = []
        
        # 收集所有错误
        all_errors.extend(self.database.validate())
        all_errors.extend(self.redis.validate())
        all_errors.extend(self.security.validate(is_production=self.app.env == "production"))
        all_errors.extend(self.cache.validate())
        all_errors.extend(self.server.validate())
        all_errors.extend(self.app.validate())
        
        # 如果有错误，记录并抛出异常
        if all_errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {error}" for error in all_errors)
            logger.error(error_msg)
            
            # 如果是生产环境，抛出异常
            if self.app.env == "production":
                raise ValueError(error_msg)
            else:
                logger.warning("开发环境，继续运行但配置可能有问题")
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        return f"postgresql://{self.database.user}:{self.database.password}@{self.database.host}:{self.database.port}/{self.database.name}"
    
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.app.env == "production"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于调试）"""
        return {
            "database": {
                "type": "postgres",  # 固定为PostgreSQL
                "host": self.database.host,
                "port": self.database.port,
                "name": self.database.name,
                "user": self.database.user,
                "has_password": bool(self.database.password),
            },
            "redis": {
                "host": self.redis.host,
                "port": self.redis.port,
                "db": self.redis.db,
                "has_password": bool(self.redis.password),
                "ttl": self.redis.ttl,
            },
            "security": {
                "has_secret_key": bool(self.security.secret_key),
                "secure_cookies": self.security.secure_cookies,
                "ssl_verify": self.security.ssl_verify,
            },
            "cache": {
                "duration": self.cache.duration,
                "request_interval": self.cache.request_interval,
            },
            "server": {
                "port": self.server.port,
                "debug": self.server.debug,
                "host": self.server.host,
            },
            "app": {
                "env": self.app.env,
                "version": self.app.version,
                "default_funds": self.app.default_funds,
            }
        }


# 全局单例实例（线程安全）
import threading
_config_instance = None
_config_lock = threading.Lock()

def get_config() -> ConfigManager:
    """获取配置管理器实例（线程安全的单例模式）"""
    global _config_instance
    
    # 双重检查锁定模式
    if _config_instance is None:
        with _config_lock:
            if _config_instance is None:
                _config_instance = ConfigManager()
                logger.info("配置管理器初始化完成")
                logger.info(f"环境: {_config_instance.app.env}")
                logger.info(f"数据库: PostgreSQL ({_config_instance.database.host}:{_config_instance.database.port})")
    
    return _config_instance


# 兼容性函数
def get_database_config() -> Dict[str, Any]:
    """获取数据库配置（兼容旧代码）"""
    config = get_config().database
    return {
        "type": "postgres",  # 固定为PostgreSQL
        "host": config.host,
        "port": config.port,
        "name": config.name,
        "user": config.user,
        "password": config.password,
    }


def get_redis_config() -> Dict[str, Any]:
    """获取Redis配置（兼容旧代码）"""
    config = get_config().redis
    return {
        "host": config.host,
        "port": config.port,
        "db": config.db,
        "password": config.password,
        "ttl": config.ttl,
    }