"""
Task models - 任务相关的数据模型
"""

import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskType(str, Enum):
    """Task type enumeration"""

    FUND_FETCH = "fund_fetch"
    NAV_UPDATE = "nav_update"
    SCORE_CALC = "score_calculation"
    CACHE_WARM = "cache_warmup"
    BATCH_IMPORT = "batch_import"


class TaskStatus(str, Enum):
    """Task status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo(BaseModel):
    """Task information model"""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class TaskContext:
    """Task execution context"""

    def __init__(
        self,
        task_id: str,
        params: dict[str, Any],
        cancel_event: threading.Event,
        update_progress_func: Callable[[float, str], None],
    ):
        self.task_id = task_id
        self.params = params
        self._cancel_event = cancel_event
        self._update_progress = update_progress_func
        self._current_progress = 0.0

    def update_progress(self, progress: float, message: str = "") -> None:
        """Update task progress"""
        self._current_progress = progress
        self._update_progress(progress, message)

    def check_cancelled(self) -> bool:
        """Check if task has been cancelled"""
        return self._cancel_event.is_set()

    @property
    def is_cancelled(self) -> bool:
        """Check if task has been cancelled (alias)"""
        return self.check_cancelled()
