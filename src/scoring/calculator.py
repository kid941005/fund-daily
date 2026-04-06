"""
评分计算器模块
包含综合评分、等级评定、报告格式化、排名加分
"""

import logging
from datetime import datetime

from src.utils.error_handling import handle_errors

from .config import _get_cached_score, _set_cached_score
from .models import SCORE_VERSION, ScoreAudit, ScoreInput
from .utils import get_grade  # 统一使用 utils.py 的等级函数
from .weights import SCORE_WEIGHTS

logger = logging.getLogger(__name__)


def _build_dimension_input(fund_data: dict | None, field: str, default=None):
    """从 fund_data 中提取维度评分所需的原始输入"""
    if fund_data is None:
        return default
    return fund_data.get(field, default)


def calculate_total_score(
    fund_detail: dict,
    risk_metrics: dict,
    market_sentiment: str,
    market_score: int,
    news: list[dict],
    hot_sectors: list[dict],
    commodity_sentiment: str,
    fund_manager: dict | None,
    fund_type: str,
    fund_scale: float,
    daily_change: float,
    fund_data: dict = None,
    fund_code: str = "",
    use_cache: bool = False,
    audit: ScoreAudit | None = None,
) -> dict:
    """
    计算基金综合评分（100分制，含完整审计追踪）

    新增审计追踪功能:
    - 每个维度返回原始输入值（input 字段）
    - 支持 data_source / data_fetched_at / calculation_version
    - 支持传入 audit 对象或自动构建
    """
    # 构建审计对象
    if audit is None:
        audit = ScoreAudit(
            data_source="unknown",
            calculation_version=SCORE_VERSION,
            calculation_time=datetime.now(),
        )

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

    # 1. 估值面 (25分) - 记录原始输入
    valuation_input = {
        "return_1y": _build_dimension_input(fund_data, "return_1y"),
        "return_3m": _build_dimension_input(fund_data, "return_3m"),
        "return_6m": _build_dimension_input(fund_data, "return_6m"),
    }
    valuation = calculate_valuation_score(fund_detail, fund_data)
    valuation["input"] = valuation_input

    # 2. 业绩表现 (20分) - 记录原始输入
    performance_input = {
        "return_1y": _build_dimension_input(fund_data, "return_1y"),
        "return_3m": _build_dimension_input(fund_data, "return_3m"),
        "volatility": risk_metrics.get("volatility") if risk_metrics else None,
    }
    performance = calculate_performance_score(fund_data)
    performance["input"] = performance_input

    # 3. 风险控制 (15分) - 记录原始输入
    risk_control_input = {
        "max_drawdown": risk_metrics.get("max_drawdown") if risk_metrics else None,
        "sharpe_ratio": risk_metrics.get("sharpe_ratio") if risk_metrics else None,
        "volatility": risk_metrics.get("volatility") if risk_metrics else None,
    }
    risk_control = calculate_risk_control_score(risk_metrics, fund_data)
    risk_control["input"] = risk_control_input

    # 4. 动量趋势 (15分) - 记录原始输入
    momentum_input = {
        "return_1m": _build_dimension_input(fund_data, "return_1m"),
        "return_3m": _build_dimension_input(fund_data, "return_3m"),
    }
    momentum = calculate_momentum_score(fund_data)
    momentum["input"] = momentum_input

    # 5. 市场情绪 (10分) - 记录原始输入
    sentiment_input = {
        "market_sentiment": market_sentiment,
        "market_score": market_score,
    }
    sentiment = calculate_sentiment_score(market_sentiment, market_score)
    sentiment["input"] = sentiment_input

    # 6. 板块景气 (8分) - 记录原始输入
    sector_input = {
        "fund_type": fund_type,
        "hot_sectors_count": len(hot_sectors) if hot_sectors else 0,
        "commodity_sentiment": commodity_sentiment,
    }
    sector = calculate_sector_score(fund_type, hot_sectors, commodity_sentiment, fund_data)
    sector["input"] = sector_input

    # 7. 基金经理 (4分) - 记录原始输入
    manager_input = {
        "manager_name": fund_manager.get("name") if fund_manager else None,
        "manager_tenure": fund_manager.get("tenure") if fund_manager else None,
    }
    manager = calculate_manager_score(fund_manager)
    manager["input"] = manager_input

    # 8. 流动性 (3分) - 记录原始输入
    liquidity_input = {
        "daily_change": daily_change,
        "fund_scale": fund_scale,
    }
    liquidity = calculate_liquidity_score(daily_change, fund_scale)
    liquidity["input"] = liquidity_input

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

    # 先对维度分数进行截断（确保不超过权重上限，不低于0）
    dimension_scores = {
        "valuation": max(0, min(valuation["score"], SCORE_WEIGHTS["valuation"])),
        "performance": max(0, min(performance["score"], SCORE_WEIGHTS["performance"])),
        "risk_control": max(0, min(risk_control["score"], SCORE_WEIGHTS["risk_control"])),
        "momentum": max(0, min(momentum["score"], SCORE_WEIGHTS["momentum"])),
        "sentiment": max(0, min(sentiment["score"], SCORE_WEIGHTS["sentiment"])),
        "sector": max(0, min(sector["score"], SCORE_WEIGHTS["sector"])),
        "manager": max(0, min(manager["score"], SCORE_WEIGHTS["manager"])),
        "liquidity": max(0, min(liquidity["score"], SCORE_WEIGHTS["liquidity"])),
    }

    # 用截断后的值更新原始字典
    valuation["score"] = dimension_scores["valuation"]
    performance["score"] = dimension_scores["performance"]
    risk_control["score"] = dimension_scores["risk_control"]
    momentum["score"] = dimension_scores["momentum"]
    sentiment["score"] = dimension_scores["sentiment"]
    sector["score"] = dimension_scores["sector"]
    manager["score"] = dimension_scores["manager"]
    liquidity["score"] = dimension_scores["liquidity"]

    # 重新计算总分
    total_score = sum(dimension_scores.values())

    # 验证截断后的分数
    validation_errors = []
    for dim, score in dimension_scores.items():
        if score < 0:
            validation_errors.append(f"维度'{dim}'分数{score}为负数")

    if total_score < 0 or total_score > 100:
        validation_errors.append(f"总分{total_score}超出范围[0, 100]")

    if validation_errors:
        logger.warning(f"评分校验警告 {fund_code}: {', '.join(validation_errors)}")

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
        # 审计字段
        "audit": audit.to_dict(),
    }

    if fund_code:
        _set_cached_score(fund_code, result)

    return result


@handle_errors(default_return="[评分报告生成失败]", log_level="warning")
def format_score_report(scoring_result: dict) -> str:
    """格式化评分报告"""
    details = scoring_result["details"]
    dimension_scores = sum(detail.get("score", 0) for detail in details.values())

    lines = [
        "📊 基金综合评分报告",
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
def apply_ranking_bonus(funds: list[dict]) -> list[dict]:
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


def calculate_score_v2(input_data: ScoreInput) -> dict:
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


def calculate_total_score_with_audit(
    fund_detail: dict,
    risk_metrics: dict,
    market_sentiment: str,
    market_score: int,
    news: list[dict],
    hot_sectors: list[dict],
    commodity_sentiment: str,
    fund_manager: dict | None,
    fund_type: str,
    fund_scale: float,
    daily_change: float,
    fund_data: dict = None,
    fund_code: str = "",
    use_cache: bool = False,
    data_source: str = "api",
    data_fetched_at: datetime | None = None,
    nav_date: str | None = None,
) -> dict:
    """
    计算基金综合评分（带完整审计追踪的便捷封装）

    Args:
        data_source: 数据来源 (api/cache/db)
        data_fetched_at: 数据抓取时间
        nav_date: 净值数据日期
    """
    audit = ScoreAudit(
        data_source=data_source,
        data_fetched_at=data_fetched_at or datetime.now(),
        nav_date=nav_date,
        calculation_version=SCORE_VERSION,
        calculation_time=datetime.now(),
    )
    return calculate_total_score(
        fund_detail=fund_detail,
        risk_metrics=risk_metrics,
        market_sentiment=market_sentiment,
        market_score=market_score,
        news=news,
        hot_sectors=hot_sectors,
        commodity_sentiment=commodity_sentiment,
        fund_manager=fund_manager,
        fund_type=fund_type,
        fund_scale=fund_scale,
        daily_change=daily_change,
        fund_data=fund_data,
        fund_code=fund_code,
        use_cache=use_cache,
        audit=audit,
    )
