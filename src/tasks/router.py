"""
Task Router Module

FastAPI router for task management endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .api import (
    TaskCancelResponse,
    TaskListResponse,
    TaskResponse,
    TaskStatsResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
    task_to_response,
    tasks_to_list_response,
)
from .background import BackgroundTaskManager, TaskStatus, TaskType

logger = logging.getLogger(__name__)

tasks_router = APIRouter(prefix="/api/tasks", tags=["任务"])


def get_task_manager() -> BackgroundTaskManager:
    """Get task manager instance"""
    return BackgroundTaskManager.get_instance()


@tasks_router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all tasks with optional filters

    - **status**: Filter by task status (pending, running, completed, failed, cancelled)
    - **task_type**: Filter by task type (fund_fetch, nav_update, score_calculation, cache_warmup, batch_import)
    - **limit**: Maximum number of tasks to return
    - **offset**: Number of tasks to skip
    """
    manager = get_task_manager()

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid status: {status}. Valid values: {[s.value for s in TaskStatus]}"
            )

    # Get tasks
    tasks = manager.list_tasks(status=status_filter, task_type=task_type, limit=limit, offset=offset)

    # Get stats
    stats = manager.get_stats()

    return tasks_to_list_response(tasks, stats)


@tasks_router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats():
    """
    Get task statistics

    Returns counts of tasks by status and configuration info.
    """
    manager = get_task_manager()
    stats = manager.get_stats()

    return TaskStatsResponse(**stats)


@tasks_router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """
    Get task information by ID

    - **task_id**: Unique task identifier
    """
    manager = get_task_manager()
    task_info = manager.get_task(task_id)

    if task_info is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return task_to_response(task_info)


@tasks_router.post("/submit", response_model=TaskSubmitResponse)
async def submit_task(request: TaskSubmitRequest):
    """
    Submit a new background task

    - **task_type**: Type of task to submit
        - fund_fetch: Fund data fetching
        - nav_update: NAV update
        - score_calculation: Score calculation
        - cache_warmup: Cache warmup
        - batch_import: Batch import
    - **params**: Task-specific parameters
    - **user_id**: Optional user ID for tracking
    """
    manager = get_task_manager()

    # Validate task type
    valid_types = [t.value for t in TaskType]
    if request.task_type not in valid_types:
        raise HTTPException(
            status_code=400, detail=f"Invalid task type: {request.task_type}. Valid values: {valid_types}"
        )

    # Check concurrent limit
    running_count = manager.get_running_count()
    max_concurrent = manager._max_concurrent

    if running_count >= max_concurrent:
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "error": f"Too many running tasks ({running_count}/{max_concurrent}). Please try again later.",
            },
        )

    # Submit task
    task_id = manager.submit(task_type=request.task_type, params=request.params, user_id=request.user_id)

    return TaskSubmitResponse(task_id=task_id, status="pending", message="Task submitted successfully")


@tasks_router.post("/cancel/{task_id}", response_model=TaskCancelResponse)
async def cancel_task(task_id: str):
    """
    Cancel a running or pending task

    - **task_id**: Task identifier to cancel
    """
    manager = get_task_manager()
    task_info = manager.get_task(task_id)

    if task_info is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # Check if task can be cancelled
    if task_info.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Task cannot be cancelled: status is {task_info.status}")

    # Cancel task
    cancelled = manager.cancel_task(task_id)

    if cancelled:
        return TaskCancelResponse(task_id=task_id, cancelled=True, message="Task cancelled successfully")
    else:
        return TaskCancelResponse(task_id=task_id, cancelled=False, message="Failed to cancel task")


# Import handlers to register them
from . import handlers  # noqa: F401
