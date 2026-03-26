"""
Scheduler Manager

APScheduler wrapper with Redis persistence, distributed locking for
cluster deployments, and integration with the background task system.
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    EVENT_JOB_SUBMITTED,
)
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from .config import DEFAULT_TIMEZONE, SchedulerConfig, get_scheduler_config
from .jobs import (
    SCHEDULED_JOBS,
    get_scheduled_job,
    list_scheduled_jobs,
)

logger = logging.getLogger(__name__)


class DistributedLock:
    """
    Redis-based distributed lock for cluster deployments.

    Ensures only one scheduler instance runs a particular job at a time.
    """

    def __init__(
        self,
        redis_host: str,
        redis_port: int,
        redis_db: int,
        redis_password: Optional[str] = None,
        lock_ttl: int = 300,
    ):
        self._redis_host = redis_host
        self._redis_port = redis_port
        self._redis_db = redis_db
        self._redis_password = redis_password
        self._lock_ttl = lock_ttl
        self._redis = None
        self._local = threading.local()

    def _get_redis(self):
        """Get thread-local Redis connection"""
        if not hasattr(self._local, "redis") or self._local.redis is None:
            import redis as redis_lib

            self._local.redis = redis_lib.Redis(
                host=self._redis_host,
                port=self._redis_port,
                db=self._redis_db,
                password=self._redis_password,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
        return self._local.redis

    def acquire(self, job_id: str, instance_id: str) -> bool:
        """
        Acquire lock for a job.

        Returns True if lock was acquired, False if another instance holds it.
        """
        lock_key = f"apscheduler:lock:{job_id}"
        redis = self._get_redis()

        try:
            # Use SET NX with TTL
            acquired = redis.set(
                lock_key,
                instance_id,
                nx=True,
                ex=self._lock_ttl,
            )
            return bool(acquired)
        except Exception as e:
            logger.error(f"[Scheduler] Lock acquire failed: {e}")
            return False  # Fail safe - don't run if we can't confirm we have the lock

    def release(self, job_id: str, instance_id: str) -> bool:
        """Release lock if we own it"""
        lock_key = f"apscheduler:lock:{job_id}"
        redis = self._get_redis()

        try:
            # Only release if we own the lock
            current = redis.get(lock_key)
            if current == instance_id:
                redis.delete(lock_key)
                return True
            return False
        except Exception as e:
            logger.warning(f"[Scheduler] Lock release failed: {e}")
            return False

    def is_locked(self, job_id: str) -> bool:
        """Check if a job is currently locked"""
        lock_key = f"apscheduler:lock:{job_id}"
        try:
            redis = self._get_redis()
            return redis.exists(lock_key) > 0
        except Exception:
            return False


class SchedulerManager:
    """
    APScheduler Manager (Singleton)

    Features:
    - Redis job store for persistence
    - Distributed locks for cluster mode
    - Event listeners for monitoring
    - Job execution tracking
    - Background task system integration
    """

    _instance: Optional["SchedulerManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """Initialize scheduler manager"""
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._initialized = True
        self._config = config or get_scheduler_config()
        self._scheduler: Optional[BackgroundScheduler] = None
        self._distributed_lock: Optional[DistributedLock] = None
        self._instance_id = self._config.get_instance_id()

        # Job execution tracking
        self._job_stats: Dict[str, Dict[str, Any]] = {}
        self._stats_lock = threading.Lock()

        # Listener references (prevent GC)
        self._listener_refs: List[Any] = []

        # Initialize distributed lock if cluster mode
        if self._config.cluster_enabled:
            self._distributed_lock = DistributedLock(
                redis_host=self._config.redis_host,
                redis_port=self._config.redis_port,
                redis_db=self._config.redis_db,
                redis_password=self._config.redis_password,
                lock_ttl=self._config.lock_ttl,
            )
            logger.info(f"[Scheduler] Cluster mode enabled (instance: {self._instance_id})")
        else:
            logger.info("[Scheduler] Running in single-instance mode")

        # Build job stores and executors
        self._setup_scheduler()

    def _setup_scheduler(self):
        """Create and configure the APScheduler instance"""
        import tzlocal

        # Get local timezone
        try:
            local_tz = tzlocal.get_localzone()
        except Exception:
            local_tz = timezone(timedelta(hours=8))  # Fallback to Shanghai

        # Configure job stores
        jobstores = {
            "default": RedisJobStore(
                db=self._config.redis_db,
                jobs_key="apscheduler:jobs:jobs",
                run_times_key="apscheduler:jobs:run_times",
                host=self._config.redis_host,
                port=self._config.redis_port,
                password=self._config.redis_password,
            )
        }

        # Configure executors
        executors = {
            "default": ThreadPoolExecutor(max_workers=5),
            "processpool": ProcessPoolExecutor(max_workers=3),
        }

        # Configure job defaults
        job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 60,
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=str(local_tz),
        )

        # Register event listeners
        self._register_listeners()

    def _register_listeners(self):
        """Register APScheduler event listeners"""

        # Job executed successfully
        def on_job_executed(event):
            job_id = event.job_id
            duration_ms = (event.scheduled_run_time and event.retval) and 0 or 0
            if event.retval is not None and hasattr(event.retval, "total_seconds"):
                duration_ms = event.retval.total_seconds() * 1000

            with self._stats_lock:
                stats = self._job_stats.get(job_id, {"runs": 0, "successes": 0, "errors": 0, "durations": []})
                stats["runs"] = stats.get("runs", 0) + 1
                stats["successes"] = stats.get("successes", 0) + 1
                if hasattr(event, "scheduled_run_time"):
                    stats["last_run"] = event.scheduled_run_time
                self._job_stats[job_id] = stats

            logger.info(f"✅ [Scheduler] Job {job_id} executed successfully")

        # Job raised an exception
        def on_job_error(event):
            job_id = event.job_id
            exception = event.exception if hasattr(event, "exception") else "Unknown"

            with self._stats_lock:
                stats = self._job_stats.get(job_id, {"runs": 0, "successes": 0, "errors": 0, "durations": []})
                stats["runs"] = stats.get("runs", 0) + 1
                stats["errors"] = stats.get("errors", 0) + 1
                stats["last_error"] = str(exception)
                if hasattr(event, "scheduled_run_time"):
                    stats["last_run"] = event.scheduled_run_time
                self._job_stats[job_id] = stats

            logger.error(f"❌ [Scheduler] Job {job_id} failed: {exception}")
            self._notify_job_failure(job_id, exception)

        # Job submission (for distributed lock management)
        def on_job_submitted(event):
            if self._distributed_lock:
                job_id = event.job_id
                acquired = self._distributed_lock.acquire(job_id, self._instance_id)
                if not acquired:
                    logger.warning(f"[Scheduler] Job {job_id} skipped (locked by another instance)")
                    # Remove job to prevent execution
                    try:
                        self._scheduler.remove_job(job_id)
                    except Exception:
                        pass

        # Job missed
        def on_job_missed(event):
            job_id = event.job_id
            logger.warning(f"⚠️ [Scheduler] Job {job_id} missed its scheduled run")

        # Store references to prevent GC
        self._listener_refs = [
            self._scheduler.add_listener(on_job_executed, EVENT_JOB_EXECUTED),
            self._scheduler.add_listener(on_job_error, EVENT_JOB_ERROR),
            self._scheduler.add_listener(on_job_submitted, EVENT_JOB_SUBMITTED),
            self._scheduler.add_listener(on_job_missed, EVENT_JOB_MISSED),
        ]

    def _notify_job_failure(self, job_id: str, error: str):
        """Send notification when a job fails"""
        import os

        try:
            feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL")
            if feishu_webhook:
                import requests

                message = {"msg_type": "text", "content": {"text": f"⚠️ [Scheduler] Job {job_id} failed:\n{error}"}}
                requests.post(feishu_webhook, json=message, timeout=5)
        except Exception:
            pass

    # ---- Public API ----

    def start(self):
        """Start the scheduler"""
        if self._scheduler is None:
            self._setup_scheduler()

        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("🚀 [Scheduler] Scheduler started")

            # Add predefined jobs
            self._add_predefined_jobs()

    def stop(self, wait: bool = True):
        """Stop the scheduler"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("⏹️ [Scheduler] Scheduler stopped")

    def pause(self):
        """Pause all job scheduling"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.pause()
            logger.info("⏸️ [Scheduler] Scheduler paused")

    def resume(self):
        """Resume job scheduling"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.resume()
            logger.info("▶️ [Scheduler] Scheduler resumed")

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._scheduler is not None and self._scheduler.running

    @property
    def instance_id(self) -> str:
        """Get this scheduler instance's ID"""
        return self._instance_id

    # ---- Job Management ----

    def add_job(
        self,
        job_id: str,
        func: Callable,
        trigger: str = "cron",
        name: str = None,
        **trigger_args,
    ) -> bool:
        """
        Add a scheduled job

        Args:
            job_id: Unique job identifier
            func: Callable to execute
            trigger: Trigger type ('date', 'interval', 'cron')
            name: Human-readable job name
            **trigger_args: Trigger-specific arguments

        Returns:
            True if job was added, False otherwise
        """
        if self._scheduler is None:
            logger.error("[Scheduler] Scheduler not initialized")
            return False

        try:
            # Build trigger kwargs
            trigger_kwargs = {}
            if trigger == "cron":
                for field in ["year", "month", "day", "week", "day_of_week", "hour", "minute", "second"]:
                    if field in trigger_args:
                        trigger_kwargs[field] = trigger_args.pop(field)
                from apscheduler.triggers.cron import CronTrigger

                trigger_obj = CronTrigger(**trigger_kwargs)
            elif trigger == "interval":
                for field in ["weeks", "days", "hours", "minutes", "seconds", "start_date", "end_date"]:
                    if field in trigger_args:
                        trigger_kwargs[field] = trigger_args.pop(field)
                from apscheduler.triggers.interval import IntervalTrigger

                trigger_obj = IntervalTrigger(**trigger_kwargs)
            elif trigger == "date":
                from apscheduler.triggers.date import DateTrigger

                trigger_obj = DateTrigger(run_date=trigger_args.get("run_date"))
            else:
                logger.error(f"[Scheduler] Unknown trigger type: {trigger}")
                return False

            # Add the job
            self._scheduler.add_job(
                func,
                trigger_obj,
                id=job_id,
                name=name or job_id,
                replace=True,
                **trigger_args,
            )

            logger.info(f"📋 [Scheduler] Job added: {job_id} (trigger: {trigger})")
            return True

        except Exception as e:
            logger.error(f"❌ [Scheduler] Failed to add job {job_id}: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID"""
        if self._scheduler is None:
            return False

        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"🗑️ [Scheduler] Job removed: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to remove job {job_id}: {e}")
            return False

    def get_jobs(self) -> List[Any]:
        """Get list of all scheduled jobs"""
        if self._scheduler is None:
            return []
        return self._scheduler.get_jobs()

    def get_job(self, job_id: str) -> Optional[Any]:
        """Get a specific job by ID"""
        if self._scheduler is None:
            return None
        try:
            return self._scheduler.get_job(job_id)
        except Exception:
            return None

    def run_job_now(self, job_id: str) -> Dict[str, Any]:
        """
        Trigger a job to run immediately.

        Args:
            job_id: Job identifier

        Returns:
            Dict with 'success', 'message', and 'triggered_at' keys
        """
        job = self.get_job(job_id)
        if job is None:
            return {
                "success": False,
                "message": f"Job not found: {job_id}",
                "triggered_at": datetime.now(),
            }

        # Check distributed lock
        if self._distributed_lock:
            if self._distributed_lock.is_locked(job_id):
                return {
                    "success": False,
                    "message": f"Job {job_id} is locked by another instance",
                    "triggered_at": datetime.now(),
                }
            self._distributed_lock.acquire(job_id, self._instance_id)

        try:
            # Get the job's callable and call it directly
            func = job.func
            from functools import partial

            if isinstance(func, partial):
                func = func.func

            # Run async function or regular function
            import asyncio

            try:
                # 使用 get_running_loop() 检查是否有运行中的事件循环
                # 而不是 get_event_loop()（可能在没有循环时创建新的）
                try:
                    loop = asyncio.get_running_loop()
                    # 已有运行中的循环，在其中创建任务
                    asyncio.create_task(self._run_job_async(func, job_id))
                    triggered = True
                except RuntimeError:
                    # 没有运行中的循环，创建一个新的来运行协程
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        triggered = loop.run_until_complete(self._run_job_async(func, job_id))
                    finally:
                        loop.close()
            except Exception as e:
                logger.error(f"❌ [Scheduler] Failed to run job {job_id}: {e}")
                return {
                    "success": False,
                    "message": str(e),
                    "triggered_at": datetime.now(),
                }

            return {
                "success": True,
                "message": f"Job {job_id} triggered",
                "triggered_at": datetime.now(),
                "result": triggered,
            }

        except Exception as e:
            logger.error(f"❌ [Scheduler] Failed to run job {job_id}: {e}")
            return {
                "success": False,
                "message": str(e),
                "triggered_at": datetime.now(),
            }

    async def _run_job_async(self, func, job_id: str):
        """Run a job function asynchronously"""
        try:
            if callable(func) and hasattr(func, "__wrapped__"):
                # Check if it's an async function
                import asyncio

                result = await func()
                return result
            else:
                return func()
        except Exception as e:
            logger.error(f"❌ [Scheduler] Job {job_id} execution error: {e}")
            raise

    def pause_job(self, job_id: str) -> bool:
        """Pause a specific job"""
        if self._scheduler is None:
            return False
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"⏸️ [Scheduler] Job paused: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        if self._scheduler is None:
            return False
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"▶️ [Scheduler] Job resumed: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to resume job {job_id}: {e}")
            return False

    def reschedule_job(self, job_id: str, **trigger_args) -> bool:
        """Reschedule a job with new trigger arguments"""
        job = self.get_job(job_id)
        if job is None:
            return False

        try:
            trigger_type = trigger_args.pop("trigger_type", "cron")

            if trigger_type == "cron":
                from apscheduler.triggers.cron import CronTrigger

                trigger_obj = CronTrigger(**trigger_args)
            elif trigger_type == "interval":
                from apscheduler.triggers.interval import IntervalTrigger

                trigger_obj = IntervalTrigger(**trigger_args)
            elif trigger_type == "date":
                from apscheduler.triggers.date import DateTrigger

                trigger_obj = DateTrigger(run_date=trigger_args.get("run_date"))
            else:
                return False

            job.reschedule(trigger_obj)
            logger.info(f"🔄 [Scheduler] Job rescheduled: {job_id}")
            return True

        except Exception as e:
            logger.error(f"❌ [Scheduler] Failed to reschedule job {job_id}: {e}")
            return False

    # ---- Predefined Jobs ----

    def _add_predefined_jobs(self):
        """Add all predefined scheduled jobs from the registry"""
        import asyncio

        for job_id, meta in SCHEDULED_JOBS.items():
            if not meta.enabled:
                logger.info(f"[Scheduler] Skipping disabled job: {job_id}")
                continue

            try:
                # Import the function
                import importlib

                module_path, func_name = meta.func_ref.rsplit(".", 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)

                # Build trigger
                if meta.trigger_type == "cron":
                    from apscheduler.triggers.cron import CronTrigger

                    trigger_obj = CronTrigger(**meta.trigger_args)
                elif meta.trigger_type == "interval":
                    from apscheduler.triggers.interval import IntervalTrigger

                    trigger_obj = IntervalTrigger(**meta.trigger_args)
                else:
                    logger.warning(f"[Scheduler] Unknown trigger for {job_id}: {meta.trigger_type}")
                    continue

                self._scheduler.add_job(
                    func,
                    trigger_obj,
                    id=job_id,
                    name=meta.name,
                    replace=True,
                    misfire_grace_time=meta.misfire_grace_time,
                    max_instances=meta.max_instances,
                    coalesce=meta.coalesce,
                )

                logger.info(f"📋 [Scheduler] Registered job: {job_id} ({meta.name})")

            except Exception as e:
                logger.error(f"❌ [Scheduler] Failed to register job {job_id}: {e}")

    # ---- Stats ----

    def get_job_stats(self, job_id: str) -> Dict[str, Any]:
        """Get execution stats for a job"""
        with self._stats_lock:
            return dict(self._job_stats.get(job_id, {}))

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all jobs"""
        with self._stats_lock:
            return {k: dict(v) for k, v in self._job_stats.items()}


# ---- Singleton Accessor ----

_scheduler_manager: Optional[SchedulerManager] = None


def get_scheduler_manager() -> SchedulerManager:
    """Get the singleton scheduler manager instance"""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager
