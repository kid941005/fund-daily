"""
建议生成模块 - 负责生成投资建议
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..fetcher import fetch_fund_data, fetch_fund_detail, fetch_fund_manager, fetch_fund_scale
from ..analyzer import calculate_risk_metrics, get_market_sentiment, get_commodity_sentiment

logger = logging.getLogger(__name__)

# ============== 配置常量 ==============
ADVICE_SCORE_THRESHOLDS = {"BUY": 60, "HOLD": 40, "SELL": 20}
ADVICE_ALLOCATION_RATIOS = {
    "HIGH": 0.375, "MEDIUM_HIGH": 0.275, "MEDIUM": 0.225,
    "LOW": 0.175, "LOWER": 0.125, "MINIMAL": 0.075, "NONE": 0
}
# 评分权重配置 - 增加区分度
ADVICE_WEIGHT_CONFIG = {
    # 涨跌类 - 扩大差距
    "DAILY_CHANGE": 15, "M1_CHANGE": 10, "M3_CHANGE": 8,
    # 动量趋势
    "MOMENTUM": 15, "TREND": 12, 
    # 市场情绪
    "MARKET_SENTIMENT": 12, "HOT_SECTOR": 15, 
    # 商品和季节性
    "COMMODITY": 10, "SEASONAL": 8,
    # 风险调整收益 - 扩大差距
    "SHARPE_HIGH": 30, "SHARPE_LOW": -25, "DRAWDOWN": 15, 
    # 规模和流动性
    "SCALE": 8, "POSITION": 5
}


def generate_advice(funds: List[Dict]) -> Dict:
    """
    Generate investment advice based on fund performance and market indicators
    
    Args:
        funds: List of analyzed fund data
        
    Returns:
        dict: Investment advice
    """
    if not funds:
        return {"advice": "暂无基金数据", "risk_level": "未知", "action": "观望"}

    # 基础统计
    up_count = sum(1 for f in funds if f.get("trend") == "up")
    down_count = sum(1 for f in funds if f.get("trend") == "down")
    total = len(funds)

    avg_change = sum(f.get("daily_change", 0) for f in funds) / total if total > 0 else 0

    # 获取市场情绪
    market = get_market_sentiment()
    market_sentiment = market.get("sentiment", "平稳")
    market_score = market.get("score", 0)

    # 获取大宗商品情绪
    commodity = get_commodity_sentiment()

    # 计算组合加权指标（并行获取基金详情）
    total_sharpe = 0
    total_drawdown = 0
    total_risk_score = 0
    funds_with_risk = 0

    # 并行获取所有基金详情
    fund_codes = [f.get("fund_code") for f in funds if f.get("fund_code")]
    
    def fetch_risk(code):
        try:
            return fetch_fund_detail(code)
        except Exception:
            return {}
    
    # 使用线程池并行获取，最多5个线程
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_risk, code): code for code in fund_codes}
        for future in as_completed(futures):
            try:
                detail = future.result()
                risk = detail.get("risk_metrics", {})
                if risk:
                    total_sharpe += risk.get("sharpe_ratio", 0)
                    total_drawdown += risk.get("estimated_max_drawdown", 0)
                    total_risk_score += risk.get("risk_score", 4)
                    funds_with_risk += 1
            except Exception:
                pass

    if funds_with_risk > 0:
        avg_sharpe = total_sharpe / funds_with_risk
        avg_drawdown = total_drawdown / funds_with_risk
        avg_risk = total_risk_score / funds_with_risk
    else:
        avg_sharpe = 0
        avg_drawdown = 0
        avg_risk = 4

    # 计算技术评分
    technical_score = 0
    up_funds = [f for f in funds if f.get("trend") == "up"]
    down_funds = [f for f in funds if f.get("trend") == "down"]

    if len(up_funds) > len(down_funds):
        technical_score += ADVICE_WEIGHT_CONFIG["MOMENTUM"]
    elif len(down_funds) > len(up_funds):
        technical_score -= 10

    # 行业轮动分析
    hot_sectors = []
    try:
        from ..fetcher import fetch_hot_sectors
        hot_sectors = fetch_hot_sectors(5) or []
    except Exception:
        pass

    # 大宗商品
    commodity_sentiment = commodity.get("sentiment", "平稳")
    commodity_score = commodity.get("score", 0)

    # 基金类型分析
    fund_types = {}
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

    # 核心评分计算
    score = 0
    
    # 1. 市场情绪
    sentiment_map = {"乐观": 15, "偏多": 10, "平稳": 0, "偏空": -10, "恐慌": -15}
    score += sentiment_map.get(market_sentiment, 0)
    score += market_score * 0.5

    # 2. 大宗商品
    commodity_map = {"乐观": 15, "偏多": 10, "平稳": 0, "偏空": -10}
    score += commodity_map.get(commodity_sentiment, 0)

    # 3. 涨跌分布
    if up_count > down_count:
        score += ADVICE_WEIGHT_CONFIG["MOMENTUM"]
    elif down_count > up_count:
        score -= ADVICE_WEIGHT_CONFIG["MOMENTUM"]

    # 4. 行业热点
    if hot_sectors:
        score += ADVICE_WEIGHT_CONFIG["HOT_SECTOR"]

    # 5. 仓位
    position_ratio = 50  # 简化

    # 6. 夏普比率
    if avg_sharpe > 1:
        score += ADVICE_WEIGHT_CONFIG["SHARPE_HIGH"]
    elif avg_sharpe > 0:
        score += 10
    else:
        score += ADVICE_WEIGHT_CONFIG["SHARPE_LOW"]

    # 7. 风险评分
    score += avg_risk * ADVICE_WEIGHT_CONFIG["DRAWDOWN"] / 2

    # 8. 基金类型权重
    if fund_types.get("股票", 0) > fund_types.get("债券", 0):
        score += 5

    # 9. 计算平均收益
    total_profit = 0
    count = 0
    for f in funds:
        try:
            profit = float(f.get("return_1y", 0) or 0)
            total_profit += profit
            count += 1
        except Exception:
            pass
    
    avg_profit_pct = total_profit / count if count > 0 else 0

    # 10. 技术分析
    technical_score += (up_count - down_count) * 3
    if technical_score > 30:
        score += 10
    elif technical_score < -30:
        score -= 10
    else:
        score += max(technical_score, -30)

    # 确定操作建议
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

    # 边界条件判断
    if position_ratio >= 100 and action == "买入":
        action = "持有"
    elif position_ratio >= 80 and action == "买入":
        action = "持有"

    # 止损止盈
    if avg_profit_pct < -30:
        action = "减仓/止损"
    elif avg_profit_pct > 50:
        action = "部分止盈"

    # 生成建议文本
    advice = _build_advice_text(action, score, market_sentiment, avg_change, up_count, down_count)

    # 风险等级
    if avg_risk >= 7:
        risk_level = "高风险"
    elif avg_risk >= 5:
        risk_level = "中高风险"
    elif avg_risk >= 3:
        risk_level = "中等风险"
    else:
        risk_level = "中低风险"

    return {
        "advice": advice,
        "risk_level": risk_level,
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
        "position_ratio": position_ratio,
        "avg_profit_pct": round(avg_profit_pct, 1),
    }


def _build_advice_text(action: str, score: int, sentiment: str, avg_change: float, up: int, down: int) -> str:
    """构建建议文本"""
    if action == "买入":
        return f"市场{sentiment}，建议适当加仓"
    elif action == "持有":
        return f"市场平稳，建议继续持有"
    elif action == "减仓":
        return f"市场偏谨慎，建议适当减仓"
    elif action == "卖出":
        return f"市场情绪较差，建议减仓观望"
    else:
        return f"建议{action}"


__all__ = ["generate_advice", "ADVICE_SCORE_THRESHOLDS", "ADVICE_ALLOCATION_RATIOS", "ADVICE_WEIGHT_CONFIG"]


# ============== 额外函数 ==============
def generate_daily_report(fund_codes: List[str]) -> Dict:
    """Generate daily report for funds"""
    from ..fetcher import fetch_fund_data
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


# 修复循环导入
def _generate_daily_report_internal(fund_codes: List[str]) -> Dict:
    """Internal function to generate daily report"""
    from ..fetcher import fetch_fund_data
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
