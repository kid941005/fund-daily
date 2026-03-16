"""
from typing import List, Dict, Optional, Tuple
基金评分系统 - 100分制严谨评分
基于8大维度，30+细分指标
"""

import re
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# 导入缓存工具
try:
    from ..fetcher import get_cache, set_cache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    logger.warning("Fetcher not available, scoring cache disabled")

# ============== 评分缓存配置 ==============
SCORE_CACHE_TTL = 3600  # 缓存1小时
SCORE_CACHE_PREFIX = "fund_score:"

# ============== 评分权重配置 ==============
# 评分权重 - 增加区分度
SCORE_WEIGHTS = {
    "valuation": 25,      # 估值面 (25分) - 保持不变
    "performance": 25,   # 业绩表现 (20→25分) - 扩大
    "risk_control": 15,  # 风险控制 (15分) - 保持
    "momentum": 20,       # 动量趋势 (15→20分) - 扩大
    "sentiment": 10,     # 市场情绪 (10分) - 保持
    "sector": 10,        # 板块景气 (8→10分) - 扩大
    "manager": 3,        # 基金经理 (4→3分) - 减小
    "liquidity": 2,      # 流动性 (3→2分) - 减小
}


def _get_cache_key(fund_code: str) -> str:
    """生成缓存key"""
    return f"{SCORE_CACHE_PREFIX}{fund_code}"


def _get_cached_score(fund_code: str) -> Optional[Dict]:
    """获取缓存的评分"""
    if not HAS_CACHE:
        return None
    try:
        return get_cache(_get_cache_key(fund_code))
    except Exception:
        return None


def _set_cached_score(fund_code: str, score: Dict) -> None:
    """设置评分缓存"""
    if not HAS_CACHE:
        return
    try:
        set_cache(_get_cache_key(fund_code), score)
    except Exception:
        pass


# ============== 1. 估值面评分 (25分) ==============
def calculate_valuation_score(fund_detail: Dict, fund_data: Dict = None) -> Dict:
    """
    估值面评分 (满分25分)
    基于基金收益率、规模调整
    """
    details = {}
    scores = []
    
    # 1.1 近1年收益评分 (15分) - 基于实际收益率
    return_1y = 0
    if fund_data and fund_data.get("return_1y"):
        return_1y = float(fund_data.get("return_1y", 0) or 0)
    
    if return_1y > 50:
        s = 15
        r = f"近1年收益{return_1y:.1f}%，顶尖"
    elif return_1y > 30:
        s = 12
        r = f"近1年收益{return_1y:.1f}%，优秀"
    elif return_1y > 15:
        s = 10
        r = f"近1年收益{return_1y:.1f}%，良好"
    elif return_1y > 5:
        s = 7
        r = f"近1年收益{return_1y:.1f}%，一般"
    elif return_1y > 0:
        s = 4
        r = f"近1年收益{return_1y:.1f}%，较小"
    else:
        s = 1
        r = f"近1年收益{return_1y:.1f}%"
    scores.append(s)
    details["return_1y_score"] = s
    details["return_1y_reason"] = r
    
    # 1.2 近3月收益评分 (10分)
    return_3m = 0
    if fund_data and fund_data.get("return_3m"):
        return_3m = float(fund_data.get("return_3m", 0) or 0)
    
    if return_3m > 20:
        s = 10
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 10:
        s = 8
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 5:
        s = 5
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 0:
        s = 3
        r = f"近3月{return_3m:.1f}%"
    else:
        s = 1
        r = f"近3月{return_3m:.1f}%"
    scores.append(s)
    details["return_3m_score"] = s
    details["return_3m_reason"] = r
    
    total = min(25, sum(scores))
    return {
        "score": total,
        "reason": "基于收益率表现",
        "details": details
    }


# ============== 2. 业绩表现评分 (20分) ==============
def calculate_performance_score(fund_data: Dict = None) -> Dict:
    """
    业绩表现评分 (满分20分)
    基于各时间段收益表现
    """
    details = {}
    scores = []
    
    if not fund_data:
        return {"score": 6, "reason": "无数据", "details": {}}
    
    # 2.1 近3月表现 (8分)
    return_3m = float(fund_data.get("return_3m", 0) or 0)
    if return_3m > 30:
        s = 8
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 15:
        s = 6
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 5:
        s = 4
        r = f"近3月{return_3m:.1f}%"
    elif return_3m > 0:
        s = 2
        r = f"近3月{return_3m:.1f}%"
    else:
        s = 0
        r = f"近3月{return_3m:.1f}%"
    scores.append(s)
    details["return_3m"] = s
    
    # 2.2 近1月表现 (6分)
    return_1m = float(fund_data.get("return_1m", 0) or 0)
    if return_1m > 10:
        s = 6
    elif return_1m > 5:
        s = 5
    elif return_1m > 0:
        s = 3
    elif return_1m > -5:
        s = 1
    else:
        s = 0
    scores.append(s)
    details["return_1m"] = s
    
    # 2.3 收益稳定性 (6分)
    # 比较近1月和近3月趋势
    if return_1m > 0 and return_3m > 0:
        s = 6  # 趋势一致向上
        r = "收益稳定上升"
    elif return_1m > 0 and return_3m < 0:
        s = 4  # 短期反弹
        r = "短期反弹"
    elif return_1m < 0 and return_3m > 0:
        s = 3  # 短期回调
        r = "短期回调"
    elif return_1m < 0 and return_3m < 0:
        s = 0  # 持续下跌
        r = "持续下跌"
    else:
        s = 2
        r = "震荡"
    scores.append(s)
    details["stability"] = s
    
    total = min(20, sum(scores))
    return {
        "score": total,
        "reason": f"近3月{return_3m:+.1f}%，近1月{return_1m:+.1f}%",
        "details": details
    }


# ============== 3. 风险控制评分 (15分) ==============
def calculate_risk_control_score(risk_metrics: Dict, fund_data: Dict = None) -> Dict:
    """
    风险控制评分 (满分15分)
    基于夏普比率、最大回撤、波动率
    """
    details = {}
    scores = []
    
    # 3.1 夏普比率 (6分)
    sharpe = risk_metrics.get("sharpe_ratio", 0) or 0
    if sharpe >= 1.5:
        s = 6
        r = f"夏普比率{sharpe:.2f}，优秀"
    elif sharpe >= 1.0:
        s = 5
        r = f"夏普比率{sharpe:.2f}，良好"
    elif sharpe >= 0.5:
        s = 3
        r = f"夏普比率{sharpe:.2f}，一般"
    elif sharpe >= 0:
        s = 1
        r = f"夏普比率{sharpe:.2f}，较差"
    else:
        s = 0
        r = f"夏普比率{sharpe:.2f}，很差"
    scores.append(s)
    details["sharpe"] = s
    
    # 3.2 最大回撤 (5分)
    drawdown = risk_metrics.get("estimated_max_drawdown", 0) or 0
    if drawdown < 10:
        s = 5
        r = f"回撤{drawdown:.1f}%，控制良好"
    elif drawdown < 20:
        s = 3
        r = f"回撤{drawdown:.1f}%，控制一般"
    elif drawdown < 30:
        s = 1
        r = f"回撤{drawdown:.1f}%，波动较大"
    else:
        s = 0
        r = f"回撤{drawdown:.1f}%，风险较高"
    scores.append(s)
    details["drawdown"] = s
    
    # 3.3 波动率 (4分)
    volatility = risk_metrics.get("volatility", 0) or 0
    if volatility < 10:
        s = 4
        r = f"波动{volatility:.1f}%，较低"
    elif volatility < 20:
        s = 2
        r = f"波动{volatility:.1f}%，中等"
    else:
        s = 0
        r = f"波动{volatility:.1f}%，较高"
    scores.append(s)
    details["volatility"] = s
    
    total = min(15, sum(scores))
    return {
        "score": total,
        "reason": f"夏普{sharpe:.2f}，回撤{drawdown:.1f}%",
        "details": details
    }


# ============== 4. 动量趋势评分 (15分) ==============
def calculate_momentum_score(fund_data: Dict = None) -> Dict:
    """
    动量趋势评分 (满分15分)
    基于短期动量和趋势强度
    """
    details = {}
    scores = []
    
    if not fund_data:
        return {"score": 5, "reason": "无数据", "details": {}}
    
    # 4.1 短期动量 (8分)
    return_1m = float(fund_data.get("return_1m", 0) or 0)
    daily_change = float(fund_data.get("daily_change", 0) or 0)
    
    # 动量评分
    if return_1m > 10 and daily_change > 2:
        s = 8
        r = "强势上涨"
    elif return_1m > 5 and daily_change > 0:
        s = 6
        r = "温和上涨"
    elif return_1m > 0:
        s = 4
        r = "小幅上涨"
    elif return_1m > -5:
        s = 2
        r = "小幅下跌"
    elif return_1m > -10:
        s = 1
        r = "明显下跌"
    else:
        s = 0
        r = "大幅下跌"
    scores.append(s)
    details["momentum"] = s
    
    # 4.2 趋势强度 (7分)
    # 比较近1月和近3月
    return_3m = float(fund_data.get("return_3m", 0) or 0)
    if return_1m > 0 and return_3m > 0 and return_1m > return_3m / 3:
        s = 7
        r = "上升趋势强劲"
    elif return_1m > 0 and return_3m > 0:
        s = 5
        r = "上升趋势稳健"
    elif return_1m < 0 and return_3m < 0 and return_1m < return_3m / 3:
        s = 0
        r = "下降趋势加速"
    elif return_1m < 0 and return_3m < 0:
        s = 2
        r = "下降趋势"
    elif return_1m * return_3m < 0:
        s = 3
        r = "趋势震荡"
    else:
        s = 4
        r = "趋势不明"
    scores.append(s)
    details["trend"] = s
    
    total = min(15, sum(scores))
    return {
        "score": total,
        "reason": f"动量{r}，趋势{r}",
        "details": details
    }


# ============== 5. 市场情绪评分 (10分) ==============
def calculate_sentiment_score(market_sentiment: str, market_score: int) -> Dict:
    """
    市场情绪评分 (满分10分)
    """
    sentiment_map = {
        "乐观": 10,
        "偏多": 8,
        "平稳": 5,
        "偏空": 2,
        "恐慌": 0,
    }
    
    score = sentiment_map.get(market_sentiment, 5)
    
    return {
        "score": score,
        "reason": f"市场{market_sentiment}",
        "details": {"sentiment": market_sentiment, "score": market_score}
    }


# ============== 6. 板块景气评分 (8分) ==============
def calculate_sector_score(fund_type: str, hot_sectors: List[Dict], commodity_sentiment: str, fund_data: Dict = None) -> Dict:
    """
    板块景气评分 (满分8分)
    """
    details = {}
    scores = []
    
    # 6.1 大宗商品环境 (4分)
    if commodity_sentiment in ["乐观", "偏多"]:
        s = 4
        r = "商品景气高"
    elif commodity_sentiment == "平稳":
        s = 2
        r = "商品平稳"
    else:
        s = 1
        r = "商品低迷"
    scores.append(s)
    details["commodity"] = s
    
    # 6.2 行业匹配 (4分)
    hot_names = [s.get("name", "").lower() for s in hot_sectors[:5]]
    fund_type_lower = fund_type.lower() if fund_type else ""
    
    matched = False
    for name in hot_names:
        if name in fund_type_lower or fund_type_lower in name:
            s = 4
            r = f"属于热门板块{name}"
            matched = True
            break
    
    if not matched:
        s = 2
        r = "行业一般"
    scores.append(s)
    details["sector_match"] = s
    
    total = min(8, sum(scores))
    return {
        "score": total,
        "reason": r,
        "details": details
    }


# ============== 7. 基金经理评分 (4分) ==============
def calculate_manager_score(fund_manager: Optional[Dict]) -> Dict:
    """
    基金经理评分 (满分4分)
    """
    if not fund_manager:
        return {"score": 1, "reason": "无数据", "details": {}}
    
    star = fund_manager.get("star", 0) or 0
    work_time = fund_manager.get("workTime", "")
    
    # 解析任职年限
    years = 0
    match = re.search(r"(\d+)年", work_time)
    if match:
        years = int(match.group(1))
    
    if star >= 5 and years >= 5:
        score = 4
    elif star >= 4 and years >= 3:
        score = 3
    elif star >= 3 and years >= 1:
        score = 2
    else:
        score = 1
    
    return {
        "score": score,
        "reason": f"{star}星，{years}年",
        "details": {"star": star, "years": years}
    }


# ============== 8. 流动性评分 (3分) ==============
def calculate_liquidity_score(daily_change: float, fund_scale: float) -> Dict:
    """
    流动性评分 (满分3分)
    """
    # 涨幅太大或太小都影响流动性
    if abs(daily_change) < 3:
        s = 3
        r = f"涨跌{daily_change:+.2f}%，正常"
    elif abs(daily_change) < 5:
        s = 2
        r = f"涨跌{daily_change:+.2f}%，波动较大"
    else:
        s = 1
        r = f"涨跌{daily_change:+.2f}%，异常波动"
    
    return {
        "score": s,
        "reason": r,
        "details": {"daily_change": daily_change}
    }


# ============== 综合评分 ==============
def calculate_total_score(
    fund_detail: Dict,
    risk_metrics: Dict,
    market_sentiment: str,
    market_score: int,
    news: List[Dict],
    hot_sectors: List[Dict],
    commodity_sentiment: str,
    fund_manager: Optional[Dict],
    fund_type: str,
    fund_scale: float,
    daily_change: float,
    fund_data: Dict = None,
    fund_code: str = ""  # 新增：用于缓存
) -> Dict:
    """
    计算基金综合评分（100分制）
    """
    # 尝试从缓存获取
    if fund_code and HAS_CACHE:
        cached = _get_cached_score(fund_code)
        if cached:
            logger.info(f"Using cached score for {fund_code}")
            cached["from_cache"] = True
            return cached
    
    # 1. 估值面 (25分)
    valuation = calculate_valuation_score(fund_detail, fund_data)
    
    # 2. 业绩表现 (20分)
    performance = calculate_performance_score(fund_data)
    
    # 3. 风险控制 (15分)
    risk_control = calculate_risk_control_score(risk_metrics, fund_data)
    
    # 4. 动量趋势 (15分)
    momentum = calculate_momentum_score(fund_data)
    
    # 5. 市场情绪 (10分)
    sentiment = calculate_sentiment_score(market_sentiment, market_score)
    
    # 6. 板块景气 (8分)
    sector = calculate_sector_score(fund_type, hot_sectors, commodity_sentiment, fund_data)
    
    # 7. 基金经理 (4分)
    manager = calculate_manager_score(fund_manager)
    
    # 8. 流动性 (3分)
    liquidity = calculate_liquidity_score(daily_change, fund_scale)
    
    # 计算总分
    total_score = (
        valuation["score"] +
        performance["score"] +
        risk_control["score"] +
        momentum["score"] +
        sentiment["score"] +
        sector["score"] +
        manager["score"] +
        liquidity["score"]
    )
    
    # 汇总结果
    result = {
        "total_score": total_score,
        "max_score": 100,
        "grade": _get_grade(total_score),
        "details": {
            "valuation": valuation,
            "performance": performance,
            "risk_control": risk_control,
            "momentum": momentum,
            "sentiment": sentiment,
            "sector": sector,
            "manager": manager,
            "liquidity": liquidity,
        }
    }
    
    # 缓存结果
    if fund_code and HAS_CACHE:
        _set_cached_score(fund_code, result)
    
    return result


def _get_grade(score: int) -> str:
    """根据评分获取等级"""
    if score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C+"
    elif score >= 40:
        return "C"
    else:
        return "D"


def format_score_report(scoring_result: Dict) -> str:
    """格式化评分报告"""
    details = scoring_result["details"]
    
    lines = [
        f"📊 基金综合评分报告",
        "=" * 40,
        f"总分: {scoring_result['total_score']}/100 ({scoring_result['grade']}级)",
        "",
        "【各维度评分】",
        f"  1. 估值面: {details['valuation']['score']}/25",
        f"  2. 业绩表现: {details['performance']['score']}/20",
        f"  3. 风险控制: {details['risk_control']['score']}/15",
        f"  4. 动量趋势: {details['momentum']['score']}/15",
        f"  5. 市场情绪: {details['sentiment']['score']}/10",
        f"  6. 板块景气: {details['sector']['score']}/8",
        f"  7. 基金经理: {details['manager']['score']}/4",
        f"  8. 流动性: {details['liquidity']['score']}/3",
        "",
    ]
    
    return "\n".join(lines)


def apply_ranking_bonus(funds: List[Dict]) -> List[Dict]:
    """
    根据持仓内排名加分，拉开分数差距
    """
    if not funds or len(funds) < 2:
        return funds
    
    # 提取可比较的指标
    changes = [(i, float(f.get('daily_change', 0) or 0)) for i, f in enumerate(funds)]
    m1_returns = [(i, float(f.get('return_1m', 0) or 0)) for i, f in enumerate(funds)]
    
    # 按日涨幅排序
    changes.sort(key=lambda x: x[1], reverse=True)
    m1_returns.sort(key=lambda x: x[1], reverse=True)
    
    for i, fund in enumerate(funds):
        score = fund.get('score_100', {}).get('total_score', 0)
        if not score:
            continue
        
        # 涨幅排名前25%加8分
        if i < len(funds) * 0.25:
            score += 8
        elif i < len(funds) * 0.5:
            score += 4
        
        # 近1月排名前25%加8分
        idx_m1 = next((j for j, x in enumerate(m1_returns) if x[0] == funds.index(fund)), -1)
        if idx_m1 >= 0 and idx_m1 < len(funds) * 0.25:
            score += 8
        elif idx_m1 >= 0 and idx_m1 < len(funds) * 0.5:
            score += 4
        
        if 'score_100' not in fund:
            fund['score_100'] = {}
        fund['score_100']['total_score'] = min(score, 100)  # 不超过100分
    
    return funds
