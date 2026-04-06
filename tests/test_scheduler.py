"""
Tests for Scheduler Module

Tests for APScheduler-based scheduled task management.
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSchedulerConfig:
    """Tests for SchedulerConfig"""

    def test_config_from_env_defaults(self):
        """Test default config values"""
        # Clear env vars
        env_backup = {
            k: os.environ.pop(k, None)
            for k in list(os.environ.keys())
            if k.startswith("SCHEDULER_") or k.startswith("REDIS_")
        }
        try:
            from src.scheduler.config import SchedulerConfig

            config = SchedulerConfig()
            assert config.timezone == "Asia/Shanghai"
            assert config.cluster_enabled is True
            assert config.lock_ttl == 300
            assert config.redis_host == "localhost"
            assert config.redis_port == 6379
            assert config.redis_db == 1
        finally:
            # Restore env
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v

    def test_config_from_env_override(self):
        """Test config from environment variables"""
        os.environ["SCHEDULER_CLUSTER_ENABLED"] = "false"
        os.environ["SCHEDULER_LOCK_TTL"] = "600"
        os.environ["REDIS_HOST"] = "redis.example.com"
        os.environ["REDIS_PORT"] = "6380"
        os.environ["REDIS_DB"] = "2"
        try:
            from src.scheduler.config import SchedulerConfig

            config = SchedulerConfig.from_env()
            assert config.cluster_enabled is False
            assert config.lock_ttl == 600
            assert config.redis_host == "redis.example.com"
            assert config.redis_port == 6380
            assert config.redis_db == 2
        finally:
            os.environ.pop("SCHEDULER_CLUSTER_ENABLED", None)
            os.environ.pop("SCHEDULER_LOCK_TTL", None)
            os.environ.pop("REDIS_HOST", None)
            os.environ.pop("REDIS_PORT", None)
            os.environ.pop("REDIS_DB", None)

    def test_get_instance_id(self):
        """Test instance ID generation"""
        from src.scheduler.config import SchedulerConfig

        config = SchedulerConfig()
        instance_id = config.get_instance_id()
        assert instance_id is not None
        assert isinstance(instance_id, str)
        assert len(instance_id) > 0

        # Should be consistent within same instance
        assert config.get_instance_id() == instance_id


class TestJobMetadata:
    """Tests for job metadata and registry"""

    def test_scheduled_jobs_registered(self):
        """Test that predefined jobs are registered"""
        from src.scheduler.jobs import (
            SCHEDULED_JOBS,
        )

        assert len(SCHEDULED_JOBS) > 0, "Expected at least one predefined job"

        # Check all expected jobs exist
        expected_jobs = [
            "daily_nav_update",
            "weekly_score_calculation",
            "market_open_reminder",
            "cache_warmup",
            "cleanup_old_data",
            "fund_data_fetch",
        ]
        for job_id in expected_jobs:
            assert job_id in SCHEDULED_JOBS, f"Expected job {job_id} to be registered"

    def test_job_metadata_fields(self):
        """Test job metadata has required fields"""
        from src.scheduler.jobs import get_scheduled_job

        job = get_scheduled_job("daily_nav_update")
        assert job is not None
        assert job.job_id == "daily_nav_update"
        assert job.name == "每日净值更新"
        assert job.trigger_type in ("cron", "interval", "date")
        assert job.enabled is True
        assert job.func_ref is not None
        assert isinstance(job.max_instances, int)

    def test_list_scheduled_jobs(self):
        """Test listing all scheduled jobs"""
        from src.scheduler.jobs import list_scheduled_jobs

        jobs = list_scheduled_jobs()
        assert isinstance(jobs, dict)
        assert len(jobs) > 0
        for job_id, meta in jobs.items():
            assert job_id == meta.job_id
            assert meta.name is not None
            assert meta.trigger_type is not None

    def test_get_job_trigger_args(self):
        """Test getting trigger arguments for a job"""
        from src.scheduler.jobs import get_scheduled_job

        nav_job = get_scheduled_job("daily_nav_update")
        assert nav_job is not None
        assert "hour" in nav_job.trigger_args or "minute" in nav_job.trigger_args

        cache_job = get_scheduled_job("cache_warmup")
        assert cache_job is not None
        assert cache_job.trigger_type == "interval"


class TestDistributedLock:
    """Tests for distributed lock functionality"""

    def test_lock_key_format(self):
        """Test that lock keys are properly formatted"""
        from src.scheduler.config import LOCK_KEY_PREFIX

        assert LOCK_KEY_PREFIX == "apscheduler:lock:"
        assert LOCK_KEY_PREFIX.endswith(":")


class TestSchedulerManagerUnit:
    """Unit tests for SchedulerManager without real Redis"""

    def test_manager_singleton(self):
        """Test SchedulerManager is a singleton"""
        from src.scheduler.manager import SchedulerManager

        # Reset singleton
        SchedulerManager._instance = None

        with patch("src.scheduler.manager.RedisJobStore"):
            with patch("src.scheduler.manager.BackgroundScheduler"):
                with patch("src.scheduler.manager.DistributedLock"):
                    manager1 = SchedulerManager()
                    manager2 = SchedulerManager()
                    assert manager1 is manager2

        # Cleanup
        SchedulerManager._instance = None

    def test_manager_initialization(self):
        """Test manager initializes correctly"""
        from src.scheduler.config import SchedulerConfig
        from src.scheduler.manager import SchedulerManager

        SchedulerManager._instance = None

        with patch("src.scheduler.manager.RedisJobStore"):
            with patch("src.scheduler.manager.BackgroundScheduler"):
                with patch("src.scheduler.manager.DistributedLock"):
                    config = SchedulerConfig(cluster_enabled=False)
                    manager = SchedulerManager(config=config)

                    assert manager._config is config
                    assert manager._instance_id == config.get_instance_id()

        SchedulerManager._instance = None

    def test_is_running_state(self):
        """Test is_running reflects scheduler state"""
        from src.scheduler.config import SchedulerConfig
        from src.scheduler.manager import SchedulerManager

        SchedulerManager._instance = None

        mock_scheduler = MagicMock()
        mock_scheduler.running = False

        with patch("src.scheduler.manager.RedisJobStore"):
            with patch("src.scheduler.manager.BackgroundScheduler", return_value=mock_scheduler):
                with patch("src.scheduler.manager.DistributedLock"):
                    config = SchedulerConfig(cluster_enabled=False)
                    manager = SchedulerManager(config=config)

                    assert manager.is_running() is False

                    mock_scheduler.running = True
                    assert manager.is_running() is True

        SchedulerManager._instance = None


class TestSchedulerAPI:
    """Tests for scheduler API models"""

    def test_job_response_model(self):
        """Test JobResponse model creation"""
        from src.scheduler.api import JobResponse, JobState

        job = JobResponse(
            id="test_job",
            name="Test Job",
            trigger="cron",
            state=JobState.PENDING,
        )
        assert job.id == "test_job"
        assert job.name == "Test Job"
        assert job.state == JobState.PENDING

    def test_trigger_type_enum(self):
        """Test TriggerType enum"""
        from src.scheduler.api import TriggerType

        assert TriggerType.DATE == "date"
        assert TriggerType.INTERVAL == "interval"
        assert TriggerType.CRON == "cron"

    def test_extract_trigger_args(self):
        """Test extracting trigger arguments"""
        from src.scheduler.api import _extract_trigger_args

        # Test cron trigger args
        mock_cron = MagicMock()
        mock_cron.type = "cron"
        mock_cron.hour = "16"
        mock_cron.minute = "0"
        mock_cron.day_of_week = "mon-fri"
        mock_cron.year = None
        mock_cron.month = None
        mock_cron.day = None
        mock_cron.week = None
        mock_cron.second = None

        args = _extract_trigger_args(mock_cron)
        assert args["type"] == "cron"
        assert args["hour"] == "16"
        assert args["minute"] == "0"
        assert args["day_of_week"] == "mon-fri"

    def test_extract_trigger_args_interval(self):
        """Test extracting interval trigger arguments"""
        from src.scheduler.api import _extract_trigger_args

        mock_interval = MagicMock()
        mock_interval.type = "interval"
        mock_interval.minutes = 30
        mock_interval.hours = None
        mock_interval.days = None
        mock_interval.weeks = None
        mock_interval.seconds = None
        mock_interval.start_date = None
        mock_interval.end_date = None

        args = _extract_trigger_args(mock_interval)
        assert args["type"] == "interval"
        assert args["minutes"] == 30

    def test_jobs_to_response(self):
        """Test jobs list to response conversion"""
        from datetime import timezone

        from src.scheduler.api import jobs_to_response

        mock_job = MagicMock()
        mock_job.id = "test_job"
        mock_job.name = "Test Job"
        mock_job.trigger.type = "cron"
        mock_job.trigger.hour = "16"
        mock_job.trigger.minute = "0"
        mock_job.trigger.day_of_week = "mon-fri"
        mock_job.trigger.year = None
        mock_job.trigger.month = None
        mock_job.trigger.day = None
        mock_job.trigger.week = None
        mock_job.trigger.second = None
        mock_job.next_run_time = None
        mock_job.pending = False
        mock_job.misfire_grace_time = 60
        mock_job.max_instances = 1
        mock_job.coalesce = True
        mock_job.func_ref = "test_func"
        mock_job.kwargs = {}

        current_time = datetime.now(timezone.utc)
        response = jobs_to_response([mock_job], running=True, current_time=current_time)

        assert response.running is True
        assert response.total == 1
        assert len(response.jobs) == 1
        assert response.jobs[0].id == "test_job"
        assert response.jobs[0].trigger == "cron"

    def test_reschedule_request_model(self):
        """Test JobRescheduleRequest model"""
        from src.scheduler.api import JobRescheduleRequest

        # Cron request
        req = JobRescheduleRequest(
            trigger="cron",
            hour="10",
            minute="30",
            day_of_week="mon-fri",
        )
        assert req.trigger == "cron"
        assert req.hour == "10"
        assert req.minute == "30"

        # Interval request
        req2 = JobRescheduleRequest(
            trigger="interval",
            hours=2,
        )
        assert req2.trigger == "interval"
        assert req2.hours == 2

    def test_scheduler_status_response(self):
        """Test SchedulerStatusResponse model"""
        from datetime import timezone

        from src.scheduler.api import SchedulerStatusResponse

        now = datetime.now(timezone.utc)
        response = SchedulerStatusResponse(
            running=True,
            current_time=now,
            timezone="Asia/Shanghai",
            instance_id="test-host:12345",
            cluster_enabled=True,
            pending_jobs=5,
        )
        assert response.running is True
        assert response.timezone == "Asia/Shanghai"
        assert response.cluster_enabled is True


class TestScheduledJobFunctions:
    """Tests for individual scheduled job functions"""

    def test_is_trading_day(self):
        """Test trading day detection"""
        from src.scheduler.jobs import _is_trading_day

        # Note: This may pass or fail depending on current day
        # Just verify it returns a boolean
        result = _is_trading_day()
        assert isinstance(result, bool)

    def test_get_fund_codes(self):
        """Test fund code retrieval"""
        from src.scheduler.jobs import _get_fund_codes

        # Should return a list (possibly empty)
        codes = _get_fund_codes()
        assert isinstance(codes, list)

    def test_send_market_reminder_no_webhook(self):
        """Test market reminder without webhook configured"""
        from src.scheduler.jobs import _send_market_reminder

        # Remove webhook if set
        old_webhook = os.environ.pop("FEISHU_WEBHOOK_URL", None)
        try:
            # Should not raise, just return None
            _send_market_reminder()
        finally:
            if old_webhook:
                os.environ["FEISHU_WEBHOOK_URL"] = old_webhook

    def test_daily_nav_update_returns_dict(self):
        """Test daily_nav_update returns expected dict structure"""
        import asyncio

        from src.scheduler.jobs import daily_nav_update

        # Mock inside the function where it's imported (BackgroundTaskManager is imported locally)
        with patch("src.tasks.background.BackgroundTaskManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.submit.return_value = "test-task-id"
            mock_manager_class.get_instance.return_value = mock_manager

            with patch("src.scheduler.jobs._get_fund_codes", return_value=["000001"]):
                result = daily_nav_update()

        assert isinstance(result, dict)
        assert "task_id" in result

    def test_cache_warmup(self):
        """Test cache warmup job"""
        import asyncio

        from src.scheduler.jobs import cache_warmup

        with patch("src.tasks.background.BackgroundTaskManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.submit.return_value = "test-task-id"
            mock_manager_class.get_instance.return_value = mock_manager

            result = cache_warmup()

        assert isinstance(result, dict)
        assert "task_id" in result

    def test_market_open_reminder_not_trading_day(self):
        """Test market open reminder on non-trading day"""
        import asyncio

        from src.scheduler.jobs import market_open_reminder

        with patch("src.scheduler.jobs._is_trading_day", return_value=False):
            result = market_open_reminder()

        assert result.get("skipped") is True

    def test_cleanup_old_data(self):
        """Test cleanup job"""
        import asyncio

        from src.scheduler.jobs import cleanup_old_data

        with patch("src.cache.manager.CacheManager") as mock_cache_mgr:
            mock_instance = MagicMock()
            mock_cache_mgr.get_instance.return_value = mock_instance

            result = cleanup_old_data()

        assert isinstance(result, dict)
        assert "errors" in result


class TestFastAPIRouter:
    """Tests for the FastAPI scheduler router"""

    def test_router_prefix(self):
        """Test router has correct prefix"""
        from web.api_fastapi.routers.scheduler import router

        assert router.prefix == "/api/scheduler"

    def test_router_has_expected_routes(self):
        """Test router has expected route handlers"""
        from web.api_fastapi.routers.scheduler import router

        routes = {r.path for r in router.routes}
        # Router has prefix /api/scheduler, so full paths include it
        # Check at least the main routes exist
        assert "/api/scheduler/jobs" in routes
        assert "/api/scheduler/status" in routes
        assert "/api/scheduler/jobs/{job_id}" in routes
        assert "/api/scheduler/jobs/{job_id}/run" in routes


# ---- Integration Tests (require Redis) ----


class TestSchedulerIntegration:
    """Integration tests that require Redis (skip if unavailable)"""

    @pytest.fixture
    def redis_available(self):
        """Check if Redis is available"""
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, db=1, socket_connect_timeout=2)
            r.ping()
            return True
        except Exception:
            return False

    @pytest.mark.skipif(
        os.environ.get("SKIP_REDIS_TESTS") == "1",
        reason="Redis tests skipped (SKIP_REDIS_TESTS=1)",
    )
    @pytest.mark.skipif(
        not pytest.importorskip("redis", reason="redis-py not installed"),
        reason="redis-py not installed",
    )
    def test_scheduler_manager_with_redis(self, redis_available):
        """Test scheduler manager with real Redis (if available)"""
        if not redis_available:
            pytest.skip("Redis not available")

        from src.scheduler.config import SchedulerConfig
        from src.scheduler.manager import SchedulerManager

        # Reset singleton
        SchedulerManager._instance = None

        config = SchedulerConfig(cluster_enabled=True)
        manager = SchedulerManager(config=config)

        assert manager is not None
        assert manager.instance_id is not None

        # Cleanup
        SchedulerManager._instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
