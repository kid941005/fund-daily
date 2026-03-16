"""
Fund service layer for business logic
Separates business logic from HTTP handling
"""

import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from src.fetcher import fetch_fund_data, fetch_fund_manager, fetch_fund_scale
from src.advice import (
    analyze_fund,
    generate_daily_report,
    generate_advice,
    get_fund_detail_info,
)
from src.analyzer import get_market_sentiment, get_commodity_sentiment
from src.fetcher import fetch_hot_sectors, fetch_market_news
from src.scoring import calculate_total_score
from src.cache.redis_cache import redis_get, redis_set, get_redis_client

logger = logging.getLogger(__name__)

# 缓存 key 前缀
CACHE_PREFIX = "fund_daily:"
MARKET_CACHE_KEY = f"{CACHE_PREFIX}market_data"
MARKET_CACHE_TTL = 300  # 5分钟


def get_cached_market_data() -> Dict:
    """获取缓存的市场数据（先从 Redis 获取，缓存未命中则重新获取）"""
    # 尝试从 Redis 获取
    cached = redis_get(MARKET_CACHE_KEY)
    if cached:
        logger.info("Using cached market data from Redis")
        return cached
    
    # 缓存未命中，获取最新市场数据
    logger.info("Fetching fresh market data...")
    with ThreadPoolExecutor(max_workers=4) as executor:
        market_future = executor.submit(get_market_sentiment)
        commodity_future = executor.submit(get_commodity_sentiment)
        sectors_future = executor.submit(fetch_hot_sectors, 5)
        news_future = executor.submit(fetch_market_news, 10)
        
        market = market_future.result()
        commodity = commodity_future.result()
        sectors = sectors_future.result()
        news = news_future.result()
    
    market_data = {
        "market": market,
        "commodity": commodity,
        "hot_sectors": sectors,
        "news": news
    }
    
    # 写入 Redis 缓存
    redis_set(MARKET_CACHE_KEY, market_data, MARKET_CACHE_TTL)
    
    return market_data


def calculate_fund_score(fund: Dict, fund_code: str) -> Optional[Dict]:
    """
    计算单只基金的100分制评分
    
    Args:
        fund: 基金数据（包含 analyze_fund 结果）
        fund_code: 基金代码
    
    Returns:
        dict: 评分结果
    """
    # 获取市场数据
    market_data = get_cached_market_data()
    market = market_data["market"]
    commodity = market_data["commodity"]
    hot_sectors = market_data["hot_sectors"]
    news = market_data["news"]
    
    # 获取 manager 和 scale（使用缓存）
    fund_manager = fetch_fund_manager(fund_code)
    fund_scale = fetch_fund_scale(fund_code)
    
    # 计算评分
    scoring = calculate_total_score(
        fund_detail=fund,
        risk_metrics=fund.get("risk_metrics", {}),
        market_sentiment=market.get("sentiment", "平稳"),
        market_score=market.get("score", 0),
        news=news,
        hot_sectors=hot_sectors,
        commodity_sentiment=commodity.get("sentiment", "平稳"),
        fund_manager=fund_manager,
        fund_type=fund.get("fund_name", ""),
        fund_scale=fund_scale,
        daily_change=float(fund.get("daily_change", 0) or 0),
        fund_data={
            "return_1m": fund.get("syl_6y", fund.get("return_1m")),
            "return_3m": fund.get("syl_3y", fund.get("return_3m")),
            "return_1y": fund.get("syl_1y", fund.get("return_1y")),
        },
        fund_code=fund_code,
    )
    
    return scoring


def calculate_fund_scores_batch(funds: List[Dict]) -> List[Dict]:
    """
    批量计算多只基金的评分（并行获取 + 复用市场数据）
    
    Args:
        funds: 基金列表（包含 analyze_fund 结果）
    
    Returns:
        list: 带评分的基金列表
    """
    if not funds:
        return []
    
    # 获取市场数据（只获取一次）
    market_data = get_cached_market_data()
    market = market_data["market"]
    commodity = market_data["commodity"]
    hot_sectors = market_data["hot_sectors"]
    news = market_data["news"]
    
    # 收集所有基金代码
    codes = [f.get("fund_code", "") for f in funds if f.get("fund_code")]
    
    # 并行获取所有基金的 manager 和 scale
    manager_cache = {}
    scale_cache = {}
    
    def fetch_info(code):
        try:
            return {
                "code": code,
                "manager": fetch_fund_manager(code),
                "scale": fetch_fund_scale(code),
            }
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"code": code, "manager": None, "scale": 0}
    
    with ThreadPoolExecutor(max_workers=min(5, len(codes))) as executor:
        futures = {executor.submit(fetch_info, code): code for code in codes}
        for future in as_completed(futures):
            result = future.result()
            if result:
                manager_cache[result["code"]] = result["manager"]
                scale_cache[result["code"]] = result["scale"]
    
    # 计算每只基金的评分
    for fund in funds:
        code = fund.get("fund_code", "")
        fund_manager = manager_cache.get(code)
        fund_scale = scale_cache.get(code, 0)
        
        scoring = calculate_total_score(
            fund_detail=fund,
            risk_metrics=fund.get("risk_metrics", {}),
            market_sentiment=market.get("sentiment", "平稳"),
            market_score=market.get("score", 0),
            news=news,
            hot_sectors=hot_sectors,
            commodity_sentiment=commodity.get("sentiment", "平稳"),
            fund_manager=fund_manager,
            fund_type=fund.get("fund_name", ""),
            fund_scale=fund_scale,
            daily_change=float(fund.get("daily_change", 0) or 0),
            fund_data={
                "return_1m": fund.get("syl_6y", fund.get("return_1m")),
                "return_3m": fund.get("syl_3y", fund.get("return_3m")),
                "return_1y": fund.get("syl_1y", fund.get("return_1y")),
            },
            fund_code=code,
        )
        fund["score_100"] = scoring
    
    return funds


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

    # 并行获取基金数据
    funds = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_fund_data, code): code for code in codes}
        for future in as_completed(futures):
            data = future.result()
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
    
    # Inject holdings amount into funds
    funds = report.get("funds", [])
    for fund in funds:
        code = fund.get("fund_code")
        holding = holdings_dict.get(code, {})
        amount = holding.get("amount", 0)
        fund["amount"] = amount
    
    advice = generate_advice(funds)

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

    # 使用缓存的市场数据（只获取一次）
    market_data = get_cached_market_data()
    market = market_data["market"]
    commodity = market_data["commodity"]
    hot_sectors = market_data["hot_sectors"]
    news = market_data["news"]
    
    market_sentiment = market.get("sentiment", "平稳")
    market_score = market.get("score", 0)
    commodity_sentiment = commodity.get("sentiment", "平稳")
    
    # 并行获取所有基金的manager和scale
    # 创建代码到基金的映射
    funds_detail_dict = {f.get("fund_code"): f for f in funds_detail if f.get("fund_code")}
    codes = [f.get("fund_code") for f in funds_detail if f.get("fund_code")]
    
    def fetch_fund_info(code):
        """并行获取单个基金信息"""
        try:
            # 获取基金详细信息
            detail = fetch_fund_detail(code)
            # 合并到 fund 中
            fund = funds_detail_dict.get(code, {})
            for k, v in detail.items():
                if k not in fund:
                    fund[k] = v
            return {
                "code": code,
                "manager": fetch_fund_manager(code),
                "scale": fetch_fund_scale(code),
                "detail": detail,
            }
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"code": code, "manager": None, "scale": 0, "detail": {}}
    
    # 使用线程池并行获取
    manager_cache = {}
    scale_cache = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_fund_info, code): code for code in codes}
        for future in as_completed(futures):
            result = future.result()
            manager_cache[result["code"]] = result["manager"]
            scale_cache[result["code"]] = result["scale"]
    
    for fund in funds_detail:
        try:
            code = fund.get("fund_code", "")
            
            # 使用缓存的manager和scale
            fund_manager = manager_cache.get(code)
            fund_scale = scale_cache.get(code, 0)
            daily_change = float(fund.get("daily_change", 0) or 0)
            
            # Get risk_metrics from fund
            risk_metrics = fund.get("risk_metrics", {})
            
            # 构建基金数据用于差异化评分
            fund_data = {
                "return_1m": fund.get("syl_6y", fund.get("return_1m")),
                "return_3m": fund.get("syl_3y", fund.get("return_3m")),
                "return_1y": fund.get("syl_1y", fund.get("return_1y")),
                "daily_change": fund.get("daily_change"),
            }
            
            scoring = calculate_total_score(
                fund_detail=detail if detail else fund,
                risk_metrics=risk_metrics,
                market_sentiment=market_sentiment,
                market_score=market_score,
                news=news,
                hot_sectors=hot_sectors,
                commodity_sentiment=commodity_sentiment,
                fund_manager=fund_manager,
                fund_type=fund.get("fund_name", ""),
                fund_scale=fund_scale,
                daily_change=daily_change,
                fund_data=fund_data,
                fund_code=code,  # 传入fund_code用于缓存
            )
            fund["score_100"] = scoring
        except Exception as e:
            logger.error(f"Error: {e}")
            fund["score_100"] = {"error": str(e)}

    # 计算总金额和持仓比例
    total_amount = sum(f.get("amount", 0) for f in funds_detail)
    
    # 先计算当前持仓比例
    for fund in funds_detail:
        amount = fund.get("amount", 0)
        fund["current_pct"] = round(amount / total_amount * 100, 1) if total_amount > 0 else 0
    
    # 计算每只基金的评分并排序（去弱留强）
    scored_funds = []
    for fund in funds_detail:
        score = fund.get("score_100", {}).get("total_score", 0)
        amount = fund.get("amount", 0)
        scored_funds.append({
            "fund": fund,
            "score": score,
            "amount": amount
        })
    
    # 根据评分计算目标持仓比例
    if scored_funds:
        total_score = sum(max(f["score"], 0) for f in scored_funds)
        
        if total_score > 0 and total_amount > 0:
            for item in scored_funds:
                fund = item["fund"]
                score = max(item["score"], 0)
                base_ratio = score / total_score
                # 高分基金获得更高权重
                if score >= 60:
                    target_ratio = base_ratio * 1.5
                elif score >= 50:
                    target_ratio = base_ratio * 1.2
                else:
                    target_ratio = base_ratio * 0.8
                # 计算目标金额
                fund["target_amount"] = round(total_amount * target_ratio, 2)
                fund["target_pct"] = round(target_ratio * 100, 1)
        else:
            for item in scored_funds:
                item["fund"]["target_pct"] = round(100 / len(scored_funds), 1)
                item["fund"]["target_amount"] = 0

    # 计算 target_amount
    for item in scored_funds:
        fund = item.get("fund", {})
        if "target_amount" not in fund:
            fund["target_amount"] = 0
        if "target_pct" in fund and total_amount > 0:
            fund["target_amount"] = round(total_amount * fund["target_pct"] / 100, 2)

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
    
    # 基于评分的转换建议
    funds_with_scores = [f for f in funds if f.get("score_100") and f.get("score_100", {}).get("total_score")]
    if len(funds_with_scores) >= 2:
        # 按评分排序
        sorted_funds = sorted(funds_with_scores, key=lambda x: x["score_100"]["total_score"], reverse=True)
        best = sorted_funds[0]
        worst = sorted_funds[-1]
        
        if best["score_100"]["total_score"] - worst["score_100"]["total_score"] >= 15:
            suggestions.append(
                f"🔄 建议将{worst.get('fund_name', worst.get('fund_code'))}({worst['score_100']['total_score']}分)"
                f"转换为{best.get('fund_name', best.get('fund_code'))}({best['score_100']['total_score']}分)"
            )

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
