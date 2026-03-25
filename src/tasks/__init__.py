"""
Fund Daily Background Tasks Module

Provides async background task processing with:
- Task persistence in Redis
- Progress tracking
- Task cancellation
- Concurrent task limiting
"""

from .background import (
    BackgroundTaskManager,
    TaskInfo,
    TaskStatus,
    TaskType,
)
from .task_registry import TaskRegistry, register_task

__all__ = [
    "BackgroundTaskManager",
    "TaskInfo",
    "TaskStatus",
    "TaskType",
    "TaskRegistry",
    "register_task",
]
