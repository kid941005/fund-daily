"""
Scheduler Configuration

APScheduler configuration including timezone, job stores, and executors.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import timezone, timedelta

# Default timezone for China market
DEFAULT_TIMEZONE = "Asia/Shanghai"

# Job store Redis key prefix
JOB_STORE_KEY = "apscheduler:jobs"

# Distributed lock key prefix
LOCK_KEY_PREFIX = "apscheduler:lock:"

# Lock TTL in seconds (5 minutes default)
DEFAULT_LOCK_TTL = 300


@dataclass
class SchedulerConfig:
    """
    APScheduler Configuration

    Attributes:
        timezone: Scheduler timezone (default: Asia/Shanghai)
        job_stores: Job store configuration
        executors: Executor configuration
        job_defaults: Default job settings
        misfire_grace_time: Seconds after missed time to still run job
        max_instances: Max concurrent instances of same job
        coalesce: Coalesce missed executions into one
        job_existing: What to do with existing jobs ('replace', 'keep')
        cluster_enabled: Enable distributed lock for cluster deployments
        lock_ttl: Lock TTL in seconds for cluster mode
        redis_host: Redis host (for job store and locks)
        redis_port: Redis port
        redis_db: Redis database number
        redis_password: Redis password (optional)
        instance_id: Unique ID for this instance (for cluster locks)
    """

    # Timezone
    timezone: str = DEFAULT_TIMEZONE

    # Job store persistence
    job_stores: dict = field(
        default_factory=lambda: {
            "default": {
                "type": "redis",
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
                "db": int(os.getenv("REDIS_DB", "1")),  # Use DB 1 for scheduler to avoid conflict
                "password": os.getenv("REDIS_PASSWORD"),
                "key_prefix": JOB_STORE_KEY,
                "jobs_key": f"{JOB_STORE_KEY}:jobs",
                "run_times_key": f"{JOB_STORE_KEY}:run_times",
            }
        }
    )

    # Executors configuration
    executors: dict = field(
        default_factory=lambda: {
            "default": {"type": "threadpool", "max_workers": 5},
            "processpool": {"type": "processpool", "max_workers": 3},
        }
    )

    # Job defaults
    job_defaults: dict = field(
        default_factory=lambda: {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 60,
        }
    )

    # Cluster support
    cluster_enabled: bool = True
    lock_ttl: int = DEFAULT_LOCK_TTL
    instance_id: Optional[str] = None

    # Redis connection settings (used for both job store and locks)
    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "1")))
    redis_password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        """Create config from environment variables"""
        return cls(
            timezone=os.getenv("SCHEDULER_TIMEZONE", DEFAULT_TIMEZONE),
            cluster_enabled=os.getenv("SCHEDULER_CLUSTER_ENABLED", "true").lower() == "true",
            lock_ttl=int(os.getenv("SCHEDULER_LOCK_TTL", str(DEFAULT_LOCK_TTL))),
            instance_id=os.getenv("SCHEDULER_INSTANCE_ID"),
            log_level=os.getenv("SCHEDULER_LOG_LEVEL", "INFO"),
        )

    def get_instance_id(self) -> str:
        """Get unique instance ID for this process"""
        if self.instance_id:
            return self.instance_id
        import socket

        hostname = socket.gethostname()
        pid = os.getpid()
        self.instance_id = f"{hostname}:{pid}"
        return self.instance_id


# Global config instance
_config: Optional[SchedulerConfig] = None


def get_scheduler_config() -> SchedulerConfig:
    """Get or create the global scheduler config"""
    global _config
    if _config is None:
        _config = SchedulerConfig.from_env()
    return _config
