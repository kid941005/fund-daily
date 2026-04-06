"""
Advice module - 投资建议模块
提供基金分析、建议生成、评分等功能
"""

import logging
import re

from ..analyzer import calculate_risk_metrics, get_commodity_sentiment, get_market_sentiment
from ..fetcher import fetch_fund_data, fetch_fund_detail
from .generate import PORTFOLIO_ALLOCATION_RATIOS as ALLOCATION_RATIOS
from .generate import PORTFOLIO_SCORE_THRESHOLDS as SCORE_THRESHOLDS
from .generate import PORTFOLIO_WEIGHT_CONFIG as WEIGHT_CONFIG
from .generate import (
    format_report_for_share,
    generate_advice,
    generate_daily_report,
)

logger = logging.getLogger(__name__)

__all__ = [
    "analyze_fund",
    "generate_daily_report",
    "format_report_for_share",
    "generate_advice",
    "get_fund_detail_info",
    "generate_100_score",
    "format_100_score_report",
    "get_commodity_sentiment",
    "get_market_sentiment",
    "SCORE_THRESHOLDS",
    "ALLOCATION_RATIOS",
    "WEIGHT_CONFIG",
]


def analyze_fund(fund_data: dict, use_cache: bool = True) -> dict:
    """Analyze fund data"""
    if "error" in fund_data:
        return {"error": fund_data["error"]}
    if not fund_data.get("code"):
        return {"error": "No fund data available"}

    fund_code = fund_data.get("code", "")
    name = fund_data.get("name", "Unknown")
    nav = fund_data.get("nav", 0) or fund_data.get("dwjz", "N/A")
    estimated_change = float(
        fund_data.get("estimated_change", 0)
        or fund_data.get("estimated_change_percent", 0)
        or fund_data.get("gszzl", 0)
    )
    estimated_nav = fund_data.get("estimated_nav", "N/A")

    trend = "up" if estimated_change > 0 else "down" if estimated_change < 0 else "flat"

    if estimated_change > 3:
        summary = f"🚀 {name} 大涨 {estimated_change}%，净值 {nav}"
    elif estimated_change > 1:
        summary = f"📈 {name} 上涨 {estimated_change}%，净值 {nav}"
    elif estimated_change > -1:
        summary = f"➖ {name} 平盘 {estimated_change}%，净值 {nav}"
    elif estimated_change > -3:
        summary = f"📉 {name} 下跌 {estimated_change}%，净值 {nav}"
    else:
        summary = f"🔻 {name} 大跌 {estimated_change}%，净值 {nav}"

    score_100 = {}
    try:
        score_100 = generate_100_score(fund_code, estimated_change, use_cache=use_cache) or {}
    except Exception as e:
        logger.error(f"Error generating score for {fund_code}: {e}")

    # 保存评分到数据库（包含8维度+审计追踪）
    if score_100 and not score_100.get("error"):
        try:
            from datetime import date
            from db.fund_ops import save_fund_score

            details = score_100.get("details", {})
            audit = score_100.get("audit", {})

            save_fund_score(
                fund_code=fund_code,
                score_date=date.today(),
                total_score=score_100.get("total_score"),
                # 8维度分数
                valuation_score=details.get("valuation", {}).get("score"),
                performance_score=details.get("performance", {}).get("score"),
                risk_score=details.get("risk_control", {}).get("score"),
                momentum_score=details.get("momentum", {}).get("score"),
                sentiment_score=details.get("sentiment", {}).get("score"),
                sector_score=details.get("sector", {}).get("score"),
                manager_score=details.get("manager", {}).get("score"),
                liquidity_score=details.get("liquidity", {}).get("score"),
                # 8维度原因
                valuation_reason=details.get("valuation", {}).get("reason"),
                performance_reason=details.get("performance", {}).get("reason"),
                risk_reason=details.get("risk_control", {}).get("reason"),
                momentum_reason=details.get("momentum", {}).get("reason"),
                sentiment_reason=details.get("sentiment", {}).get("reason"),
                sector_reason=details.get("sector", {}).get("reason"),
                manager_reason=details.get("manager", {}).get("reason"),
                liquidity_reason=details.get("liquidity", {}).get("reason"),
                # 审计字段
                data_source=audit.get("data_source"),
                data_fetched_at=audit.get("data_fetched_at"),
                calculation_version=audit.get("calculation_version"),
                dimension_inputs={
                    dim: details.get(dim, {}).get("input", {})
                    for dim in ["valuation", "performance", "risk_control", "momentum", "sentiment", "sector", "manager", "liquidity"]
                    if details.get(dim, {}).get("input")
                },
            )
        except Exception as e:
            logger.warning(f"Failed to save score to DB for {fund_code}: {e}")

    return {
        "fund_code": fund_code,
        "fund_name": name,
        "nav": nav,
        "estimate_nav": estimated_nav,
        "daily_change": estimated_change,
        "date": fund_data.get("update_time"),
        "trend": trend,
        "summary": summary,
        "score_100": score_100,
    }


def get_fund_detail_info(code: str, use_cache: bool = True) -> dict:
    """Get detailed fund information"""
    try:
        fund_data = fetch_fund_data(code, use_cache=use_cache)
        detail_data = fetch_fund_detail(code)

        raw_html = detail_data.get("raw_html", "")
        syl_1n_match = re.search(r'syl_1n="([^"]+)"', raw_html)
        syl_3y_match = re.search(r'syl_3y="([^"]+)"', raw_html)
        syl_1y_match = re.search(r'syl_1y="([^"]+)"', raw_html)

        def safe_float(match, default: float = 0.0) -> float:
            return float(match.group(1)) if match and match.group(1) else default

        fund_name = fund_data.get("name", "")
        risk_metrics = calculate_risk_metrics(
            safe_float(syl_1y_match),
            safe_float(syl_3y_match),
            safe_float(syl_1n_match),
            fund_name,
        )

        return {
            "fund_code": code,
            "fund_name": fund_name,
            "nav": fund_data.get("nav"),
            "estimate_nav": fund_data.get("estimated_nav"),
            "daily_change": fund_data.get("estimated_change"),
            "date": fund_data.get("update_time"),
            "return_1w": detail_data.get("syl_1z"),
            "return_1m": detail_data.get("syl_1y"),
            "return_3m": detail_data.get("syl_3y"),
            "return_6m": detail_data.get("syl_6y"),
            "return_1y": detail_data.get("syl_1n"),
            "fee_rate": detail_data.get("fund_Rate"),
            "risk_metrics": risk_metrics,
        }
    except Exception as e:
        return {"error": str(e), "fund_code": code}


def generate_100_score(fund_code: str, daily_change: float = 0.0, use_cache: bool = False) -> dict:
    """Generate 100-point score - real-time first, fallback to stored"""
    # 1. 优先实时计算
    try:
        from src.services.score_service import get_score_service
        service = get_score_service()
        result = service.calculate_score(fund_code, use_cache=use_cache)
        if result and "error" not in result:
            logger.info(f"实时评分成功: {fund_code} (score: {result.get('total_score')})")
            result["data_freshness"] = "realtime"
            result["error"] = None  # 清除可能的错误
            return result
        elif result and "error" in result:
            logger.warning(f"实时评分失败: {fund_code} ({result.get('error')})")
            # 实时计算失败，尝试使用历史数据
    except Exception as e:
        logger.error(f"实时评分异常: {fund_code} ({e})")
    
    # 2. 实时计算失败，使用历史数据作为后备
    try:
        from db.fund_ops import get_fund_score
        stored_score = get_fund_score(fund_code)
        if stored_score:
            logger.info(f"使用历史评分: {fund_code} (date: {stored_score.get('score_date')})")
            result = _format_stored_score(stored_score)
            result["data_freshness"] = "stored"
            result["calculation_error"] = "实时计算失败，使用历史数据"
            return result
    except Exception as e:
        logger.error(f"获取历史评分也失败: {fund_code} ({e})")
    
    # 3. 全部失败
    return {"error": "实时计算和历史数据均不可用", "total_score": 0, "grade": "E"}


def _format_stored_score(stored: dict) -> dict:
    """将数据库存储的评分格式化为API响应格式"""
    return {
        "total_score": stored.get("total_score", 0),
        "grade": stored.get("grade", "E"),
        "details": {
            "valuation": {
                "score": stored.get("valuation_score", 0),
                "reason": stored.get("valuation_reason", ""),
            },
            "performance": {
                "score": stored.get("performance_score", 0),
                "reason": stored.get("performance_reason", ""),
            },
            "risk_control": {
                "score": stored.get("risk_control_score", 0),
                "reason": stored.get("risk_control_reason", ""),
            },
            "momentum": {
                "score": stored.get("momentum_score", 0),
                "reason": stored.get("momentum_reason", ""),
            },
            "sentiment": {
                "score": stored.get("sentiment_score", 0),
                "reason": stored.get("sentiment_reason", ""),
            },
            "sector": {
                "score": stored.get("sector_score", 0),
                "reason": stored.get("sector_reason", ""),
            },
            "manager": {
                "score": stored.get("manager_score", 0),
                "reason": stored.get("manager_reason", ""),
            },
            "liquidity": {
                "score": stored.get("liquidity_score", 0),
                "reason": stored.get("liquidity_reason", ""),
            },
        },
        "breakdown": {
            "valuation": {"score": stored.get("valuation_score", 0), "reason": stored.get("valuation_reason", "")},
            "performance": {"score": stored.get("performance_score", 0), "reason": stored.get("performance_reason", "")},
            "risk_control": {"score": stored.get("risk_control_score", 0), "reason": stored.get("risk_control_reason", "")},
            "momentum": {"score": stored.get("momentum_score", 0), "reason": stored.get("momentum_reason", "")},
            "sentiment": {"score": stored.get("sentiment_score", 0), "reason": stored.get("sentiment_reason", "")},
            "sector": {"score": stored.get("sector_score", 0), "reason": stored.get("sector_reason", "")},
            "manager": {"score": stored.get("manager_score", 0), "reason": stored.get("manager_reason", "")},
            "liquidity": {"score": stored.get("liquidity_score", 0), "reason": stored.get("liquidity_reason", "")},
        },
        "audit": {
            "data_source": "stored",
            "calculation_time": str(stored.get("created_at", "")),
            "score_date": str(stored.get("score_date", "")),
        },
    }


def format_100_score_report(fund_code: str) -> str:
    """Format 100 score report"""
    fund_data = fetch_fund_data(fund_code)
    fund_name = fund_data.get("name", fund_code)
    daily_change = float(fund_data.get("estimated_change", 0) or fund_data.get("estimated_change_percent", 0) or 0)
    scoring = generate_100_score(fund_code, daily_change)
    if "error" in scoring:
        return f"获取评分失败: {scoring['error']}"
    return f"📊 {fund_name} 评分: {scoring['total_score']}/100 ({scoring['grade']}级)"
