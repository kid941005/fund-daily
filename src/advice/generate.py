"""
建议生成模块 - 负责生成投资建议
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from ..analyzer import get_commodity_sentiment, get_market_sentiment
from ..fetcher import fetch_fund_data, fetch_fund_detail

logger = logging.getLogger(__name__)

# ============== 配置常量 ==============
# 组合投资建议配置（区别于 scoring 模块的 SCORE_WEIGHTS）
PORTFOLIO_SCORE_THRESHOLDS = {"BUY": 60, "HOLD": 40, "SELL": 20}
PORTFOLIO_ALLOCATION_RATIOS = {
    "HIGH": 0.375,
    "MEDIUM_HIGH": 0.275,
    "MEDIUM": 0.225,
    "LOW": 0.175,
    "LOWER": 0.125,
    "MINIMAL": 0.075,
    "NONE": 0,
}
PORTFOLIO_WEIGHT_CONFIG = {
    "DAILY_CHANGE": 15,
    "M1_CHANGE": 10,
    "M3_CHANGE": 8,
    "MOMENTUM": 15,
    "TREND": 12,
    "MARKET_SENTIMENT": 12,
    "HOT_SECTOR": 15,
    "COMMODITY": 10,
    "SEASONAL": 8,
    "SHARPE_HIGH": 30,
    "SHARPE_LOW": -25,
    "DRAWDOWN": 15,
    "SCALE": 8,
    "POSITION": 5,
}

# ============== 辅助函数 ==============

SENTIMENT_MAP = {"乐观": 15, "偏多": 10, "平稳": 0, "偏空": -10, "恐慌": -15}
COMMODITY_MAP = {"乐观": 15, "偏多": 10, "平稳": 0, "偏空": -10}


def _fetch_fund_risks(fund_codes: List[str]) -> Dict[str, Dict]:
    """并行获取基金风险指标"""
    result: Dict[str, Dict] = {}

    def fetch_one(code: str) -> tuple:
        try:
            detail = fetch_fund_detail(code)
            return code, detail.get("risk_metrics", {})
        except Exception:
            return code, {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_one, code): code for code in fund_codes}
        for future in as_completed(futures):
            try:
                code, risk = future.result()
                result[code] = risk
            except Exception:
                pass
    return result


def _compute_base_stats(funds: List[Dict]) -> tuple:
    """计算基础统计数据"""
    up_count = sum(1 for f in funds if f.get("trend") == "up")
    down_count = sum(1 for f in funds if f.get("trend") == "down")
    avg_change = sum(f.get("daily_change", 0) for f in funds) / len(funds) if funds else 0
    return up_count, down_count, avg_change


def _compute_risk_profile(funds: List[Dict]) -> tuple:
    """计算组合风险指标"""
    fund_codes = [f.get("fund_code") for f in funds if f.get("fund_code")]
    risks = _fetch_fund_risks(fund_codes)

    total_sharpe = total_drawdown = total_risk = 0
    for risk in risks.values():
        total_sharpe += risk.get("sharpe_ratio", 0)
        total_drawdown += risk.get("estimated_max_drawdown", 0)
        total_risk += risk.get("risk_score", 4)

    count = len(risks) or 1
    return total_sharpe / count, total_drawdown / count, total_risk / count


def _compute_sentiment_score(market_sentiment: str, market_score: float, commodity_sentiment: str) -> int:
    """计算情绪得分"""
    return SENTIMENT_MAP.get(market_sentiment, 0) + int(market_score * 0.5) + COMMODITY_MAP.get(commodity_sentiment, 0)


def _compute_technical_score(up_count: int, down_count: int) -> int:
    """计算技术面得分"""
    score = 0
    if up_count > down_count:
        score += PORTFOLIO_WEIGHT_CONFIG["MOMENTUM"]
    elif down_count > up_count:
        score -= PORTFOLIO_WEIGHT_CONFIG["MOMENTUM"]
    score += (up_count - down_count) * 3
    return max(min(score, 30), -30)


def _determine_action(score: int, avg_profit_pct: float, position_ratio: int) -> str:
    """根据综合评分确定操作建议"""
    if score > 50:
        action = "买入"
    elif score > 30:
        action = "持有"
    elif score > 10:
        action = "持有"
    elif score > -10:
        action = "减仓"
    else:
        action = "卖出"

    # 仓位约束
    if position_ratio >= 80 and action == "买入":
        action = "持有"

    # 止损止盈
    if avg_profit_pct < -30:
        action = "减仓/止损"
    elif avg_profit_pct > 50:
        action = "部分止盈"

    return action


def _get_risk_level(avg_risk: float) -> str:
    """根据平均风险评分确定风险等级"""
    if avg_risk >= 7:
        return "高风险"
    if avg_risk >= 5:
        return "中高风险"
    if avg_risk >= 3:
        return "中等风险"
    return "中低风险"


def _build_advice_text(action: str, sentiment: str) -> str:
    """构建建议文本"""
    if action == "买入":
        return f"市场{sentiment}，建议适当加仓"
    if action == "持有":
        return f"市场平稳，建议继续持有"
    if action == "减仓":
        return f"市场偏谨慎，建议适当减仓"
    if action == "卖出":
        return f"市场情绪较差，建议减仓观望"
    return f"建议{action}"


# ============== 主函数 ==============


def generate_advice(funds: List[Dict]) -> Dict:
    """生成投资建议"""
    if not funds:
        return {"advice": "暂无基金数据", "risk_level": "未知", "action": "观望"}

    # 基础统计
    up_count, down_count, avg_change = _compute_base_stats(funds)

    # 市场情绪
    market = get_market_sentiment()
    market_sentiment = market.get("sentiment", "平稳")
    market_score = market.get("score", 0)
    commodity = get_commodity_sentiment()
    commodity_sentiment = commodity.get("sentiment", "平稳")
    commodity_score = commodity.get("score", 0)

    # 风险指标
    avg_sharpe, avg_drawdown, avg_risk = _compute_risk_profile(funds)

    # 热点行业
    try:
        from ..fetcher import fetch_hot_sectors

        hot_sectors = fetch_hot_sectors(5) or []
    except Exception:
        hot_sectors = []

    # 基金类型分布
    fund_types: Dict[str, int] = {}
    for f in funds:
        name = f.get("fund_name", "")
        if "混合" in name:
            fund_types["混合"] = fund_types.get("混合", 0) + 1
        elif "股票" in name or "指数" in name:
            fund_types["股票"] = fund_types.get("股票", 0) + 1
        elif "债券" in name:
            fund_types["债券"] = fund_types.get("债券", 0) + 1
        else:
            fund_types["其他"] = fund_types.get("其他", 0) + 1

    # 综合评分
    score = _compute_sentiment_score(market_sentiment, market_score, commodity_sentiment)

    # 热点行业加分
    if hot_sectors:
        score += PORTFOLIO_WEIGHT_CONFIG["HOT_SECTOR"]

    # 夏普比率
    if avg_sharpe > 1:
        score += PORTFOLIO_WEIGHT_CONFIG["SHARPE_HIGH"]
    elif avg_sharpe > 0:
        score += 10
    else:
        score += PORTFOLIO_WEIGHT_CONFIG["SHARPE_LOW"]

    # 风险评分
    score += avg_risk * PORTFOLIO_WEIGHT_CONFIG["DRAWDOWN"] / 2

    # 股票型基金权重
    if fund_types.get("股票", 0) > fund_types.get("债券", 0):
        score += 5

    # 平均收益率
    total_profit = sum(float(f.get("return_1y", 0) or 0) for f in funds)
    avg_profit_pct = total_profit / len(funds) if funds else 0

    # 技术面
    technical_score = _compute_technical_score(up_count, down_count)
    if technical_score > 30:
        score += 10
    elif technical_score < -30:
        score -= 10
    else:
        score += technical_score

    # 操作建议
    action = _determine_action(score, avg_profit_pct, position_ratio=50)
    advice = _build_advice_text(action, market_sentiment)

    return {
        "advice": advice,
        "risk_level": _get_risk_level(avg_risk),
        "action": action,
        "up_count": up_count,
        "down_count": down_count,
        "avg_change": round(avg_change, 2),
        "market_sentiment": market_sentiment,
        "market_score": market_score,
        "commodity_sentiment": commodity_sentiment,
        "commodity_score": commodity_score,
        "sharpe_ratio": round(avg_sharpe, 2),
        "max_drawdown": round(avg_drawdown, 2),
        "risk_score": round(avg_risk, 1),
        "technical_score": technical_score,
        "position_ratio": 50,
        "avg_profit_pct": round(avg_profit_pct, 1),
    }


def generate_daily_report(fund_codes: List[str]) -> Dict:
    """Generate daily report for funds"""
    from . import analyze_fund

    funds = []
    for code in fund_codes:
        data = fetch_fund_data(code)
        if data and not data.get("error"):
            funds.append(analyze_fund(data))

    if not funds:
        return {"error": "No data"}

    advice = generate_advice(funds)

    return {
        "date": funds[0].get("date", ""),
        "funds": funds,
        "advice": advice,
    }


def format_report_for_share(report: Dict) -> str:
    """Format report for sharing"""
    lines = ["📊 基金日报", ""]

    advice = report.get("advice", {})
    funds = report.get("funds", [])

    lines.append(f"市场: {advice.get('market_sentiment', '平稳')}")
    lines.append(f"建议: {advice.get('action', '观望')}")
    lines.append("")

    for f in funds[:5]:
        change = f.get("daily_change", 0)
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        lines.append(f"{emoji} {f.get('fund_name', '')}: {change:+.2f}%")

    return "\n".join(lines)


__all__ = [
    "generate_advice",
    "generate_daily_report",
    "format_report_for_share",
    "PORTFOLIO_SCORE_THRESHOLDS",
    "PORTFOLIO_ALLOCATION_RATIOS",
    "PORTFOLIO_WEIGHT_CONFIG",
]
