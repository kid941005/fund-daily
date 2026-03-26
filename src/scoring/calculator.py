"""
评分计算器模块
包含综合评分、等级评定、报告格式化、排名加分
"""

import logging
from typing import Dict, List, Optional

from src.utils.error_handling import handle_errors

from .config import SCORE_WEIGHTS, _get_cached_score, _set_cached_score
from .models import ScoreInput
from .utils import get_grade  # 统一使用 utils.py 的等级函数
from .weights import validate_weights

logger = logging.getLogger(__name__)


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
    fund_code: str = "",
    use_cache: bool = True,
) -> Dict:
    """
    计算基金综合评分（100分制）
    """
    # 尝试从缓存获取（仅当 use_cache=True 时）
    if use_cache and fund_code:
        cached = _get_cached_score(fund_code)
        if cached:
            logger.info(f"Using cached score for {fund_code}")
            cached["from_cache"] = True
            return cached

    # 导入各维度评分函数
    from .liquidity import calculate_liquidity_score
    from .manager import calculate_manager_score
    from .momentum import calculate_momentum_score
    from .performance import calculate_performance_score
    from .risk_control import calculate_risk_control_score
    from .sector import calculate_sector_score
    from .sentiment import calculate_sentiment_score
    from .valuation import calculate_valuation_score

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
        valuation["score"]
        + performance["score"]
        + risk_control["score"]
        + momentum["score"]
        + sentiment["score"]
        + sector["score"]
        + manager["score"]
        + liquidity["score"]
    )

    # 权重校验
    validation_errors = []
    dimension_scores = {
        "valuation": valuation["score"],
        "performance": performance["score"],
        "risk_control": risk_control["score"],
        "momentum": momentum["score"],
        "sentiment": sentiment["score"],
        "sector": sector["score"],
        "manager": manager["score"],
        "liquidity": liquidity["score"],
    }

    for dim, score in dimension_scores.items():
        max_score = SCORE_WEIGHTS[dim]
        if score > max_score:
            validation_errors.append(f"维度'{dim}'分数{score}超过权重上限{max_score}")
        if score < 0:
            validation_errors.append(f"维度'{dim}'分数{score}为负数")

    if total_score < 0 or total_score > 100:
        validation_errors.append(f"总分{total_score}超出范围[0, 100]")

    calculated_total = sum(dimension_scores.values())
    if abs(calculated_total - total_score) > 0.001:
        validation_errors.append(f"维度分数之和{calculated_total}与总分{total_score}不一致")

    if validation_errors:
        logger.warning(f"评分校验警告 {fund_code}: {', '.join(validation_errors)}")
        for dim in dimension_scores:
            max_score = SCORE_WEIGHTS[dim]
            if dimension_scores[dim] > max_score:
                if dim == "valuation":
                    valuation["score"] = min(valuation["score"], max_score)
                elif dim == "performance":
                    performance["score"] = min(performance["score"], max_score)
                elif dim == "risk_control":
                    risk_control["score"] = min(risk_control["score"], max_score)
                elif dim == "momentum":
                    momentum["score"] = min(momentum["score"], max_score)
                elif dim == "sentiment":
                    sentiment["score"] = min(sentiment["score"], max_score)
                elif dim == "sector":
                    sector["score"] = min(sector["score"], max_score)
                elif dim == "manager":
                    manager["score"] = min(manager["score"], max_score)
                elif dim == "liquidity":
                    liquidity["score"] = min(liquidity["score"], max_score)

        total_score = (
            valuation["score"]
            + performance["score"]
            + risk_control["score"]
            + momentum["score"]
            + sentiment["score"]
            + sector["score"]
            + manager["score"]
            + liquidity["score"]
        )

    result = {
        "total_score": total_score,
        "base_score": total_score,
        "ranking_bonus": 0,
        "max_score": 100,
        "grade": get_grade(total_score),
        "details": {
            "valuation": valuation,
            "performance": performance,
            "risk_control": risk_control,
            "momentum": momentum,
            "sentiment": sentiment,
            "sector": sector,
            "manager": manager,
            "liquidity": liquidity,
        },
    }

    if fund_code:
        _set_cached_score(fund_code, result)

    return result


@handle_errors(default_return="[评分报告生成失败]", log_level="warning")
def format_score_report(scoring_result: Dict) -> str:
    """格式化评分报告"""
    details = scoring_result["details"]
    dimension_scores = sum(detail.get("score", 0) for detail in details.values())

    lines = [
        f"📊 基金综合评分报告",
        "=" * 40,
        f"总分: {scoring_result['total_score']}/100 ({scoring_result.get('grade', 'N/A')}级)",
    ]

    if scoring_result.get("ranking_bonus", 0) > 0:
        base_score = scoring_result.get("base_score", dimension_scores)
        ranking_bonus = scoring_result.get("ranking_bonus", 0)
        lines.append(f"  基础分: {base_score} + 排名加分: {ranking_bonus} = {base_score + ranking_bonus}")

    lines.append("")
    lines.append("【各维度评分】")
    lines.append(f"  1. 估值面: {details['valuation']['score']}/25")
    lines.append(f"  2. 业绩表现: {details['performance']['score']}/20")
    lines.append(f"  3. 风险控制: {details['risk_control']['score']}/15")
    lines.append(f"  4. 动量趋势: {details['momentum']['score']}/15")
    lines.append(f"  5. 市场情绪: {details['sentiment']['score']}/10")
    lines.append(f"  6. 板块景气: {details['sector']['score']}/8")
    lines.append(f"  7. 基金经理: {details['manager']['score']}/4")
    lines.append(f"  8. 流动性: {details['liquidity']['score']}/3")
    lines.append(f"  维度分数总和: {dimension_scores}")

    if abs(dimension_scores - scoring_result.get("total_score", 0)) > 0.001:
        lines.append(
            f"  ⚠️  注意: 维度分数之和({dimension_scores})与总分({scoring_result.get('total_score', 0)})不一致"
        )

    lines.append("")
    return "\n".join(lines)


@handle_errors(default_return=None, log_level="warning")
def apply_ranking_bonus(funds: List[Dict]) -> List[Dict]:
    """
    根据持仓内排名加分，拉开分数差距
    """
    if not funds or len(funds) < 2:
        return funds

    changes = [(i, float(f.get("daily_change", 0) or 0)) for i, f in enumerate(funds)]
    m1_returns = [(i, float(f.get("return_1m", 0) or 0)) for i, f in enumerate(funds)]

    changes.sort(key=lambda x: x[1], reverse=True)
    m1_returns.sort(key=lambda x: x[1], reverse=True)

    for i, fund in enumerate(funds):
        if "score_100" not in fund:
            continue

        score_100 = fund["score_100"]
        base_score = score_100.get("total_score", 0)
        if not base_score:
            continue

        ranking_bonus = 0

        if i < len(funds) * 0.25:
            ranking_bonus += 8
        elif i < len(funds) * 0.5:
            ranking_bonus += 4

        idx_m1 = next((j for j, x in enumerate(m1_returns) if x[0] == funds.index(fund)), -1)
        if idx_m1 >= 0 and idx_m1 < len(funds) * 0.25:
            ranking_bonus += 8
        elif idx_m1 >= 0 and idx_m1 < len(funds) * 0.5:
            ranking_bonus += 4

        total_score = min(base_score + ranking_bonus, 100)
        score_100["total_score"] = total_score
        score_100["ranking_bonus"] = ranking_bonus
        score_100["base_score"] = base_score
        score_100["grade"] = get_grade(total_score)

    return funds


def calculate_score_v2(input_data: ScoreInput) -> Dict:
    """
    新版评分函数，使用ScoreInput数据类封装参数
    """
    return calculate_total_score(
        fund_detail=input_data.fund_detail,
        risk_metrics=input_data.risk_metrics,
        market_sentiment=input_data.market_sentiment,
        market_score=input_data.market_score,
        news=input_data.news,
        hot_sectors=input_data.hot_sectors,
        commodity_sentiment=input_data.commodity_sentiment,
        fund_manager=input_data.fund_manager,
        fund_type=input_data.fund_type,
        fund_scale=input_data.fund_scale,
        daily_change=input_data.daily_change,
        fund_data=input_data.fund_data,
        fund_code=input_data.fund_code,
    )
