"""
JWT Token 认证测试
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置测试环境变量
os.environ['FUND_DAILY_DB_HOST'] = 'localhost'
os.environ['FUND_DAILY_DB_PASSWORD'] = '941005'
os.environ['FUND_DAILY_JWT_SECRET'] = 'test-jwt-secret-for-testing-only'


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
        import jwt
        from datetime import datetime, timezone, timedelta
        from src.jwt_auth import verify_access_token, JWT_SECRET
        
        # 使用与 jwt_auth 模块相同的密钥创建已过期的 token
        payload = {
            "sub": "user_expired",
            "username": "expireduser",
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=1),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),  # 已过期
            "iss": "fund-daily"
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        is_valid, _, error = verify_access_token(expired_token)
        assert is_valid is False
        assert "expired" in error.lower()

    def test_get_token_from_header(self):
        """测试从请求头提取 token"""
        from src.jwt_auth import get_token_from_header
        from flask import Flask
        
        app = Flask(__name__)
        
        with app.test_request_context(headers={"Authorization": "Bearer mytesttoken123"}):
            token = get_token_from_header()
            assert token == "mytesttoken123"
        
        with app.test_request_context(headers={"Authorization": "bearer lowercase_token"}):
            token = get_token_from_header()
            assert token is None  # 必须是 Bearer (大写B)

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


class TestJwtDecorator:
    """JWT 装饰器测试"""

    def test_jwt_required_valid(self):
        """测试有效 JWT 通过装饰器"""
        from src.jwt_auth import create_access_token, jwt_required
        from flask import Flask, g, jsonify
        from functools import wraps
        
        app = Flask(__name__)
        
        @app.route("/test")
        @jwt_required
        def test_endpoint():
            return jsonify({"user_id": g.user_id, "username": g.username})
        
        token = create_access_token("decorator_user", "decouser")
        
        with app.test_client() as client:
            resp = client.get("/test", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["user_id"] == "decorator_user"
            assert data["username"] == "decouser"

    def test_jwt_required_missing(self):
        """测试缺少 token 返回 401"""
        from src.jwt_auth import jwt_required
        from flask import Flask, jsonify
        
        app = Flask(__name__)
        
        @app.route("/test")
        @jwt_required
        def test_endpoint():
            return jsonify({"success": True})
        
        with app.test_client() as client:
            resp = client.get("/test")
            assert resp.status_code == 401
            data = resp.get_json()
            assert data["need_auth"] is True
            assert data["error_code"] == "MISSING_TOKEN"

    def test_jwt_required_invalid(self):
        """测试无效 token 返回 401"""
        from src.jwt_auth import jwt_required
        from flask import Flask, jsonify
        
        app = Flask(__name__)
        
        @app.route("/test")
        @jwt_required
        def test_endpoint():
            return jsonify({"success": True})
        
        with app.test_client() as client:
            resp = client.get("/test", headers={"Authorization": "Bearer badtoken"})
            assert resp.status_code == 401
            data = resp.get_json()
            assert data["error_code"] == "INVALID_TOKEN"

    def test_jwt_optional_with_token(self):
        """测试 jwt_optional 有 token 时注入用户"""
        from src.jwt_auth import create_access_token, jwt_optional
        from flask import Flask, g, jsonify
        
        app = Flask(__name__)
        
        @app.route("/test")
        @jwt_optional
        def test_endpoint():
            if g.is_authenticated:
                return jsonify({"auth": True, "user_id": g.user_id})
            return jsonify({"auth": False})
        
        token = create_access_token("optional_user", "optuser")
        
        with app.test_client() as client:
            resp = client.get("/test", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["auth"] is True
            assert data["user_id"] == "optional_user"

    def test_jwt_optional_no_token(self):
        """测试 jwt_optional 无 token 时继续执行"""
        from src.jwt_auth import jwt_optional
        from flask import Flask, g, jsonify
        
        app = Flask(__name__)
        
        @app.route("/test")
        @jwt_optional
        def test_endpoint():
            if g.is_authenticated:
                return jsonify({"auth": True})
            return jsonify({"auth": False})
        
        with app.test_client() as client:
            resp = client.get("/test")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["auth"] is False
