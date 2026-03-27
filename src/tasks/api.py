"""
Task API Module

Provides API models and response helpers for task endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .models import TaskInfo


class TaskResponse(BaseModel):
    """Task API response model"""

    task_id: str
    task_type: str
    status: str
    progress: float = 0.0
    message: str = ""
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def from_task_info(cls, task_info: TaskInfo) -> "TaskResponse":
        """Create response from TaskInfo"""
        return cls(
            task_id=task_info.task_id,
            task_type=task_info.task_type,
            status=task_info.status.value if hasattr(task_info.status, "value") else task_info.status,
            progress=task_info.progress,
            message=task_info.message,
            created_at=task_info.created_at,
            started_at=task_info.started_at,
            completed_at=task_info.completed_at,
            result=task_info.result,
            error=task_info.error,
        )


class TaskListResponse(BaseModel):
    """Task list response model"""

    tasks: List[TaskResponse]
    total: int
    stats: Dict[str, Any]


class TaskSubmitRequest(BaseModel):
    """Task submission request model"""

    task_type: str = Field(..., description="Task type (e.g., 'fund_fetch', 'nav_update')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    user_id: Optional[str] = Field(None, description="User ID for the task")


class TaskSubmitResponse(BaseModel):
    """Task submission response model"""

    task_id: str
    status: str
    message: str


class TaskCancelResponse(BaseModel):
    """Task cancellation response model"""

    task_id: str
    cancelled: bool
    message: str


class TaskStatsResponse(BaseModel):
    """Task statistics response model"""

    total_tasks: int
    running_tasks: int
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    max_concurrent: int


def task_to_response(task_info: TaskInfo) -> TaskResponse:
    """Convert TaskInfo to API response"""
    return TaskResponse.from_task_info(task_info)


def tasks_to_list_response(tasks: List[TaskInfo], stats: Dict[str, Any]) -> TaskListResponse:
    """Convert task list to API response"""
    return TaskListResponse(tasks=[task_to_response(t) for t in tasks], total=len(tasks), stats=stats)
