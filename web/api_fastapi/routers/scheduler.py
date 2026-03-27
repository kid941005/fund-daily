"""
FastAPI Scheduler Router

REST API endpoints for managing scheduled jobs.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.scheduler.api import (
    JobPauseResponse,
    JobRescheduleRequest,
    JobRescheduleResponse,
    JobResponse,
    JobResumeResponse,
    JobRunRequest,
    JobRunResponse,
    SchedulerJobsListResponse,
    SchedulerStatusResponse,
    jobs_to_response,
)
from src.scheduler.manager import get_scheduler_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scheduler", tags=["调度器"])


def _get_manager():
    """Get scheduler manager instance"""
    return get_scheduler_manager()


def _get_current_time():
    """Get current time with timezone"""
    return datetime.now(timezone.utc).astimezone()


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """
    Get scheduler status

    Returns the current running state, timezone, and instance information.
    """
    manager = _get_manager()

    return SchedulerStatusResponse(
        running=manager.is_running(),
        current_time=_get_current_time(),
        timezone="Asia/Shanghai",
        instance_id=manager.instance_id,
        cluster_enabled=manager._config.cluster_enabled if hasattr(manager, "_config") else False,
        pending_jobs=len(manager.get_jobs()),
    )


@router.get("/jobs", response_model=SchedulerJobsListResponse)
async def list_jobs(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
):
    """
    List all scheduled jobs

    Returns all registered scheduled jobs with their current status and next run times.
    """
    manager = _get_manager()
    jobs = manager.get_jobs()

    if job_id:
        jobs = [j for j in jobs if j.id == job_id]

    return jobs_to_response(jobs, manager.is_running(), _get_current_time())


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get details for a specific job

    - **job_id**: The unique job identifier
    """
    manager = _get_manager()
    job = manager.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    from src.scheduler.api import JobState, _extract_trigger_args

    jobs_list = [job]
    response = jobs_to_response(jobs_list, manager.is_running(), _get_current_time())

    if not response.jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return response.jobs[0]


@router.post("/jobs/{job_id}/run", response_model=JobRunResponse)
async def run_job(job_id: str, request: JobRunRequest = None):
    """
    Trigger a job to run immediately

    - **job_id**: The job identifier to run
    - **force**: Force execution even if disabled (default: False)
    """
    manager = _get_manager()

    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    result = manager.run_job_now(job_id)

    if result["success"]:
        return JobRunResponse(
            job_id=job_id,
            success=True,
            message=result.get("message", "Job triggered"),
            triggered_at=result.get("triggered_at", _get_current_time()),
        )
    else:
        raise HTTPException(
            status_code=409,
            detail={
                "job_id": job_id,
                "success": False,
                "message": result.get("message", "Job run failed"),
            },
        )


@router.post("/jobs/{job_id}/pause", response_model=JobPauseResponse)
async def pause_job(job_id: str):
    """
    Pause a scheduled job

    Paused jobs will not execute at their next scheduled time.

    - **job_id**: The job identifier to pause
    """
    manager = _get_manager()

    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    success = manager.pause_job(job_id)

    if success:
        return JobPauseResponse(job_id=job_id, success=True, message=f"Job {job_id} paused")
    else:
        raise HTTPException(status_code=500, detail=f"Failed to pause job {job_id}")


@router.post("/jobs/{job_id}/resume", response_model=JobResumeResponse)
async def resume_job(job_id: str):
    """
    Resume a paused job

    - **job_id**: The job identifier to resume
    """
    manager = _get_manager()

    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    success = manager.resume_job(job_id)

    if success:
        return JobResumeResponse(job_id=job_id, success=True, message=f"Job {job_id} resumed")
    else:
        raise HTTPException(status_code=500, detail=f"Failed to resume job {job_id}")


@router.post("/jobs/{job_id}/reschedule", response_model=JobRescheduleResponse)
async def reschedule_job(job_id: str, request: JobRescheduleRequest):
    """
    Reschedule a job with new trigger parameters

    - **job_id**: The job identifier to reschedule
    - **trigger**: New trigger type ('date', 'interval', 'cron')
    - **...**: Trigger-specific parameters
    """
    manager = _get_manager()

    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Build trigger args dict
    trigger_args = _build_trigger_args(request)
    if not trigger_args:
        raise HTTPException(status_code=400, detail="Invalid trigger parameters")

    # Include trigger type
    trigger_type = request.trigger or "cron"
    trigger_args["trigger_type"] = trigger_type

    success = manager.reschedule_job(job_id, **trigger_args)

    if success:
        updated_job = manager.get_job(job_id)
        next_run = updated_job.next_run_time if updated_job else None

        return JobRescheduleResponse(
            job_id=job_id,
            success=True,
            message=f"Job {job_id} rescheduled",
            next_run_time=next_run,
        )
    else:
        raise HTTPException(status_code=500, detail=f"Failed to reschedule job {job_id}")


@router.delete("/jobs/{job_id}")
async def remove_job(job_id: str):
    """
    Remove a scheduled job

    - **job_id**: The job identifier to remove
    """
    manager = _get_manager()

    success = manager.remove_job(job_id)

    if success:
        return {"success": True, "message": f"Job {job_id} removed"}
    else:
        raise HTTPException(status_code=404, detail=f"Job not found or could not be removed: {job_id}")


@router.get("/jobs/{job_id}/stats")
async def get_job_stats(job_id: str):
    """
    Get execution statistics for a job

    - **job_id**: The job identifier
    """
    manager = _get_manager()

    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    stats = manager.get_job_stats(job_id)

    return {
        "job_id": job_id,
        "stats": stats,
    }


@router.post("/start")
async def start_scheduler():
    """
    Start the scheduler

    Note: The scheduler is typically started automatically when the
    application starts. This endpoint is for manual control.
    """
    manager = _get_manager()

    if manager.is_running():
        return {"success": True, "message": "Scheduler already running"}

    manager.start()
    return {"success": True, "message": "Scheduler started"}


@router.post("/stop")
async def stop_scheduler():
    """
    Stop the scheduler

    Note: This will stop all scheduled jobs until start is called.
    """
    manager = _get_manager()

    if not manager.is_running():
        return {"success": True, "message": "Scheduler already stopped"}

    manager.stop()
    return {"success": True, "message": "Scheduler stopped"}


# ---- Helper ----


def _build_trigger_args(request: JobRescheduleRequest) -> dict:
    """Build trigger args dict from request model"""
    args = {}

    # Cron fields
    for field in ["year", "month", "day", "week", "day_of_week", "hour", "minute", "second"]:
        val = getattr(request, field, None)
        if val is not None:
            args[field] = val

    # Date trigger
    if request.run_date:
        args["run_date"] = request.run_date

    # Interval fields
    for field in ["weeks", "days", "hours", "minutes", "seconds"]:
        val = getattr(request, field, None)
        if val is not None:
            args[field] = val

    if request.start_date:
        args["start_date"] = request.start_date
    if request.end_date:
        args["end_date"] = request.end_date

    return args
