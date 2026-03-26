"""
Calculation Task Handler

Handles batch calculation tasks like score calculation.
"""

import logging
from typing import Dict, Any, List

from ..background import TaskContext, TaskType
from ..task_registry import register_task

logger = logging.getLogger(__name__)


@register_task(
    task_type=TaskType.SCORE_CALC, name="评分计算", description="批量计算基金评分", max_concurrent=2, timeout=3600
)
def score_calculation_handler(context: TaskContext) -> Dict[str, Any]:
    """
    Handle score calculation tasks

    Calculates comprehensive scores for funds.

    Args:
        context: Task execution context

    Returns:
        Result dictionary with calculation results
    """
    codes = context.params.get("codes", [])
    force = context.params.get("force", False)  # Force recalculation
    user_id = context.params.get("user_id")

    if not codes:
        try:
            from db import database_pg as db

            if user_id:
                holdings = db.get_holdings(user_id)
            else:
                holdings = db.get_all_holdings()
            codes = list(set([h.get("code") for h in holdings if h.get("code")]))
        except Exception as e:
            logger.error(f"Failed to get fund codes: {e}")
            codes = []

    if not codes:
        return {"calculated": 0, "errors": [], "message": "No funds to calculate"}

    total = len(codes)
    results = {"calculated": 0, "errors": [], "scores": {}}

    try:
        from src.scoring.manager import ScoreManager

        scorer = ScoreManager.get_instance()
    except ImportError as e:
        logger.error(f"Failed to get ScoreManager: {e}")
        return {"error": f"Import error: {e}"}

    for i, code in enumerate(codes):
        if context.check_cancelled():
            logger.info(f"Task {context.task_id} cancelled at {i}/{total}")
            results["cancelled"] = True
            results["calculated"] = i
            break

        try:
            # Calculate score
            score_data = scorer.calculate_fund_score(code, use_cache=not force)

            if score_data:
                results["calculated"] += 1
                results["scores"][code] = score_data

            progress = (i + 1) / total
            context.update_progress(progress, f"已计算 {i + 1}/{total} 个评分")

        except Exception as e:
            logger.warning(f"Failed to calculate score for {code}: {e}")
            results["errors"].append({"code": code, "error": str(e)})

    results["total"] = total

    context.update_progress(1.0, f"评分计算完成: {results['calculated']}/{total}")
    logger.info(f"Score calculation completed: {results['calculated']}/{total} successful")

    return results


@register_task(
    task_type=TaskType.BATCH_IMPORT, name="批量导入", description="批量导入基金数据", max_concurrent=1, timeout=1800
)
def batch_import_handler(context: TaskContext) -> Dict[str, Any]:
    """
    Handle batch import tasks

    Imports fund data from external sources.

    Args:
        context: Task execution context

    Returns:
        Result dictionary with import results
    """
    source = context.params.get("source", "xueqiu")  # xueqiu, alipay, csv
    user_id = context.params.get("user_id")
    file_path = context.params.get("file_path")

    results = {"imported": 0, "skipped": 0, "errors": []}

    context.update_progress(0.1, f"开始从 {source} 导入数据")

    if source == "xueqiu":
        results.update(_import_from_xueqiu(context))
    elif source == "alipay":
        results.update(_import_from_alipay(context))
    elif source == "csv":
        results.update(_import_from_csv(context, file_path))
    else:
        results["error"] = f"Unknown source: {source}"

    return results


def _import_from_xueqiu(context: TaskContext) -> Dict[str, Any]:
    """Import data from Xueqiu"""
    results = {"imported": 0, "skipped": 0, "errors": []}

    try:
        from src.fetcher.xueqiu import XueqiuFetcher

        fetcher = XueqiuFetcher()

        # Fetch holdings
        holdings_data = fetcher.fetch_holdings()

        if not holdings_data:
            results["message"] = "No holdings found"
            return results

        total = len(holdings_data)

        for i, holding in enumerate(holdings_data):
            if context.check_cancelled():
                results["cancelled"] = True
                break

            try:
                code = holding.get("code")
                name = holding.get("name")
                amount = holding.get("amount", 0)

                if not code:
                    results["skipped"] += 1
                    continue

                # Save to database
                _save_holding(context, code, name, amount)
                results["imported"] += 1

                progress = (i + 1) / total
                context.update_progress(progress, f"已导入 {i + 1}/{total}")

            except Exception as e:
                logger.warning(f"Failed to import holding: {e}")
                results["errors"].append(str(e))

    except ImportError as e:
        results["error"] = f"Import error: {e}"

    return results


def _import_from_alipay(context: TaskContext) -> Dict[str, Any]:
    """Import data from Alipay"""
    results = {"imported": 0, "skipped": 0, "errors": []}

    try:
        from src.fetcher.alipay import AlipayFetcher

        fetcher = AlipayFetcher()

        holdings_data = fetcher.fetch_holdings()

        if not holdings_data:
            results["message"] = "No holdings found"
            return results

        total = len(holdings_data)

        for i, holding in enumerate(holdings_data):
            if context.check_cancelled():
                results["cancelled"] = True
                break

            try:
                code = holding.get("code")
                name = holding.get("name")
                amount = holding.get("amount", 0)

                if not code:
                    results["skipped"] += 1
                    continue

                _save_holding(context, code, name, amount)
                results["imported"] += 1

                progress = (i + 1) / total
                context.update_progress(progress, f"已导入 {i + 1}/{total}")

            except Exception as e:
                logger.warning(f"Failed to import holding: {e}")
                results["errors"].append(str(e))

    except ImportError as e:
        results["error"] = f"Import error: {e}"

    return results


def _import_from_csv(context: TaskContext, file_path: str) -> Dict[str, Any]:
    """Import data from CSV file"""
    results = {"imported": 0, "skipped": 0, "errors": []}

    if not file_path:
        results["error"] = "No file path provided"
        return results

    import csv

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total = len(rows)

        for i, row in enumerate(rows):
            if context.check_cancelled():
                results["cancelled"] = True
                break

            try:
                code = row.get("code", "").strip()
                name = row.get("name", "").strip()
                amount = float(row.get("amount", 0) or 0)

                if not code:
                    results["skipped"] += 1
                    continue

                _save_holding(context, code, name, amount)
                results["imported"] += 1

                progress = (i + 1) / total
                context.update_progress(progress, f"已导入 {i + 1}/{total}")

            except Exception as e:
                logger.warning(f"Failed to import row: {e}")
                results["errors"].append(str(e))

    except FileNotFoundError:
        results["error"] = f"File not found: {file_path}"
    except Exception as e:
        results["error"] = f"CSV import error: {e}"

    return results


def _save_holding(context: TaskContext, code: str, name: str, amount: float):
    """Save a holding to the database"""
    user_id = context.params.get("user_id")

    if not user_id:
        return

    try:
        from db import database_pg as db

        db.add_holding(user_id=user_id, code=code, name=name, amount=amount)
    except Exception as e:
        logger.warning(f"Failed to save holding {code}: {e}")
        raise
