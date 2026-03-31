"""
Tests for config module
PostgreSQL 专用
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import (
    ConfigManager,
    DatabaseConfig,
    JwtConfig,
    RedisConfig,
    SecurityConfig,
    get_config,
)


class TestDatabaseConfig:
    """Tests for database configuration"""

    @patch.dict(
        os.environ,
        {
            "FUND_DAILY_DB_HOST": "testhost",
            "FUND_DAILY_DB_PORT": "5433",
            "FUND_DAILY_DB_NAME": "testdb",
            "FUND_DAILY_DB_USER": "testuser",
            "FUND_DAILY_DB_PASSWORD": "testpass",
        },
    )
    def test_from_env_postgres(self):
        """Test PostgreSQL config from environment"""
        config = DatabaseConfig.from_env()
        assert config.host == "testhost"
        assert config.port == 5433
        assert config.name == "testdb"
        assert config.user == "testuser"
        assert config.password == "testpass"

    def test_from_env_defaults(self):
        """Test default values"""
        # Clear environment variables
        for key in os.environ:
            if key.startswith("FUND_DAILY_DB_"):
                os.environ.pop(key)

        config = DatabaseConfig.from_env()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "fund_daily"
        assert config.user == "kid"
        assert config.password == ""

    def test_validate_postgres_valid(self):
        """Test PostgreSQL validation with valid config"""
        config = DatabaseConfig(host="localhost", port=5432, name="testdb", user="testuser", password="testpass")
        errors = config.validate()
        assert errors == []

    def test_validate_postgres_invalid(self):
        """Test PostgreSQL validation with invalid config"""
        config = DatabaseConfig(
            host="", port=5432, name="", user="", password="testpass"  # Empty host  # Empty name  # Empty user
        )
        errors = config.validate()
        assert len(errors) == 3
        assert "PostgreSQL 主机地址不能为空" in errors
        assert "数据库名称不能为空" in errors
        assert "数据库用户不能为空" in errors

    # 注意：DatabaseConfig 不再有 type 参数，仅支持 PostgreSQL
    # test_validate_invalid_type 测试已移除


class TestRedisConfig:
    """Tests for Redis configuration"""

    @patch.dict(
        os.environ,
        {
            "FUND_DAILY_REDIS_HOST": "redis-host",
            "FUND_DAILY_REDIS_PORT": "6380",
            "FUND_DAILY_REDIS_DB": "2",
            "FUND_DAILY_REDIS_PASSWORD": "redis-pass",
            "FUND_DAILY_REDIS_TTL": "900",
        },
    )
    def test_from_env(self):
        """Test Redis config from environment"""
        config = RedisConfig.from_env()
        assert config.host == "redis-host"
        assert config.port == 6380
        assert config.db == 2
        assert config.password == "redis-pass"
        assert config.ttl == 900

    def test_from_env_defaults(self):
        """Test default values"""
        # Clear environment variables
        for key in os.environ:
            if key.startswith("REDIS_"):
                os.environ.pop(key)

        config = RedisConfig.from_env()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
        assert config.ttl == 1800

    def test_validate_valid(self):
        """Test validation with valid config"""
        config = RedisConfig(host="localhost", port=6379, db=0, password=None, ttl=1800)
        errors = config.validate()
        assert errors == []

    def test_validate_invalid(self):
        """Test validation with invalid config"""
        config = RedisConfig(
            host="", port=0, db=16, ttl=-1  # Empty host  # Invalid port  # Invalid DB (should be 0-15)  # Invalid TTL
        )
        errors = config.validate()
        assert len(errors) == 4


class TestSecurityConfig:
    """Tests for security configuration"""

    @patch.dict(
        os.environ,
        {
            "FUND_DAILY_SECRET_KEY": "test-secret-key-12345678901234567890",
            "FUND_DAILY_SECURE_COOKIES": "true",
            "FUND_DAILY_SSL_VERIFY": "0",
        },
    )
    def test_from_env(self):
        """Test security config from environment"""
        config = SecurityConfig.from_env()
        assert config.secret_key == "test-secret-key-12345678901234567890"
        assert config.secure_cookies is True
        assert config.ssl_verify is False

    def test_from_env_defaults(self):
        """Test default values"""
        # Clear environment variables
        for key in os.environ:
            if key.startswith("FUND_DAILY_"):
                os.environ.pop(key)

        config = SecurityConfig.from_env()
        assert config.secret_key is None
        assert config.secure_cookies is False
        assert config.ssl_verify is True

    def test_validate_optional_key(self):
        """Test validation - secret key is optional but JWT must be valid"""
        config = SecurityConfig(secret_key=None, jwt=JwtConfig(secret="a-valid-jwt-secret-that-is-32chars!!"))
        errors = config.validate()
        assert len(errors) == 1  # 建议设置，但不强制
        assert any("建议设置" in error for error in errors)

    def test_validate_short_key(self):
        """Test validation with short secret key"""
        config = SecurityConfig(secret_key="short", jwt=JwtConfig(secret="test-jwt-secret"))
        errors = config.validate()
        assert len(errors) == 2  # Flask密钥短 + JWT密钥短
        assert any("至少32字符" in error for error in errors)

    def test_validate_valid_config(self):
        """Test validation with valid config"""
        config = SecurityConfig(
            secret_key="a-valid-secret-key-that-is-32chars!",
            jwt=JwtConfig(secret="a-valid-jwt-secret-that-is-32chars!!"),
        )
        errors = config.validate()
        assert errors == []  # 全部有效


class TestConfigManager:
    """Tests for ConfigManager"""

    @patch.dict(
        os.environ,
        {
            "FUND_DAILY_ENV": "testing",
            "FUND_DAILY_DB_TYPE": "postgres",
            "REDIS_HOST": "localhost",
            "FUND_DAILY_CACHE_DURATION": "300",
            "FUND_DAILY_REQUEST_INTERVAL": "1.0",
            "PORT": "8080",
            "FLASK_DEBUG": "true",
            "FLASK_HOST": "127.0.0.1",
            "FUND_DAILY_VERSION": "2.0.0",
            "FUND_DAILY_DEFAULT_FUNDS": "000001,000002",
        },
    )
    def test_config_manager_initialization(self):
        """Test ConfigManager initialization"""
        config = ConfigManager()

        # Test app config
        assert config.app.env == "testing"
        assert config.app.version == "2.0.0"
        assert config.app.default_funds == ["000001", "000002"]

        # Test database config
        # Database type is fixed to PostgreSQL, no longer a configurable field

        # Test Redis config
        assert config.redis.host == "localhost"

        # Test cache config
        assert config.cache.duration == 300
        assert config.cache.request_interval == 1.0

        # Test server config
        assert config.server.port == 8080
        assert config.server.debug is True
        assert config.server.host == "127.0.0.1"

    def test_is_development(self):
        """Test is_development method"""
        config = ConfigManager()

        # Mock app.env
        config.app.env = "development"
        assert config.is_development() is True

        config.app.env = "production"
        assert config.is_development() is False

        config.app.env = "testing"
        assert config.is_development() is False

    def test_get_database_url(self):
        """Test get_database_url method"""
        config = ConfigManager()

        # Test PostgreSQL URL
        config.database.type = "postgres"
        config.database.host = "localhost"
        config.database.port = 5432
        config.database.name = "testdb"
        config.database.user = "testuser"
        config.database.password = "testpass"

        url = config.get_database_url()
        assert url == "postgresql://testuser:testpass@localhost:5432/testdb"
        assert url.startswith("postgresql://")


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance"""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
