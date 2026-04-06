"""
Scheduled Job Definitions

Predefined scheduled jobs for fund data management.
Each job class wraps a task handler with scheduling metadata.
"""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from src.tasks.models import TaskType

logger = logging.getLogger(__name__)


T = TypeVar("T")


def batch_process(
    items: list[T],
    processor: Callable[[T], Any],
    batch_size: int = 10,
    max_workers: int = 5,
    progress_callback: Callable[[int, int], None] = None,
) -> dict[str, list[Any]]:
    """
    分批处理任务

    Args:
        items: 待处理的数据列表
        processor: 处理函数
        batch_size: 每批大小
        max_workers: 最大并发数
        progress_callback: 进度回调函数 (current, total)

    Returns:
        {"success": [...], "failed": [...]}
    """
    results = {"success": [], "failed": []}
    total = len(items)

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = items[batch_start:batch_end]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {executor.submit(processor, item): item for item in batch}

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results["success"].append(result)
                except Exception as e:
                    logger.warning(f"处理失败 {item}: {e}")
                    results["failed"].append({"item": item, "error": str(e)})

        if progress_callback:
            progress_callback(batch_end, total)

        logger.debug(f"批次完成: {batch_end}/{total}")

    return results


class ScheduledJobType(str, Enum):
    """Predefined scheduled job types"""

    FUND_FETCH = "fund_fetch"
    NAV_UPDATE = "nav_update"
    SCORE_CALC = "score_calc"
    CACHE_WARMUP = "cache_warmup"
    MARKET_OPEN_CHECK = "market_open_check"
    CLEANUP_OLD_DATA = "cleanup_old_data"


# ---- Job Metadata Registry ----


class JobMetadata:
    """Metadata for a scheduled job"""

    def __init__(
        self,
        job_id: str,
        name: str,
        description: str,
        trigger_type: str,
        trigger_args: dict[str, Any],
        func_ref: str,
        enabled: bool = True,
        misfire_grace_time: int = 60,
        max_instances: int = 1,
        coalesce: bool = True,
    ):
        self.job_id = job_id
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.trigger_args = trigger_args
        self.func_ref = func_ref
        self.enabled = enabled
        self.misfire_grace_time = misfire_grace_time
        self.max_instances = max_instances
        self.coalesce = coalesce


# Predefined job registry
SCHEDULED_JOBS: dict[str, JobMetadata] = {}


def _register_job(meta: JobMetadata):
    """Register a job in the global registry"""
    SCHEDULED_JOBS[meta.job_id] = meta
    return meta


# ---- Job Definitions ----


def _get_fund_codes(user_id: str | None = None) -> list[str]:
    """Get list of fund codes to process"""
    try:
        from db import database_pg as db

        if user_id:
            holdings = db.get_holdings(user_id)
        else:
            holdings = db.get_all_holdings()
        codes = list({h.get("code") for h in holdings if h.get("code")})
        return codes
    except Exception as e:
        logger.warning(f"Failed to get fund codes: {e}")
        return []


def _is_trading_day() -> bool:
    """Check if today is a trading day (Monday-Friday)"""
    today = datetime.now()
    # Monday = 0, Sunday = 6
    return today.weekday() < 5


# ---- Daily NAV Update Job ----
# Runs every trading day at 16:00 (30 minutes after market close)


def _daily_nav_update_sync():
    """Daily NAV update - synchronous core"""
    logger.info("🔄 [Scheduler] Starting daily NAV update")
    start_time = datetime.now()

    codes = _get_fund_codes()
    if not codes:
        logger.info("🔄 [Scheduler] No funds to update, skipping")
        return {"updated": 0, "message": "No funds to update"}

    total = len(codes)
    updated = 0
    errors = []

    try:
        from src.fetcher.enhanced_fetcher import EnhancedFetcher

        fetcher = EnhancedFetcher()
    except ImportError as e:
        logger.error(f"[Scheduler] Failed to import EnhancedFetcher: {e}")
        return {"error": str(e)}

    for i, code in enumerate(codes):
        try:
            nav_data = fetcher.fetch_nav_history(code, days=7)
            if nav_data:
                updated += 1
            if (i + 1) % 10 == 0:
                logger.info(f"[Scheduler] NAV update progress: {i + 1}/{total}")
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to update NAV for {code}: {e}")
            errors.append({"code": code, "error": str(e)})

    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"✅ [Scheduler] Daily NAV update completed: {updated}/{total} in {duration:.1f}s")
    return {"updated": updated, "total": total, "errors": len(errors), "duration_s": duration}


async def _daily_nav_update_async():
    """
    Daily NAV Update Job (async core)

    Fetches latest NAV data for all tracked funds.
    Runs 30 minutes after market close to allow data providers to update.
    """


def daily_nav_update():
    """Sync wrapper for APScheduler."""
    from src.tasks.background import BackgroundTaskManager

    try:
        # Delegate to background task system
        manager = BackgroundTaskManager.get_instance()
        codes = _get_fund_codes()

        # Submit NAV update task
        task_id = manager.submit(task_type=TaskType.NAV_UPDATE.value, params={"codes": codes, "days": 7})
        logger.info(f"📋 [Scheduler] NAV update task submitted: {task_id}")
        return {"task_id": task_id, "funds": len(codes)}

    except Exception as e:
        logger.error(f"❌ [Scheduler] Daily NAV update failed: {e}")
        raise


_daily_nav_update_job = _register_job(
    JobMetadata(
        job_id="daily_nav_update",
        name="每日净值更新",
        description="每个交易日 16:00 自动抓取基金净值数据",
        trigger_type="cron",
        trigger_args={"hour": 16, "minute": 0, "day_of_week": "mon-fri"},
        func_ref="src.scheduler.jobs.daily_nav_update",
        enabled=True,
        misfire_grace_time=60,
        max_instances=1,
    )
)


# ---- Weekly Score Calculation Job ----
# Runs every Monday at 09:00


async def _weekly_score_calculation_async():
    """
    Weekly Score Calculation Job (async core)

    Recalculates comprehensive scores for all funds.
    Runs Monday morning to refresh scores for the new week.
    """


def weekly_score_calculation():
    """Sync wrapper for APScheduler."""
    from src.tasks.background import BackgroundTaskManager

    if not _is_trading_day():
        logger.info("[Scheduler] Skipping weekly score calc (not a trading day)")
        return {"skipped": True, "reason": "Not a trading day"}

    try:
        manager = BackgroundTaskManager.get_instance()
        codes = _get_fund_codes()

        task_id = manager.submit(task_type=TaskType.SCORE_CALC.value, params={"codes": codes, "force": True})
        logger.info(f"📋 [Scheduler] Score calculation task submitted: {task_id}")
        return {"task_id": task_id, "funds": len(codes)}

    except Exception as e:
        logger.error(f"❌ [Scheduler] Weekly score calculation failed: {e}")
        raise


_register_job(
    JobMetadata(
        job_id="weekly_score_calculation",
        name="每周评分计算",
        description="每周一 09:00 重新计算所有基金评分",
        trigger_type="cron",
        trigger_args={"hour": 9, "minute": 0, "day_of_week": 0},
        func_ref="src.scheduler.jobs.weekly_score_calculation",
        enabled=True,
        misfire_grace_time=120,
        max_instances=1,
    )
)


# ---- Market Open Reminder Job ----
# Runs every trading day at 08:55


async def _market_open_reminder_async():
    """
    Market Open Reminder Job (async core)

    Sends a reminder notification 5 minutes before market open.
    Integrates with notification system (Feishu/bot) if configured.
    """


def market_open_reminder():
    """Sync wrapper for APScheduler."""
    if not _is_trading_day():
        logger.info("[Scheduler] Skipping market open reminder (not a trading day)")
        return {"skipped": True}

    logger.info("🔔 [Scheduler] Market open reminder triggered")

    try:
        # Try to send notification
        _send_market_reminder()
        return {"sent": True}

    except Exception as e:
        logger.warning(f"[Scheduler] Market reminder failed: {e}")
        return {"sent": False, "error": str(e)}


def _send_market_reminder():
    """Send market open reminder via configured channel"""
    import os

    # Try Feishu webhook if configured
    feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if feishu_webhook:
        try:
            from datetime import datetime

            import requests

            today = datetime.now().strftime("%Y年%m月%d日")
            message = {
                "msg_type": "text",
                "content": {"text": f"📈 [{today}] A股市场即将开盘！\n请做好准备，今天也要加油！"},
            }
            requests.post(feishu_webhook, json=message, timeout=5)
            logger.info("[Scheduler] Feishu reminder sent")
            return
        except Exception as e:
            logger.warning(f"[Scheduler] Feishu reminder failed: {e}")

    logger.info("[Scheduler] No notification channel configured, skipping")


_register_job(
    JobMetadata(
        job_id="market_open_reminder",
        name="开市提醒",
        description="每个交易日 08:55 发送开市提醒",
        trigger_type="cron",
        trigger_args={"hour": 8, "minute": 55, "day_of_week": "mon-fri"},
        func_ref="src.scheduler.jobs.market_open_reminder",
        enabled=True,
        misfire_grace_time=30,
        max_instances=1,
    )
)


# ---- Cache Warmup Job ----
# Runs every 30 minutes


async def _cache_warmup_async():
    """
    Cache Warmup Job (async core)

    Preloads frequently accessed fund data into cache.
    Runs every 30 minutes to ensure cache freshness.
    """


def cache_warmup():
    """Sync wrapper for APScheduler."""
    from src.tasks.background import BackgroundTaskManager

    try:
        manager = BackgroundTaskManager.get_instance()

        task_id = manager.submit(task_type=TaskType.CACHE_WARM.value, params={"type": "all"})
        logger.info(f"📋 [Scheduler] Cache warmup task submitted: {task_id}")
        return {"task_id": task_id}

    except Exception as e:
        logger.error(f"❌ [Scheduler] Cache warmup failed: {e}")
        raise


_register_job(
    JobMetadata(
        job_id="cache_warmup",
        name="缓存预热",
        description="每 30 分钟预热缓存，提高 API 响应速度",
        trigger_type="interval",
        trigger_args={"minutes": 30},
        func_ref="src.scheduler.jobs.cache_warmup",
        enabled=True,
        misfire_grace_time=60,
        max_instances=1,
    )
)


# ---- Cleanup Old Data Job ----
# Runs daily at 23:00


async def _cleanup_old_data_async():
    """
    Cleanup Old Data Job (async core)

    Removes expired cache entries and old task records.
    Runs nightly to maintain database hygiene.
    """
    logger.info("🧹 [Scheduler] Starting data cleanup")
    start_time = datetime.now()

    cleaned = {"cache_entries": 0, "old_tasks": 0, "errors": []}

    # Cleanup old cache entries
    try:
        from src.cache.manager import CacheManager

        cache_mgr = CacheManager.get_instance()
        cache_mgr.cleanup_expired()
        cleaned["cache_entries"] = 1
    except Exception as e:
        logger.warning(f"[Scheduler] Cache cleanup failed: {e}")
        cleaned["errors"].append({"cache": str(e)})

    # Cleanup old completed tasks (older than 7 days)
    try:
        from src.tasks.background import BackgroundTaskManager

        BackgroundTaskManager.get_instance()
        # This would need a cleanup method in the task manager
        # For now, just log
        logger.info("[Scheduler] Task cleanup skipped (not implemented)")
    except Exception as e:
        logger.warning(f"[Scheduler] Task cleanup failed: {e}")
        cleaned["errors"].append({"tasks": str(e)})

    # Cleanup old NAV history (keep last 2 years)
    try:

        logger.info("[Scheduler] NAV history cleanup would be done here")
    except Exception as e:
        logger.warning(f"[Scheduler] NAV cleanup failed: {e}")
        cleaned["errors"].append({"nav": str(e)})

    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"✅ [Scheduler] Cleanup completed in {duration:.1f}s, errors: {len(cleaned['errors'])}")
    return cleaned


def cleanup_old_data():
    """Sync wrapper for APScheduler."""
    logger.info("🧹 [Scheduler] Starting data cleanup")
    start_time = datetime.now()

    cleaned = {"cache_entries": 0, "old_tasks": 0, "errors": []}

    # Cleanup old cache entries
    try:
        from src.cache.manager import CacheManager

        cache_mgr = CacheManager.get_instance()
        cache_mgr.cleanup_expired()
        cleaned["cache_entries"] = 1
    except Exception as e:
        logger.warning(f"[Scheduler] Cache cleanup failed: {e}")
        cleaned["errors"].append({"cache": str(e)})

    # Cleanup old completed tasks (older than 7 days)
    try:
        from src.tasks.background import BackgroundTaskManager

        BackgroundTaskManager.get_instance()
        # This would need a cleanup method in the task manager
        # For now, just log
        logger.info("[Scheduler] Task cleanup skipped (not implemented)")
    except Exception as e:
        logger.warning(f"[Scheduler] Task cleanup failed: {e}")
        cleaned["errors"].append({"tasks": str(e)})

    # Cleanup old NAV history (keep last 2 years)
    try:

        logger.info("[Scheduler] NAV history cleanup would be done here")
    except Exception as e:
        logger.warning(f"[Scheduler] NAV cleanup failed: {e}")
        cleaned["errors"].append({"nav": str(e)})

    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"✅ [Scheduler] Cleanup completed in {duration:.1f}s, errors: {len(cleaned['errors'])}")
    return cleaned


_register_job(
    JobMetadata(
        job_id="cleanup_old_data",
        name="清理过期数据",
        description="每日 23:00 清理过期缓存和旧数据",
        trigger_type="cron",
        trigger_args={"hour": 23, "minute": 0},
        func_ref="src.scheduler.jobs.cleanup_old_data",
        enabled=True,
        misfire_grace_time=300,
        max_instances=1,
    )
)


# ---- Fund Data Fetch Job ----
# Runs every 2 hours during trading hours


async def _fund_data_fetch_async():
    """
    Fund Data Fetch Job (async core)

    Periodically fetches fund basic data to keep information current.
    """
    from src.tasks.background import BackgroundTaskManager

    try:
        manager = BackgroundTaskManager.get_instance()
        codes = _get_fund_codes()

        task_id = manager.submit(task_type=TaskType.FUND_FETCH.value, params={"codes": codes, "force": False})
        logger.info(f"📋 [Scheduler] Fund fetch task submitted: {task_id}")
        return {"task_id": task_id, "funds": len(codes)}

    except Exception as e:
        logger.error(f"❌ [Scheduler] Fund fetch failed: {e}")
        raise


def fund_data_fetch():
    """Sync wrapper for APScheduler."""


_register_job(
    JobMetadata(
        job_id="fund_data_fetch",
        name="基金数据抓取",
        description="每 2 小时抓取基金基本信息",
        trigger_type="interval",
        trigger_args={"hours": 2},
        func_ref="src.scheduler.jobs.fund_data_fetch",
        enabled=True,
        misfire_grace_time=120,
        max_instances=1,
    )
)


def get_scheduled_job(job_id: str) -> JobMetadata | None:
    """Get job metadata by ID"""
    return SCHEDULED_JOBS.get(job_id)


def list_scheduled_jobs() -> dict[str, JobMetadata]:
    """List all registered scheduled jobs"""
    return dict(SCHEDULED_JOBS)


def get_job_trigger_args(job_id: str) -> dict[str, Any]:
    """Get trigger arguments for a job"""
    meta = SCHEDULED_JOBS.get(job_id)
    if meta:
        return meta.trigger_args
    return {}
