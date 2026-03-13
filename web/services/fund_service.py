"""
Fund service layer for business logic
Separates business logic from HTTP handling
"""

import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.fetcher import fetch_fund_data
from src.advice import (
    analyze_fund,
    generate_daily_report,
    generate_advice,
    get_fund_detail_info,
)

logger = logging.getLogger(__name__)


# ============== Fund Services ==============
def get_funds_for_user(holdings: List[Dict], default_codes: List[str] = None) -> List[Dict]:
    """
    Get fund data for display

    Args:
        holdings: User's holdings
        default_codes: Default fund codes if no holdings

    Returns:
        list: Analyzed fund data
    """
    if default_codes is None:
        default_codes = ["000001", "110022", "161725"]

    if holdings:
        codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
        if not codes:
            codes = default_codes
    else:
        codes = default_codes

    funds = []
    for code in codes:
        data = fetch_fund_data(code)
        analysis = analyze_fund(data)
        if "error" not in analysis:
            funds.append(analysis)

    return funds


def get_report_for_user(holdings: List[Dict], default_codes: List[str] = None) -> Dict:
    """Generate daily report for user"""
    if default_codes is None:
        default_codes = ["000001", "110022", "161725"]

    if holdings:
        codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
        if not codes:
            codes = default_codes
    else:
        codes = default_codes

    return generate_daily_report(codes)


def get_advice_for_user(holdings: List[Dict], holdings_dict: Dict = None, default_codes: List[str] = None) -> Dict:
    """
    Generate investment advice for user

    Args:
        holdings: User's holdings
        holdings_dict: Holdings as dict keyed by code
        default_codes: Default fund codes

    Returns:
        dict: Investment advice
    """
    if default_codes is None:
        default_codes = ["000001", "110022", "161725"]

    if holdings_dict is None:
        holdings_dict = {h["code"]: h for h in holdings}

    if holdings:
        codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
        if not codes:
            return {"action": "empty", "advice": "暂无持仓，请先添加持仓", "holdings": []}
    else:
        codes = default_codes
        holdings_dict = {}

    report = generate_daily_report(codes)
    advice = generate_advice(report.get("funds", []))

    # Add holdings info to advice
    advice["holdings"] = []
    for fund in report.get("funds", []):
        code = fund.get("fund_code")
        h = holdings_dict.get(code, {})
        advice["holdings"].append(
            {
                "code": code,
                "name": fund.get("fund_name"),
                "amount": h.get("amount", 0),
                "change": fund.get("daily_change", 0),
            }
        )

    return advice


def get_portfolio_analysis(holdings: List[Dict], holdings_dict: Dict = None, default_codes: List[str] = None) -> Dict:
    """Get portfolio analysis"""
    if default_codes is None:
        default_codes = ["000001", "110022", "161725"]

    if holdings_dict is None:
        holdings_dict = {h["code"]: h for h in holdings}

    if holdings:
        codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
        if not codes:
            return {"message": "暂无持仓，无法分析"}
    else:
        holdings_dict = {}
        codes = default_codes

    # Get detailed info for each fund in parallel
    funds_detail = []
    total_amount = 0

    def fetch_and_enrich(code):
        detail = get_fund_detail_info(code)
        h = holdings_dict.get(code, {})
        amount = h.get("amount", 0)
        
        if detail.get("fund_code"):
            detail["amount"] = amount
            detail["buy_nav"] = h.get("buyNav")
            detail["buy_date"] = h.get("buyDate")
            
            # Calculate holding profit
            if amount > 0 and h.get("buyNav") and detail.get("nav"):
                try:
                    current_nav = float(detail["nav"])
                    buy_nav = float(h["buyNav"])
                    profit_pct = (current_nav - buy_nav) / buy_nav * 100
                    detail["holding_profit"] = round(profit_pct, 2)
                    detail["holding_profit_amount"] = round(amount * profit_pct / 100, 2)
                except Exception:
                    pass
        
        return detail, amount

    # Use thread pool for parallel fetching
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_and_enrich, code): code for code in codes}
        for future in as_completed(futures):
            detail, amount = future.result()
            if detail.get("fund_code"):
                funds_detail.append(detail)
                total_amount += amount

    # Analyze portfolio risk
    portfolio_analysis = analyze_portfolio_risk(funds_detail, total_amount)

    # Suggest allocation
    allocation = suggest_allocation(funds_detail)

    return {
        "funds": funds_detail,
        "total_amount": total_amount,
        "risk_metrics": portfolio_analysis,
        "allocation": allocation,
    }


def analyze_portfolio_risk(funds: List[Dict], total_amount: float) -> Dict:
    """Analyze portfolio risk metrics"""
    if not funds or total_amount == 0:
        return {"message": "暂无持仓数据"}

    # Calculate weights
    for fund in funds:
        fund["weight"] = round(fund["amount"] / total_amount * 100, 2) if fund.get("amount") else 0

    # Calculate weighted risk
    total_risk_score = sum(f.get("risk_metrics", {}).get("risk_score", 4) * f.get("weight", 0) for f in funds) / 100

    # Risk level
    if total_risk_score > 6:
        risk_level = "高风险"
    elif total_risk_score > 4:
        risk_level = "中高风险"
    elif total_risk_score > 2:
        risk_level = "中等风险"
    else:
        risk_level = "中低风险"

    # Return analysis
    try:
        avg_return_1y = sum(float(f.get("return_1y", 0) or 0) * f.get("weight", 0) for f in funds) / 100
    except Exception:
        avg_return_1y = 0

    return {
        "risk_level": risk_level,
        "risk_score": round(total_risk_score, 1),
        "avg_return_1y": round(avg_return_1y, 2),
        "fund_count": len(funds),
        "diversification": "良好" if len(funds) >= 5 else "一般" if len(funds) >= 3 else "需分散",
    }


def suggest_allocation(funds: List[Dict]) -> Dict:
    """Suggest asset allocation"""
    if not funds:
        return {"message": "暂无持仓数据"}

    # Categorize by risk level
    high_risk = []
    medium_risk = []
    low_risk = []

    for fund in funds:
        risk = fund.get("risk_metrics", {}).get("risk_level", "中等风险")
        if "高" in risk:
            high_risk.append(fund)
        elif "低" in risk:
            low_risk.append(fund)
        else:
            medium_risk.append(fund)

    # Calculate percentages
    high_pct = len(high_risk) / len(funds) * 100 if funds else 0
    medium_pct = len(medium_risk) / len(funds) * 100 if funds else 0
    low_pct = len(low_risk) / len(funds) * 100 if funds else 0

    # Suggestions
    suggestions = []
    if high_pct > 50:
        suggestions.append("⚠️ 高风险基金占比过高，建议降低至30%以下")
    if low_pct < 20:
        suggestions.append("💡 建议增加低风险基金配置，提高组合稳定性")
    if len(funds) < 3:
        suggestions.append("📊 建议持有3-5只基金分散风险")

    if not suggestions:
        suggestions.append("✅ 当前配置较为合理")

    return {
        "high_risk_pct": round(high_pct, 1),
        "medium_risk_pct": round(medium_pct, 1),
        "low_risk_pct": round(low_pct, 1),
        "suggestions": suggestions,
        "ideal_allocation": {"high_risk": "20-30%", "medium_risk": "40-50%", "low_risk": "30-40%"},
    }


def calculate_summary(funds: List[Dict]) -> Dict:
    """Calculate market summary"""
    up = sum(1 for f in funds if f["trend"] == "up")
    down = sum(1 for f in funds if f["trend"] == "down")
    flat = len(funds) - up - down

    return {
        "total": len(funds),
        "up": up,
        "down": down,
        "flat": flat,
        "sentiment": "乐观" if up > down else "谨慎" if down > up else "平稳",
    }
