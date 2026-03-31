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
    """Generate 100-point score using unified scoring service"""
    try:
        from src.services.score_service import get_score_service

        service = get_score_service()
        return service.calculate_score(fund_code, use_cache=use_cache)
    except Exception as e:
        logger.error(f"Generate 100 score error: {e}")
        return {"error": str(e)}


def format_100_score_report(fund_code: str) -> str:
    """Format 100 score report"""
    fund_data = fetch_fund_data(fund_code)
    fund_name = fund_data.get("name", fund_code)
    daily_change = float(fund_data.get("estimated_change", 0) or fund_data.get("estimated_change_percent", 0) or 0)
    scoring = generate_100_score(fund_code, daily_change)
    if "error" in scoring:
        return f"获取评分失败: {scoring['error']}"
    return f"📊 {fund_name} 评分: {scoring['total_score']}/100 ({scoring['grade']}级)"
