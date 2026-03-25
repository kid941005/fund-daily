"""
Cache Update Task Handler

Handles cache warmup and update tasks.
"""

import logging
from typing import Dict, Any

from ..background import TaskContext, TaskType
from ..task_registry import register_task

logger = logging.getLogger(__name__)


@register_task(
    task_type=TaskType.CACHE_WARM,
    name="缓存预热",
    description="预热常用数据的缓存",
    max_concurrent=1,
    timeout=600
)
def cache_warmup_handler(context: TaskContext) -> Dict[str, Any]:
    """
    Handle cache warmup tasks
    
    Preloads commonly accessed data into cache.
    
    Args:
        context: Task execution context
        
    Returns:
        Result dictionary with warmup results
    """
    warmup_type = context.params.get("type", "all")  # all, funds, analysis, scores
    user_id = context.params.get("user_id")
    
    results = {
        "warmed": [],
        "errors": [],
        "type": warmup_type
    }
    
    try:
        from src.cache.manager import CacheManager
        cache_mgr = CacheManager.get_instance()
    except ImportError as e:
        logger.error(f"Failed to get CacheManager: {e}")
        return {"error": f"Import error: {e}"}
    
    try:
        from db import database_pg as db
        
        # Get funds to warmup
        if user_id:
            holdings = db.get_holdings(user_id)
        else:
            holdings = db.get_all_holdings()
        
        codes = list(set([h.get("code") for h in holdings if h.get("code")]))
        
    except Exception as e:
        logger.error(f"Failed to get holdings: {e}")
        codes = []
    
    total = len(codes)
    context.update_progress(0.1, f"开始缓存预热，共 {total} 个基金")
    
    # Warmup fund data
    if warmup_type in ("all", "funds"):
        for i, code in enumerate(codes):
            if context.check_cancelled():
                results["cancelled"] = True
                break
            
            try:
                # Warmup fund basic info
                _warmup_fund_cache(cache_mgr, code)
                results["warmed"].append(f"fund:{code}")
                
                progress = 0.1 + 0.5 * (i + 1) / total
                context.update_progress(progress, f"预热基金缓存 {i + 1}/{total}")
                
            except Exception as e:
                logger.warning(f"Failed to warmup cache for {code}: {e}")
                results["errors"].append({"code": code, "error": str(e)})
    
    # Warmup analysis data
    if warmup_type in ("all", "analysis"):
        context.update_progress(0.6, "预热分析数据缓存")
        
        for i, code in enumerate(codes):
            if context.check_cancelled():
                results["cancelled"] = True
                break
            
            try:
                _warmup_analysis_cache(cache_mgr, code)
                results["warmed"].append(f"analysis:{code}")
                
                progress = 0.6 + 0.3 * (i + 1) / total
                context.update_progress(progress, f"预热分析缓存 {i + 1}/{total}")
                
            except Exception as e:
                logger.warning(f"Failed to warmup analysis for {code}: {e}")
                results["errors"].append({"code": code, "error": str(e)})
    
    # Warmup score data
    if warmup_type in ("all", "scores"):
        context.update_progress(0.9, "预热评分数据缓存")
        
        for i, code in enumerate(codes):
            if context.check_cancelled():
                results["cancelled"] = True
                break
            
            try:
                _warmup_score_cache(cache_mgr, code)
                results["warmed"].append(f"score:{code}")
                
                progress = 0.9 + 0.1 * (i + 1) / total
                context.update_progress(progress, f"预热评分缓存 {i + 1}/{total}")
                
            except Exception as e:
                logger.warning(f"Failed to warmup score for {code}: {e}")
                results["errors"].append({"code": code, "error": str(e)})
    
    results["total"] = total
    results["warmed_count"] = len(results["warmed"])
    
    context.update_progress(1.0, f"缓存预热完成: {len(results['warmed'])} 项")
    logger.info(f"Cache warmup completed: {results['warmed_count']} items")
    
    return results


def _warmup_fund_cache(cache_mgr, code: str):
    """Warmup fund basic cache"""
    try:
        from src.fetcher import fetch_fund_data
        fund_data = fetch_fund_data(code)
        return fund_data is not None
    except Exception:
        return False


def _warmup_analysis_cache(cache_mgr, code: str):
    """Warmup analysis cache"""
    try:
        from src.advice import get_fund_detail_info
        detail = get_fund_detail_info(code)
        return detail is not None
    except Exception:
        return False


def _warmup_score_cache(cache_mgr, code: str):
    """Warmup score cache"""
    try:
        from src.scoring.manager import ScoreManager
        scorer = ScoreManager.get_instance()
        score = scorer.calculate_fund_score(code)
        return score is not None
    except Exception:
        return False
