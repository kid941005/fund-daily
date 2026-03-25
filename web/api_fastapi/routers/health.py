"""
Health Check Router
"""

import logging
from datetime import datetime

from fastapi import APIRouter
from db import database_pg as db
from src.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["健康检查"])


def get_version():
    """Read version from VERSION file"""
    VERSION_FILE = "/home/kid/fund-daily/VERSION"
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip() or "2.6.0"
    except Exception:
        return "2.6.0"


VERSION = get_version()


@router.get("/health")
async def basic_health_check():
    """Basic health check endpoint"""
    # Check PostgreSQL
    pg_status = "ok"
    try:
        with db.get_db() as conn:
            with db.get_cursor(conn) as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as e:
        pg_status = str(e)
    
    # Check Redis
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
        }
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    health = await basic_health_check()
    
    # Add more detailed checks
    components = {}
    
    # Check database pools
    try:
        pool = db.get_pool()
        components["db_pool"] = {
            "status": "ok",
            "size": pool.size(),
            "checked_out": pool.checkedout(),
        }
    except Exception as e:
        components["db_pool"] = {"status": "error", "error": str(e)}
    
    # Check cache
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
    
    health["components"] = components
    health["timestamp"] = datetime.now().isoformat()
    
    return health
