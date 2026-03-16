"""
Advice module - 投资建议模块
提供基金分析、建议生成、评分等功能
"""

from .generate import (
    generate_advice, 
    generate_daily_report,
    format_report_for_share,
    ADVICE_SCORE_THRESHOLDS as SCORE_THRESHOLDS, 
    ADVICE_ALLOCATION_RATIOS as ALLOCATION_RATIOS, 
    ADVICE_WEIGHT_CONFIG as WEIGHT_CONFIG
)
from ..fetcher import fetch_fund_data, fetch_fund_detail, fetch_fund_manager, fetch_fund_scale
from ..analyzer import calculate_risk_metrics, get_market_sentiment, get_commodity_sentiment

# 保留原有函数以保持兼容性
from .generate import generate_advice as _generate_advice_old

# 导入技术分析
from typing import Dict, List, Optional


def analyze_fund(fund_data: Dict) -> Dict:
    """Analyze fund data"""
    if "error" in fund_data:
        return {"error": fund_data["error"]}
    if not fund_data.get("fundcode"):
        return {"error": "No fund data available"}
    
    gszzl = float(fund_data.get("gszzl", 0))
    trend = "up" if gszzl > 0 else "down" if gszzl < 0 else "flat"
    
    # 生成summary
    name = fund_data.get("name", "Unknown")
    nav = fund_data.get("dwjz", "N/A")
    if gszzl > 3:
        summary = f"🚀 {name} 大涨 {gszzl}%，净值 {nav}"
    elif gszzl > 1:
        summary = f"📈 {name} 上涨 {gszzl}%，净值 {nav}"
    elif gszzl > -1:
        summary = f"➖ {name} 平盘 {gszzl}%，净值 {nav}"
    elif gszzl > -3:
        summary = f"📉 {name} 下跌 {gszzl}%，净值 {nav}"
    else:
        summary = f"🔻 {name} 大跌 {gszzl}%，净值 {nav}"
    
    fund_code = fund_data.get("fundcode")
    
    # 生成100分制评分
    score_100 = {}
    try:
        from . import generate_100_score
        score_100 = generate_100_score(fund_code, gszzl) or {}
    except Exception as e:
        print(f"Error generating score for {fund_code}: {e}")
    
    return {
        "fund_code": fund_code,
        "fund_name": name,
        "nav": nav,
        "estimate_nav": fund_data.get("gsz"),
        "daily_change": gszzl,
        "date": fund_data.get("jzrq"),
        "trend": trend,
        "summary": summary,
        "score_100": score_100,
    }


def get_fund_detail_info(code: str) -> Dict:
    """Get detailed fund information"""
    try:
        fund_data = fetch_fund_data(code)
        detail_data = fetch_fund_detail(code)
        
        import re
        syl_1n = re.search(r'syl_1n="([^"]+)"', detail_data.get("raw_html", ""))
        syl_3y = re.search(r'syl_3y="([^"]+)"', detail_data.get("raw_html", ""))
        syl_1y = re.search(r'syl_1y="([^"]+)"', detail_data.get("raw_html", ""))

        fund_name = fund_data.get("name", "")
        risk_metrics = calculate_risk_metrics(
            float(syl_1y.group(1)) if syl_1y and syl_1y.group(1) else 0,
            float(syl_3y.group(1)) if syl_3y and syl_3y.group(1) else 0,
            float(syl_1n.group(1)) if syl_1n and syl_1n.group(1) else 0,
            fund_name,
        )

        return {
            "fund_code": code,
            "fund_name": fund_data.get("name", ""),
            "nav": fund_data.get("dwjz"),
            "estimate_nav": fund_data.get("gsz"),
            "daily_change": fund_data.get("gszzl"),
            "date": fund_data.get("jzrq"),
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


def calculate_ma(closes: List[float], period: int) -> Optional[float]:
    """Calculate moving average"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def calculate_macd(closes: List[float]) -> Dict:
    """Calculate MACD indicator"""
    if len(closes) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0, "trend": "unknown"}

    def ema(data, period):
        ema_values = []
        multiplier = 2 / (period + 1)
        for i, price in enumerate(data):
            if i < period - 1:
                ema_values.append(sum(data[:period]) / period)
            else:
                ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values

    ema_12 = ema(closes, 12)
    ema_26 = ema(closes, 26)
    macd_line = [ema_12[i] - ema_26[i] for i in range(len(closes))]
    signal_line = ema(macd_line, 9)
    histogram = macd_line[-1] - signal_line[-1] if signal_line else 0

    trend = "neutral"
    if histogram > 0:
        trend = "bullish"
    elif histogram < 0:
        trend = "bearish"

    return {"macd": macd_line[-1], "signal": signal_line[-1], "histogram": histogram, "trend": trend}


def calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate RSI indicator"""
    if len(closes) < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def analyze_technical_indicators(fund_code: str) -> Dict:
    """Analyze technical indicators"""
    return {"ma5": None, "ma10": None, "ma20": None, "macd": {"trend": "neutral"}, "rsi": None, "recommendation": "hold"}


def generate_100_score(fund_code: str, daily_change: float = 0.0) -> Dict:
    """Generate 100-point score"""
    from ..scoring import calculate_total_score
    
    try:
        fund_data = fetch_fund_data(fund_code)
        detail_data = fetch_fund_detail(fund_code)
        risk_metrics = calculate_risk_metrics(
            float(detail_data.get("syl_1y", 0) or 0),
            float(detail_data.get("syl_3y", 0) or 0),
            float(detail_data.get("syl_1n", 0) or 0),
            fund_data.get("name", ""),
        )
        
        market = get_market_sentiment()
        commodity = get_commodity_sentiment()
        
        from ..fetcher import fetch_hot_sectors, fetch_market_news, fetch_fund_manager, fetch_fund_scale
        hot_sectors = fetch_hot_sectors(5)
        news = fetch_market_news(10)
        fund_manager = fetch_fund_manager(fund_code)
        fund_scale = fetch_fund_scale(fund_code)
        
        fund_data_dict = {
            "return_1m": float(detail_data.get("syl_1y", 0) or 0),
            "return_3m": float(detail_data.get("syl_3y", 0) or 0),
            "return_6m": float(detail_data.get("syl_6y", 0) or 0),
            "return_1y": float(detail_data.get("syl_1n", 0) or 0),
            "daily_change": float(daily_change) if daily_change else 0,
        }
        
        scoring = calculate_total_score(
            fund_detail=detail_data,
            risk_metrics=risk_metrics,
            market_sentiment=market.get("sentiment", "平稳"),
            market_score=market.get("score", 0),
            news=news,
            hot_sectors=hot_sectors,
            commodity_sentiment=commodity.get("sentiment", "平稳"),
            fund_manager=fund_manager,
            fund_type=fund_data.get("name", ""),
            fund_scale=fund_scale,
            daily_change=daily_change,
            fund_data=fund_data_dict,
            fund_code=fund_code,  # 传入fund_code用于缓存
        )
        
        return scoring
    except Exception as e:
        logger.error(f"Generate 100 score error: {e}")
        return {"error": str(e)}


def format_100_score_report(fund_code: str) -> str:
    """Format 100 score report"""
    fund_data = fetch_fund_data(fund_code)
    fund_name = fund_data.get("name", fund_code)
    daily_change = float(fund_data.get("gszzl", 0) or 0)
    
    scoring = generate_100_score(fund_code, daily_change)
    
    if "error" in scoring:
        return f"获取评分失败: {scoring['error']}"
    
    details = scoring["details"]
    return f"📊 {fund_name} 评分: {scoring['total_score']}/100 ({scoring['grade']}级)"


__all__ = [
    "analyze_fund",
    "generate_daily_report",
    "format_report_for_share",
    "generate_advice", 
    "get_fund_detail_info",
    "analyze_technical_indicators",
    "generate_100_score",
    "format_100_score_report",
    "calculate_ma",
    "calculate_macd",
    "calculate_rsi",
    "SCORE_THRESHOLDS",
    "ALLOCATION_RATIOS", 
    "WEIGHT_CONFIG",
]
