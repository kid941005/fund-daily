"""
Scheduler API Models

Pydantic models for scheduler API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Job trigger types"""

    DATE = "date"
    INTERVAL = "interval"
    CRON = "cron"


class JobState(str, Enum):
    """Job state"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


# ---- Request Models ----


class JobRescheduleRequest(BaseModel):
    """Request to reschedule a job"""

    trigger: Optional[str] = Field(None, description="Trigger type: date, interval, cron")
    # Cron fields
    year: Optional[str] = Field(None, description="Year (4-digit)")
    month: Optional[str] = Field(None, description="Month (1-12)")
    day: Optional[str] = Field(None, description="Day of month (1-31)")
    week: Optional[str] = Field(None, description="Week of year (1-53)")
    day_of_week: Optional[str] = Field(None, description="Day of week (0-6 or mon-fri)")
    hour: Optional[str] = Field(None, description="Hour (0-23)")
    minute: Optional[str] = Field(None, description="Minute (0-59)")
    second: Optional[str] = Field(None, description="Second (0-59)")
    # Date trigger
    run_date: Optional[datetime] = Field(None, description="Run date for date trigger")
    # Interval trigger
    weeks: Optional[int] = Field(None, description="Weeks interval")
    days: Optional[int] = Field(None, description="Days interval")
    hours: Optional[int] = Field(None, description="Hours interval")
    minutes: Optional[int] = Field(None, description="Minutes interval")
    seconds: Optional[int] = Field(None, description="Seconds interval")
    start_date: Optional[datetime] = Field(None, description="Start date for interval")
    end_date: Optional[datetime] = Field(None, description="End date for interval")


class JobRunRequest(BaseModel):
    """Request to run a job immediately"""

    force: bool = Field(False, description="Force run even if disabled")


# ---- Response Models ----


class JobResponse(BaseModel):
    """Single job information"""

    id: str = Field(..., description="Job ID")
    name: str = Field(..., description="Job name/description")
    trigger: str = Field(..., description="Trigger type")
    trigger_args: Dict[str, Any] = Field(default_factory=dict, description="Trigger arguments")
    next_run_time: Optional[datetime] = Field(None, description="Next scheduled run time")
    last_run_time: Optional[datetime] = Field(None, description="Last run time")
    last_result: Optional[Any] = Field(None, description="Last execution result")
    last_error: Optional[str] = Field(None, description="Last execution error")
    misfire_grace_time: int = Field(60, description="Misfire grace time in seconds")
    max_instances: int = Field(1, description="Max concurrent instances")
    coalesce: bool = Field(True, description="Coalesce missed runs")
    state: JobState = Field(JobState.PENDING, description="Job state")
    func_ref: Optional[str] = Field(None, description="Function reference")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Job keyword arguments")
    runs: int = Field(0, description="Total number of executions")
    successes: int = Field(0, description="Number of successful executions")
    errors: int = Field(0, description="Number of failed executions")
    avg_duration_ms: Optional[float] = Field(None, description="Average execution duration in ms")

    model_config = {"use_enum_values": True}


class SchedulerStatusResponse(BaseModel):
    """Overall scheduler status"""

    running: bool = Field(..., description="Whether scheduler is running")
    current_time: datetime = Field(..., description="Current server time")
    timezone: str = Field(..., description="Scheduler timezone")
    instance_id: str = Field(..., description="This scheduler instance ID")
    cluster_enabled: bool = Field(..., description="Cluster mode enabled")
    pending_jobs: int = Field(0, description="Number of pending jobs")


class SchedulerJobsListResponse(BaseModel):
    """Response containing list of jobs"""

    jobs: List[JobResponse] = Field(default_factory=list)
    running: bool = Field(..., description="Whether scheduler is running")
    current_time: datetime = Field(..., description="Current server time")
    total: int = Field(0, description="Total number of jobs")
    pending: int = Field(0, description="Number of pending (scheduled) jobs")


class JobRunResponse(BaseModel):
    """Response from a job run request"""

    job_id: str
    success: bool
    message: str
    triggered_at: datetime


class JobPauseResponse(BaseModel):
    """Response from a job pause request"""

    job_id: str
    success: bool
    message: str


class JobResumeResponse(BaseModel):
    """Response from a job resume request"""

    job_id: str
    success: bool
    message: str


class JobRescheduleResponse(BaseModel):
    """Response from a job reschedule request"""

    job_id: str
    success: bool
    message: str
    next_run_time: Optional[datetime] = None


# ---- Helper Functions ----


def jobs_to_response(jobs: List[Any], running: bool, current_time: datetime) -> SchedulerJobsListResponse:
    """Convert APScheduler job list to API response"""
    job_responses = []
    pending = 0

    for job in jobs:
        try:
            next_run = job.next_run_time
            if hasattr(next_run, "replace"):
                # Handle tz-aware vs tz-naive
                if next_run.tzinfo is None and current_time.tzinfo is not None:
                    from datetime import timezone as tz

                    next_run = next_run.replace(tzinfo=tz.utc)
        except Exception:
            next_run = None

        # Determine state
        state = JobState.PENDING
        if hasattr(job, "pending"):
            if job.pending:
                state = JobState.PENDING
            else:
                state = JobState.RUNNING

        if hasattr(job, "trigger") and job.trigger:
            trigger_type = getattr(job.trigger, "type", str(job.trigger))
        else:
            trigger_type = "unknown"

        # Build trigger args
        trigger_args = _extract_trigger_args(job.trigger)

        job_response = JobResponse(
            id=job.id,
            name=getattr(job, "name", job.id),
            trigger=trigger_type,
            trigger_args=trigger_args,
            next_run_time=next_run,
            misfire_grace_time=job.misfire_grace_time if hasattr(job, "misfire_grace_time") else 60,
            max_instances=job.max_instances if hasattr(job, "max_instances") else 1,
            coalesce=job.coalesce if hasattr(job, "coalesce") else True,
            state=state,
            func_ref=getattr(job, "func_ref", None),
            kwargs=getattr(job, "kwargs", {}),
        )
        job_responses.append(job_response)
        pending += 1

    return SchedulerJobsListResponse(
        jobs=job_responses,
        running=running,
        current_time=current_time,
        total=len(job_responses),
        pending=pending,
    )


def _extract_trigger_args(trigger) -> Dict[str, Any]:
    """Extract arguments from a trigger object"""
    if trigger is None:
        return {}

    trigger_type = getattr(trigger, "type", "unknown")
    args = {"type": trigger_type}

    if trigger_type == "cron":
        for field_name in ["year", "month", "day", "week", "day_of_week", "hour", "minute", "second"]:
            val = getattr(trigger, field_name, None)
            if val is not None:
                args[field_name] = val
    elif trigger_type == "interval":
        for field_name in ["weeks", "days", "hours", "minutes", "seconds", "start_date", "end_date"]:
            val = getattr(trigger, field_name, None)
            if val is not None:
                if hasattr(val, "total_seconds"):
                    args[field_name] = val.total_seconds()
                else:
                    args[field_name] = val
    elif trigger_type == "date":
        val = getattr(trigger, "run_date", None)
        if val:
            args["run_date"] = str(val)

    return args
