"""
Tests for db/users.py and db/holdings.py
Mock database connection using monkeypatch
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db.holdings as db_holdings
import db.pool as db_pool
import db.users as db_users

# ---------------------------------------------------------------------------
# Dummy DB objects
# ---------------------------------------------------------------------------


class DummyCursor:
    def __init__(self, results=None):
        self._results = results or []
        self._last_sql = None
        self._last_params = None

    @property
    def rowcount(self):
        return len(self._results)

    def execute(self, sql, params=None):
        self._last_sql = sql
        self._last_params = params

    def fetchall(self):
        return self._results

    def fetchone(self):
        return self._results[0] if self._results else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class DummyConn:
    def __init__(self, results=None):
        self._results = results
        self._cursor = None
        self._committed = False

    def cursor(self, **kwargs):
        # ignore cursor_factory etc.
        self._cursor = DummyCursor(self._results)
        return self._cursor

    def commit(self):
        self._committed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db(monkeypatch):
    """
    Patch get_db and get_cursor at the module level where db.users and
    db.holdings import them (top-level: from .pool import get_db, get_cursor).
    """
    stored_conn = {}
    stored_results = {}

    def mock_get_db():
        conn = DummyConn(stored_results.get("cursor_results"))
        stored_conn["current"] = conn
        return conn

    # get_cursor is called with the conn from get_db - we mock it here
    # so that conn._cursor is also set (matching the real behavior)
    def mock_get_cursor(conn):
        cursor = DummyCursor(stored_results.get("cursor_results"))
        conn._cursor = cursor
        return cursor

    # Patch in both modules that import these names
    monkeypatch.setattr(db_users, "get_db", mock_get_db)
    monkeypatch.setattr(db_users, "get_cursor", mock_get_cursor)
    monkeypatch.setattr(db_holdings, "get_db", mock_get_db)
    monkeypatch.setattr(db_holdings, "get_cursor", mock_get_cursor)

    # Also patch at source
    monkeypatch.setattr(db_pool, "get_db", mock_get_db)
    monkeypatch.setattr(db_pool, "get_cursor", mock_get_cursor)

    return stored_conn, stored_results


# ---------------------------------------------------------------------------
# db/users.py tests
# ---------------------------------------------------------------------------


class TestGetUserByUsername:
    def test_returns_user(self, mock_db):
        from db.users import get_user_by_username

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = [{"user_id": "u1", "username": "alice", "password": "hash"}]
        result = get_user_by_username("alice")
        assert result is not None
        assert result["username"] == "alice"

    def test_returns_none_when_not_found(self, mock_db):
        from db.users import get_user_by_username

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = []
        result = get_user_by_username("nobody")
        assert result is None


class TestVerifyUser:
    def test_verify_user_success(self, mock_db, monkeypatch):
        from db.users import verify_user

        monkeypatch.setattr("src.auth.verify_password", lambda p, h: True)
        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = [{"user_id": "u1", "username": "alice", "password": "hash123"}]
        result = verify_user("alice", "password123")
        assert result is not None
        assert result["username"] == "alice"

    def test_verify_user_wrong_password(self, mock_db, monkeypatch):
        from db.users import verify_user

        monkeypatch.setattr("src.auth.verify_password", lambda p, h: False)
        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = [{"user_id": "u1", "username": "alice", "password": "hash123"}]
        result = verify_user("alice", "wrongpassword")
        assert result is None

    def test_verify_user_not_found(self, mock_db, monkeypatch):
        from db.users import verify_user

        monkeypatch.setattr("src.auth.verify_password", lambda p, h: True)
        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = []
        result = verify_user("nobody", "password")
        assert result is None


class TestGetUserById:
    def test_returns_user(self, mock_db):
        from db.users import get_user_by_id

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = [{"user_id": "u123", "username": "bob", "password": "xyz"}]
        result = get_user_by_id("u123")
        assert result is not None
        assert result["user_id"] == "u123"

    def test_returns_none_when_not_found(self, mock_db):
        from db.users import get_user_by_id

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = []
        result = get_user_by_id("notexist")
        assert result is None


class TestCreateUser:
    def test_create_user_executes(self, mock_db):
        from db.users import create_user

        stored_conn, stored_results = mock_db
        create_user("u_new", "newuser", "hashed_pw")
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "INSERT INTO users" in conn._cursor._last_sql
        assert conn._cursor._last_params == ("u_new", "newuser", "hashed_pw")
        assert conn._committed is True


class TestUpdateUserPassword:
    def test_update_password_executes(self, mock_db):
        from db.users import update_user_password

        stored_conn, stored_results = mock_db
        update_user_password("u1", "new_hash")
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "UPDATE users SET password" in conn._cursor._last_sql
        assert conn._cursor._last_params == ("new_hash", "u1")
        assert conn._committed is True


# ---------------------------------------------------------------------------
# db/holdings.py tests
# ---------------------------------------------------------------------------


class TestGetHoldings:
    def test_get_holdings_returns_list(self, mock_db):
        from db.holdings import get_holdings

        stored_conn, stored_results = mock_db
        holdings = [
            {"code": "000001", "name": "华夏成长", "amount": 10000},
            {"code": "110022", "name": "易方达消费", "amount": 20000},
        ]
        stored_results["cursor_results"] = holdings
        result = get_holdings("u1")
        assert len(result) == 2
        assert result[0]["code"] == "000001"

    def test_get_holdings_empty(self, mock_db):
        from db.holdings import get_holdings

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = []
        result = get_holdings("u1")
        assert result == []


class TestSaveHolding:
    def test_save_holding_inserts(self, mock_db):
        from db.holdings import save_holding

        stored_conn, stored_results = mock_db
        save_holding("u1", "000001", 10000, "华夏成长", 1.5, "2024-01-01")
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "INSERT INTO holdings" in conn._cursor._last_sql
        params = conn._cursor._last_params
        assert params[0] == "u1"
        assert params[1] == "000001"
        assert params[2] == "华夏成长"
        assert params[3] == 10000
        assert conn._committed is True


class TestDeleteHolding:
    def test_delete_holding_executes(self, mock_db):
        from db.holdings import delete_holding

        stored_conn, stored_results = mock_db
        delete_holding("u1", "000001")
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "DELETE FROM holdings" in conn._cursor._last_sql
        assert conn._cursor._last_params == ("u1", "000001")
        assert conn._committed is True


class TestClearHoldings:
    def test_clear_holdings_executes(self, mock_db):
        from db.holdings import clear_holdings

        stored_conn, stored_results = mock_db
        clear_holdings("u1")
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "DELETE FROM holdings" in conn._cursor._last_sql
        assert conn._cursor._last_params == ("u1",)
        assert conn._committed is True


class TestWatchlist:
    def test_get_watchlist_returns_codes(self, mock_db):
        from db.holdings import get_watchlist

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = [{"code": "000001"}, {"code": "110022"}]
        result = get_watchlist("u1")
        assert result == ["000001", "110022"]

    def test_get_watchlist_empty(self, mock_db):
        from db.holdings import get_watchlist

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = []
        result = get_watchlist("u1")
        assert result == []

    def test_add_to_watchlist_executes(self, mock_db):
        from db.holdings import add_to_watchlist

        stored_conn, stored_results = mock_db
        add_to_watchlist("u1", "000001")
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "INSERT INTO watchlist" in conn._cursor._last_sql
        assert conn._cursor._last_params == ("u1", "000001")
        assert conn._committed is True

    def test_remove_from_watchlist_executes(self, mock_db):
        from db.holdings import remove_from_watchlist

        stored_conn, stored_results = mock_db
        remove_from_watchlist("u1", "000001")
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "DELETE FROM watchlist" in conn._cursor._last_sql
        assert conn._cursor._last_params == ("u1", "000001")
        assert conn._committed is True


class TestConfig:
    def test_get_config_returns_config(self, mock_db):
        from db.holdings import get_config

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = [{"config": {"theme": "dark"}}]
        result = get_config("u1")
        assert result is not None
        assert result["theme"] == "dark"

    def test_get_config_returns_none(self, mock_db):
        from db.holdings import get_config

        stored_conn, stored_results = mock_db
        stored_results["cursor_results"] = []
        result = get_config("u1")
        assert result is None

    def test_save_config_executes(self, mock_db):
        from db.holdings import save_config

        stored_conn, stored_results = mock_db
        config = {"theme": "light", "notifications": True}
        save_config("u1", config)
        conn = stored_conn["current"]
        assert conn._cursor._last_sql is not None
        assert "INSERT INTO config" in conn._cursor._last_sql
        assert conn._cursor._last_params[0] == "u1"
        import json

        assert json.loads(conn._cursor._last_params[1]) == config
        assert conn._committed is True
