"""
JWT Token 认证测试

注意：jwt_required/jwt_optional 装饰器和 get_token_from_header
是 Flask 遗留实现，已迁移到 FastAPI 的依赖注入模式。
本测试文件保留核心 JWT 功能测试。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 设置测试环境变量
os.environ["FUND_DAILY_DB_HOST"] = "localhost"
os.environ["FUND_DAILY_DB_PASSWORD"] = "941005"
os.environ["FUND_DAILY_JWT_SECRET"] = "test-jwt-secret-for-testing-only"


class TestJwtAuth:
    """JWT 认证功能测试"""

    def test_create_and_verify_token(self):
        """测试 token 创建和验证"""
        from src.jwt_auth import create_token_pair, verify_access_token

        tokens = create_token_pair("user123", "testuser")

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "Bearer"

        # 验证 access token
        is_valid, payload, error = verify_access_token(tokens["access_token"])
        assert is_valid is True
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"
        assert error is None

    def test_verify_refresh_token(self):
        """测试 refresh token 验证"""
        from src.jwt_auth import create_token_pair, verify_refresh_token

        tokens = create_token_pair("user456", "refreshtest")

        is_valid, payload, error = verify_refresh_token(tokens["refresh_token"])
        assert is_valid is True
        assert payload["sub"] == "user456"
        assert payload["type"] == "refresh"

    def test_verify_wrong_type_token(self):
        """测试用 access token 验证会失败"""
        from src.jwt_auth import create_token_pair, verify_refresh_token

        tokens = create_token_pair("user789", "typetest")

        # 用 refresh token 类型验证 access token
        is_valid, payload, error = verify_refresh_token(tokens["access_token"])
        assert is_valid is False
        assert "type" in error.lower()

    def test_verify_invalid_token(self):
        """测试无效 token 验证"""
        from src.jwt_auth import verify_access_token

        is_valid, payload, error = verify_access_token("invalid.token.here")
        assert is_valid is False
        assert error is not None

    def test_expired_token(self):
        """测试过期 token"""
        from datetime import datetime, timedelta, timezone

        import jwt

        # 临时覆盖 JWT_SECRET 以使用测试密钥
        import src.jwt_auth as jwt_auth_module
        from src.jwt_auth import verify_access_token

        original_secret = jwt_auth_module.JWT_SECRET

        try:
            jwt_auth_module.JWT_SECRET = "test-jwt-secret-for-testing-only"
            # 使用与 jwt_auth 模块相同的密钥创建已过期的 token
            payload = {
                "sub": "user_expired",
                "username": "expireduser",
                "type": "access",
                "iat": datetime.now(timezone.utc) - timedelta(hours=1),
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),  # 已过期
                "iss": "fund-daily",
            }
            expired_token = jwt.encode(payload, "test-jwt-secret-for-testing-only", algorithm="HS256")

            is_valid, _, error = verify_access_token(expired_token)
            assert is_valid is False
            assert "expired" in error.lower()
        finally:
            jwt_auth_module.JWT_SECRET = original_secret

    def test_get_user_from_token(self):
        """测试从 token 获取用户"""
        from src.jwt_auth import create_token_pair, get_user_from_token

        tokens = create_token_pair("fetchuser123", "fetchtest")
        is_valid, user_id, error = get_user_from_token(tokens["access_token"])

        assert is_valid is True
        assert user_id == "fetchuser123"
        assert error is None

    def test_decode_unsafe(self):
        """测试不验证签名的解析"""
        from src.jwt_auth import create_access_token, decode_token_unsafe

        token = create_access_token("unsafe_user", "unsafetest")
        payload = decode_token_unsafe(token)

        assert payload is not None
        assert payload["sub"] == "unsafe_user"
        assert payload["username"] == "unsafetest"
