"""
Data Fetch Task Handler

Handles fund data fetching tasks in the background.
"""

import logging
from typing import Any, Dict

from ..models import TaskContext, TaskType
from ..task_registry import register_task

logger = logging.getLogger(__name__)


@register_task(
    task_type=TaskType.FUND_FETCH,
    name="基金数据抓取",
    description="从数据源抓取基金基本信息",
    max_concurrent=2,
    timeout=1800,
)
def fund_fetch_handler(context: TaskContext) -> Dict[str, Any]:
    """
    Handle fund data fetching

    Args:
        context: Task execution context

    Returns:
        Result dictionary with fetched data
    """
    codes = context.params.get("codes", [])
    force = context.params.get("force", False)

    if not codes:
        # Get all fund codes from database
        try:
            from db import database_pg as db

            holdings = db.get_all_holdings()
            codes = list(set([h.get("code") for h in holdings if h.get("code")]))
        except Exception as e:
            logger.error(f"Failed to get fund codes: {e}")
            codes = []

    if not codes:
        return {"fetched": 0, "errors": [], "message": "No funds to fetch"}

    total = len(codes)
    results = {"fetched": 0, "errors": [], "codes": []}

    # Import fetcher
    try:
        from src.fetcher import fetch_fund_data
    except ImportError as e:
        logger.error(f"Failed to import fetcher: {e}")
        return {"error": f"Import error: {e}"}

    for i, code in enumerate(codes):
        # Check cancellation
        if context.check_cancelled():
            logger.info(f"Task {context.task_id} cancelled, stopping at {i}/{total}")
            results["cancelled"] = True
            results["fetched"] = i
            break

        try:
            # Fetch fund data
            fund_data = fetch_fund_data(code, use_cache=not force)

            if fund_data:
                results["fetched"] += 1
                results["codes"].append(code)

            # Update progress
            progress = (i + 1) / total
            context.update_progress(progress, f"已抓取 {i + 1}/{total} 个基金")

        except Exception as e:
            logger.warning(f"Failed to fetch fund {code}: {e}")
            results["errors"].append({"code": code, "error": str(e)})

    results["total"] = total
    logger.info(f"Fund fetch completed: {results['fetched']}/{total} successful")

    return results


@register_task(
    task_type=TaskType.NAV_UPDATE, name="净值更新", description="更新基金净值数据", max_concurrent=3, timeout=900
)
def nav_update_handler(context: TaskContext) -> Dict[str, Any]:
    """
    Handle NAV (Net Asset Value) update tasks

    Args:
        context: Task execution context

    Returns:
        Result dictionary with update results
    """
    codes = context.params.get("codes", [])
    days = context.params.get("days", 30)  # Number of days to fetch

    if not codes:
        try:
            from db import database_pg as db

            holdings = db.get_all_holdings()
            codes = list(set([h.get("code") for h in holdings if h.get("code")]))
        except Exception as e:
            logger.error(f"Failed to get fund codes: {e}")
            codes = []

    if not codes:
        return {"updated": 0, "errors": [], "message": "No funds to update"}

    total = len(codes)
    results = {"updated": 0, "errors": [], "codes": []}

    try:
        from src.fetcher.enhanced_fetcher import EnhancedFetcher

        fetcher = EnhancedFetcher()
    except ImportError as e:
        logger.error(f"Failed to import fetchers: {e}")
        return {"error": f"Import error: {e}"}

    for i, code in enumerate(codes):
        if context.check_cancelled():
            logger.info(f"Task {context.task_id} cancelled at {i}/{total}")
            results["cancelled"] = True
            results["updated"] = i
            break

        try:
            # Fetch NAV history
            nav_data = fetcher.fetch_nav_history(code, days=days)

            if nav_data:
                results["updated"] += 1
                results["codes"].append(code)

            progress = (i + 1) / total
            context.update_progress(progress, f"已更新 {i + 1}/{total} 个净值")

        except Exception as e:
            logger.warning(f"Failed to update NAV for {code}: {e}")
            results["errors"].append({"code": code, "error": str(e)})

    results["total"] = total
    return results
