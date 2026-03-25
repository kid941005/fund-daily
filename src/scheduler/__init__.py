"""
Scheduler Module

APScheduler-based scheduled task management with Redis persistence
and cluster support via distributed locks.
"""

from .manager import SchedulerManager, get_scheduler_manager

__all__ = ["SchedulerManager", "get_scheduler_manager"]
__version__ = "1.0.0"
