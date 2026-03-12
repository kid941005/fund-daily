"""
Advice generation module for Fund Daily
Generates investment advice based on fund performance and market indicators
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from ..fetcher import fetch_fund_data, fetch_fund_detail
from ..analyzer import calculate_risk_metrics

logger = logging.getLogger(__name__)


# ============== Fund Analysis ==============
def analyze_fund(fund_data: Dict) -> Dict:
    """
    Analyze fund data and generate insights
    
    Args:
        fund_data: Raw fund data from fetcher
        
    Returns:
        dict: Analyzed fund data
    """
    if "error" in fund_data:
        return {"error": fund_data["error"]}
    
    if not fund_data.get("fundcode"):
        return {"error": "No fund data available"}
    
    try:
        gszzl = float(fund_data.get("gszzl", 0))
    except:
        gszzl = 0
    
    analysis = {
        "fund_code": fund_data.get("fundcode"),
        "fund_name": fund_data.get("name"),
        "nav": fund_data.get("dwjz"),
        "estimate_nav": fund_data.get("gsz"),
        "daily_change": gszzl,
        "date": fund_data.get("jzrq"),
        "estimate_date": fund_data.get("gztime"),
        "trend": "up" if gszzl > 0 else "down" if gszzl < 0 else "flat",
        "change_percent": f"{gszzl}%",
        "summary": _generate_summary(fund_data, gszzl)
    }
    
    return analysis


def _generate_summary(fund_data: Dict, change: float) -> str:
    """Generate text summary for a fund"""
    name = fund_data.get("name", "Unknown")
    nav = fund_data.get("dwjz", "N/A")
    
    if change > 3:
        emoji = "🚀"
        desc = "大涨"
    elif change > 1:
        emoji = "📈"
        desc = "上涨"
    elif change > -1:
        emoji = "➖"
        desc = "平盘"
    elif change > -3:
        emoji = "📉"
        desc = "下跌"
    else:
        emoji = "🔻"
        desc = "大跌"
    
    return f"{emoji} {name} 今日{desc} {change}%，净值 {nav}"


# ============== Report Generation ==============
def generate_daily_report(fund_codes: List[str]) -> Dict:
    """
    Generate daily report for multiple funds
    
    Args:
        fund_codes: List of fund codes
        
    Returns:
        dict: Daily report
    """
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "funds": [],
        "summary": {}
    }
    
    up_count = 0
    down_count = 0
    flat_count = 0
    
    for code in fund_codes:
        data = fetch_fund_data(code.strip())
        analysis = analyze_fund(data)
        
        if "error" not in analysis:
            report["funds"].append(analysis)
            
            if analysis["trend"] == "up":
                up_count += 1
            elif analysis["trend"] == "down":
                down_count += 1
            else:
                flat_count += 1
    
    report["summary"] = {
        "total": len(report["funds"]),
        "up": up_count,
        "down": down_count,
        "flat": flat_count,
        "market_sentiment": "乐观" if up_count > down_count else "谨慎" if down_count > up_count else "平稳"
    }
    
    return report


def format_report_for_share(report: Dict) -> str:
    """Format report for sharing"""
    lines = [
        f"📊 每日基金报告 {report['date']}",
        "=" * 40,
        ""
    ]
    
    for fund in report["funds"]:
        lines.append(fund["summary"])
        lines.append(f"   代码: {fund['fund_code']} | 净值: {fund['nav']}")
        if fund.get('estimate_nav'):
            lines.append(f"   估算: {fund['estimate_nav']} ({fund['change_percent']})")
        lines.append("")
    
    lines.append("=" * 40)
    lines.append(f"📈 上涨: {report['summary']['up']} 只")
    lines.append(f"📉 下跌: {report['summary']['down']} 只")
    lines.append(f"➖ 平盘: {report['summary']['flat']} 只")
    lines.append(f"💡 市场情绪: {report['summary']['market_sentiment']}")
    lines.append("")
    lines.append("⚠️ 仅供参考，不构成投资建议")
    
    return "\n".join(lines)


# ============== Advice Generation ==============
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
    up_count = sum(1 for f in funds if f.get('trend') == 'up')
    down_count = sum(1 for f in funds if f.get('trend') == 'down')
    total = len(funds)
    
    avg_change = sum(f.get('daily_change', 0) for f in funds) / total if total > 0 else 0
    
    # 获取市场情绪
    market = get_market_sentiment()
    market_sentiment = market.get('sentiment', '平稳')
    market_score = market.get('score', 0)
    
    # 计算组合加权指标
    total_sharpe = 0
    total_drawdown = 0
    total_risk_score = 0
    funds_with_risk = 0
    
    for f in funds:
        code = f.get('fund_code')
        if code:
            try:
                detail = fetch_fund_detail(code)
                risk = detail.get('risk_metrics', {})
                if risk:
                    total_sharpe += risk.get('sharpe_ratio', 0)
                    total_drawdown += risk.get('estimated_max_drawdown', 0)
                    total_risk_score += risk.get('risk_score', 4)
                    funds_with_risk += 1
            except:
                pass
    
    if funds_with_risk > 0:
        avg_sharpe = total_sharpe / funds_with_risk
        avg_drawdown = total_drawdown / funds_with_risk
        avg_risk = total_risk_score / funds_with_risk
    else:
        avg_sharpe = 0
        avg_drawdown = 0
        avg_risk = 4
    
    drawdown_days = int(avg_drawdown * 2) if avg_drawdown > 0 else 0
    drawdown_days = min(drawdown_days, 30)
    
    # 估算仓位和收益率
    total_value = sum(f.get('amount', f.get('total_value', 0)) for f in funds)
    total_cost = sum(f.get('amount', 0) * 0.8 for f in funds)
    avg_profit_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    position_ratio = (total_value / 1000000 * 100) if total_value > 0 else 0
    
    # 综合评分
    score = 0
    
    # 市场情绪权重
    if market_sentiment in ['乐观', '偏多']:
        score += 30
    elif market_sentiment == '平稳':
        score += 10
    elif market_sentiment in ['偏空', '恐慌']:
        score -= 30
    
    # 基金当日表现
    score += avg_change * 10
    
    # 夏普比率
    if avg_sharpe > 1:
        score += 20
    elif avg_sharpe > 0.5:
        score += 10
    elif avg_sharpe < 0:
        score -= 15
    
    # 最大回撤
    if avg_drawdown > 20:
        score -= 20
    elif avg_drawdown > 10:
        score -= 10
    elif avg_drawdown < 5:
        score += 10
    
    # 确定操作建议
    if score > 40:
        advice = "市场情绪乐观，基金表现良好，适合适度加仓"
        action = "买入"
    elif score > 20:
        advice = "市场偏多，建议继续持有，可少量加仓"
        action = "持有"
    elif score > -10:
        advice = "市场整体平稳，建议保持当前配置"
        action = "持有"
    elif score > -30:
        advice = "市场偏谨慎，注意风险，可适当减仓"
        action = "减仓"
    else:
        advice = "市场情绪偏空，建议减仓观望，等待机会"
        action = "卖出"
    
    # 边界条件判断
    if position_ratio >= 90 and action == "买入":
        action = "持有"
        advice = f"⚠️ 当前仓位约{position_ratio:.0f}%已较高，建议持有为主"
    elif position_ratio >= 70 and action == "买入":
        advice += "（仓位较高，请谨慎加仓）"
    
    if avg_profit_pct < -30:
        action = "减仓/止损"
        advice = f"⚠️ 平均亏损{abs(avg_profit_pct):.1f}%，建议止损或减仓"
    elif avg_profit_pct < -15:
        if action == "买入":
            action = "持有"
            advice = f"亏损{abs(avg_profit_pct):.1f}%，建议轻仓摊低成本"
    elif avg_profit_pct > 30:
        if action == "持有":
            advice += "（收益较高，可考虑部分止盈）"
    
    if avg_risk >= 7:
        risk_level = "高风险"
    elif avg_risk >= 5:
        risk_level = "中高风险"
    elif avg_risk >= 3:
        risk_level = "中等风险"
    else:
        risk_level = "中低风险"
    
    if avg_risk >= 7 and action in ["买入", "持有"]:
        advice += "（⚠️ 组合风险较高）"
    
    # 大宗商品信息
    commodity = get_commodity_sentiment()
    
    commodity_info = []
    for name, data in commodity.get('details', {}).items():
        change = data.get('change', 0) or 0
        price = data.get('price', 'N/A')
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        commodity_info.append(f"{emoji}{data.get('name', name)}: {change:+.2f}%")
    
    commodity_desc = " | ".join(commodity_info) if commodity_info else "暂无"
    
    return {
        "advice": advice,
        "risk_level": risk_level,
        "action": action,
        "up_count": up_count,
        "down_count": down_count,
        "avg_change": round(avg_change, 2),
        "market_sentiment": market_sentiment,
        "market_score": market_score,
        "commodity_sentiment": commodity.get('sentiment', '平稳'),
        "commodity_score": commodity.get('score', 0),
        "commodity_details": commodity.get('details', {}),
        "commodity_desc": commodity_desc,
        "sharpe_ratio": round(avg_sharpe, 2),
        "max_drawdown": round(avg_drawdown, 2),
        "drawdown_days": drawdown_days,
        "risk_score": round(avg_risk, 1),
        "position_ratio": round(position_ratio, 1),
        "avg_profit_pct": round(avg_profit_pct, 1),
        "total_value": round(total_value, 2)
    }


# ============== Fund Detail ==============
def get_fund_detail_info(code: str) -> Dict:
    """
    Get detailed fund information including risk metrics
    
    Args:
        code: Fund code
        
    Returns:
        dict: Detailed fund info
    """
    try:
        fund_data = fetch_fund_data(code)
        detail_data = fetch_fund_detail(code)
        
        import re
        
        # Extract metrics
        syl_1n = re.search(r'syl_1n="([^"]+)"', detail_data.get('raw_html', ''))
        syl_6y = re.search(r'syl_6y="([^"]+)"', detail_data.get('raw_html', ''))
        syl_3y = re.search(r'syl_3y="([^"]+)"', detail_data.get('raw_html', ''))
        syl_1y = re.search(r'syl_1y="([^"]+)"', detail_data.get('raw_html', ''))
        
        # Calculate risk metrics
        risk_metrics = calculate_risk_metrics(
            float(syl_1y.group(1)) if syl_1y and syl_1y.group(1) else 0,
            float(syl_3y.group(1)) if syl_3y and syl_3y.group(1) else 0,
            float(syl_1n.group(1)) if syl_1n and syl_1n.group(1) else 0
        )
        
        result = {
            "fund_code": code,
            "fund_name": fund_data.get("name", ""),
            "nav": fund_data.get("dwjz"),
            "estimate_nav": fund_data.get("gsz"),
            "daily_change": fund_data.get("gszzl"),
            "date": fund_data.get("jzrq"),
            "return_1w": detail_data.get('syl_1z'),
            "return_1m": detail_data.get('syl_1y'),
            "return_3m": detail_data.get('syl_3y'),
            "return_6m": detail_data.get('syl_6y'),
            "return_1y": detail_data.get('syl_1n'),
            "fee_rate": detail_data.get('fund_Rate'),
            "source_rate": detail_data.get('fund_sourceRate'),
            "risk_metrics": risk_metrics
        }
        
        return result
        
    except Exception as e:
        return {"error": str(e), "fund_code": code}
