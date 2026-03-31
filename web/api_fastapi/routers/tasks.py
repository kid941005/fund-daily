"""
FastAPI Tasks Router

Integrates the background task system with the FastAPI application.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.tasks.api import (
    TaskCancelResponse,
    TaskListResponse,
    TaskResponse,
    TaskStatsResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
    task_to_response,
    tasks_to_list_response,
)
from src.tasks.background import BackgroundTaskManager
from src.tasks.models import TaskStatus, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["任务"])


def get_task_manager() -> BackgroundTaskManager:
    """Get task manager instance"""
    return BackgroundTaskManager.get_instance()


@router.get("", response_model=TaskListResponse)
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


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats():
    """
    Get task statistics

    Returns counts of tasks by status and configuration info.
    """
    manager = get_task_manager()
    stats = manager.get_stats()

    return TaskStatsResponse(**stats)


@router.get("/{task_id}", response_model=TaskResponse)
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


@router.post("/submit", response_model=TaskSubmitResponse)
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


@router.post("/cancel/{task_id}", response_model=TaskCancelResponse)
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


# Fund-specific task endpoints
fund_router = APIRouter(prefix="/api/funds", tags=["基金任务"])


class FundFetchRequest(BaseModel):
    """Fund fetch request model"""

    codes: list[str] = Field(default_factory=list, description="Fund codes to fetch")
    force: bool = Field(False, description="Force refresh, ignore cache")
    user_id: Optional[str] = Field(None, description="User ID")


class ScoreCalculationRequest(BaseModel):
    """Score calculation request model"""

    codes: list[str] = Field(default_factory=list, description="Fund codes")
    force: bool = Field(False, description="Force recalculation")
    user_id: Optional[str] = Field(None, description="User ID")


class CacheWarmupRequest(BaseModel):
    """Cache warmup request model"""

    warmup_type: str = Field("all", description="Type: all, funds, analysis, scores")
    user_id: Optional[str] = Field(None, description="User ID")


@fund_router.post("/fetch", response_model=TaskSubmitResponse)
async def submit_fund_fetch_task(request: FundFetchRequest):
    """
    Submit a fund data fetch task

    Fetches fund data from external sources in the background.

    - **codes**: List of fund codes to fetch (if empty, fetches all user holdings)
    - **force**: Force refresh, ignore cache
    """
    manager = get_task_manager()

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

    task_id = manager.submit(
        task_type=TaskType.FUND_FETCH.value,
        params={"codes": request.codes, "force": request.force},
        user_id=request.user_id,
    )

    return TaskSubmitResponse(task_id=task_id, status="pending", message="Fund fetch task submitted")


@fund_router.post("/scores/calculate", response_model=TaskSubmitResponse)
async def submit_score_calculation_task(request: ScoreCalculationRequest):
    """
    Submit a score calculation task

    Calculates comprehensive scores for funds in the background.

    - **codes**: List of fund codes (if empty, calculates for all user holdings)
    - **force**: Force recalculation, ignore cache
    """
    manager = get_task_manager()

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

    task_id = manager.submit(
        task_type=TaskType.SCORE_CALC.value,
        params={"codes": request.codes, "force": request.force},
        user_id=request.user_id,
    )

    return TaskSubmitResponse(task_id=task_id, status="pending", message="Score calculation task submitted")


@fund_router.post("/cache/warmup", response_model=TaskSubmitResponse)
async def submit_cache_warmup_task(request: CacheWarmupRequest):
    """
    Submit a cache warmup task

    Preloads commonly accessed data into cache.

    - **warmup_type**: Type of data to warmup (all, funds, analysis, scores)
    """
    manager = get_task_manager()

    task_id = manager.submit(
        task_type=TaskType.CACHE_WARM.value, params={"type": request.warmup_type}, user_id=request.user_id
    )

    return TaskSubmitResponse(task_id=task_id, status="pending", message="Cache warmup task submitted")


# Import handlers to register them
from src.tasks import handlers  # noqa: E402,F401
