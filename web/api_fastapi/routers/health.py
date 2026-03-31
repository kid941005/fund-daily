"""
Health Check Router
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from db import database_pg as db
from src.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["健康检查"])

NAV_STALE_HOURS = 24
SCORE_STALE_HOURS = 48


def get_version() -> str:
    version_file = "/home/kid/fund-daily/VERSION"
    try:
        with open(version_file) as f:
            return f.read().strip() or "2.6.0"
    except Exception:
        return "2.6.0"


VERSION = get_version()


def _get_scheduler_status() -> dict[str, Any]:
    """Get scheduler jobs status"""
    try:
        from src.scheduler.manager import get_scheduler_manager

        manager = get_scheduler_manager()
        jobs = manager.get_jobs()
        job_list = []
        all_have_next = True
        for job in jobs:
            next_time = job.next_run_time
            job_list.append(
                {
                    "id": job.id,
                    "name": getattr(job, "name", job.id),
                    "next_run_time": next_time.isoformat() if next_time else None,
                    "missed": next_time is None,
                }
            )
            if next_time is None:
                all_have_next = False
        return {
            "status": "ok",
            "job_count": len(jobs),
            "all_have_next_run": all_have_next,
            "jobs": job_list,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_data_freshness() -> dict[str, Any]:
    """Check fund_nav and fund_scores data freshness"""
    result: dict[str, Any] = {"nav": {}, "scores": {}}

    try:
        with db.get_db() as conn:
            with db.get_cursor(conn) as cursor:
                cursor.execute("SELECT MAX(created_at) FROM fund_nav")
                row = cursor.fetchone()
                val = row[0] if row else None
                result["nav"]["latest_update"] = val.isoformat() if val else None

                cursor.execute("SELECT MAX(created_at) FROM fund_scores")
                row = cursor.fetchone()
                val = row[0] if row else None
                result["scores"]["latest_update"] = val.isoformat() if val else None

                today = datetime.now(timezone.utc).date()
                cursor.execute("SELECT COUNT(*) FROM fund_nav WHERE nav_date = %s", (today,))
                result["nav"]["today_count"] = cursor.fetchone()[0] or 0
    except Exception as e:
        result["error"] = str(e)

    now = datetime.now(timezone.utc)
    for field in ("nav", "scores"):
        latest = result[field].get("latest_update")
        if latest:
            try:
                dt = datetime.fromisoformat(latest).astimezone(timezone.utc)
                age_hours = (now - dt).total_seconds() / 3600
                threshold = NAV_STALE_HOURS if field == "nav" else SCORE_STALE_HOURS
                result[field]["age_hours"] = round(age_hours, 1)
                result[field]["stale"] = age_hours > threshold
            except Exception:
                pass

    return result


@router.get("/health")
async def basic_health_check():
    """Basic health check endpoint"""
    pg_status = "ok"
    try:
        with db.get_db() as conn:
            with db.get_cursor(conn) as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as e:
        pg_status = str(e)

    redis_status = "ok"
    try:
        from src.cache.redis_cache import get_redis_client

        client = get_redis_client()
        if client:
            client.ping()
        else:
            redis_status = "client not initialized"
    except Exception as e:
        redis_status = str(e)

    config = get_config()

    return {
        "status": "ok" if pg_status == "ok" and redis_status == "ok" else "degraded",
        "version": VERSION,
        "database": pg_status,
        "redis": redis_status,
        "config": {
            "env": config.app.env,
            "database_type": "postgres",
            "cache_enabled": config.cache.duration > 0,
        },
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    health = await basic_health_check()
    components: dict[str, Any] = {}

    # Database pool
    try:
        pool = db.get_pool()
        pool_size = getattr(pool, "size", lambda: None)
        pool_checked = getattr(pool, "checkedout", lambda: None)
        components["db_pool"] = {
            "status": "ok",
            "size": pool_size() if callable(pool_size) else None,
            "checked_out": pool_checked() if callable(pool_checked) else None,
        }
    except Exception as e:
        components["db_pool"] = {"status": "error", "error": str(e)}

    # Redis
    try:
        from src.cache.redis_cache import get_redis_client

        client = get_redis_client()
        if client:
            info = client.info()
            components["redis"] = {
                "status": "ok",
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
    except Exception as e:
        components["redis"] = {"status": "error", "error": str(e)}

    # Scheduler
    components["scheduler"] = _get_scheduler_status()

    # Data freshness
    components["data_freshness"] = _get_data_freshness()

    health["components"] = components
    health["timestamp"] = datetime.now(timezone.utc).isoformat()

    return health


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for k8s/load balancer."""
    issues: list[str] = []

    try:
        with db.get_db() as conn:
            with db.get_cursor(conn) as cursor:
                cursor.execute("SELECT 1")
    except Exception as e:
        issues.append(f"database: {e}")

    try:
        from src.cache.redis_cache import get_redis_client

        client = get_redis_client()
        if client:
            client.ping()
        else:
            issues.append("redis: not initialized")
    except Exception as e:
        issues.append(f"redis: {e}")

    if issues:
        return {"ready": False, "issues": issues}
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """Liveness probe."""
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}
