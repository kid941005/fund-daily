"""
from typing import List, Dict, Optional, Tuple
基金评分系统 - 100分制严谨评分
基于8大维度，30+细分指标
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime

# 导入数据模型
from .models import ScoreInput, ScoreResult

logger = logging.getLogger(__name__)

# 导入缓存工具
try:
    from ..fetcher import get_cache, set_cache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    logger.warning("Fetcher not available, scoring cache disabled")

# ============== 评分缓存配置 ==============
from src.constants import CACHE_PREFIXES, CACHE_TTL
SCORE_CACHE_TTL = CACHE_TTL.get("score_data", 600)  # 使用统一配置
SCORE_CACHE_PREFIX = CACHE_PREFIXES.get("scoring", "fund_score:v2:")

# ============== 评分权重配置（从weights模块导入） ==============
from .weights import SCORE_WEIGHTS, validate_weights, get_weight, get_all_weights, get_total_weight

# 权重校验函数（保留向后兼容）
def validate_weights_compat() -> Tuple[bool, str]:
    """
    校验权重配置是否合法
    
    Returns:
        (是否有效, 错误信息)
    """
    # 1. 检查权重字典是否为空
    if not SCORE_WEIGHTS:
        return False, "权重配置为空"
    
    # 2. 检查权重总和是否为100
    total = sum(SCORE_WEIGHTS.values())
    if total != 100:
        return False, f"权重总和应为100，实际为{total}"
    
    # 3. 检查权重类型和范围
    for dimension, weight in SCORE_WEIGHTS.items():
        # 类型检查
        if not isinstance(weight, (int, float)):
            return False, f"维度'{dimension}'的权重必须是数字，实际类型为{type(weight).__name__}"
        
        # 正数检查
        if weight <= 0:
            return False, f"维度'{dimension}'的权重必须为正数，实际为{weight}"
        
        # 范围检查：单个权重不应超过总分的一半（50分）
        if weight > 50:
            return False, f"维度'{dimension}'的权重过大（{weight}分），不应超过50分"
        
        # 整数检查（建议为整数，但允许小数）
        if not isinstance(weight, int):
            logger.warning(f"维度'{dimension}'的权重为小数{weight}，建议使用整数")
    
    # 4. 检查维度是否完整
    required_dimensions = ["valuation", "performance", "risk_control", "momentum", 
                          "sentiment", "sector", "manager", "liquidity"]
    for dim in required_dimensions:
        if dim not in SCORE_WEIGHTS:
            return False, f"缺失必要维度: {dim}"
    
    # 5. 检查是否有多余的维度
    extra_dims = set(SCORE_WEIGHTS.keys()) - set(required_dimensions)
    if extra_dims:
        logger.warning(f"评分系统包含额外的维度: {', '.join(extra_dims)}")
    
    # 6. 检查权重分布是否合理
    # 主要维度（估值、业绩、风控、动量）应占总分的较大比例
    major_dims = ["valuation", "performance", "risk_control", "momentum"]
    major_total = sum(SCORE_WEIGHTS.get(dim, 0) for dim in major_dims)
    if major_total < 60:  # 主要维度应至少占60分
        logger.warning(f"主要维度（估值、业绩、风控、动量）总分仅{major_total}分，建议至少60分")
    
    # 7. 检查流动性权重是否合理（通常不应过高）
    liquidity_weight = SCORE_WEIGHTS.get("liquidity", 0)
    if liquidity_weight > 10:
        logger.warning(f"流动性权重({liquidity_weight}分)过高，通常不应超过10分")
    
    return True, "权重配置有效"


# 启动时自动校验权重
_is_valid, _error_msg = validate_weights()
if not _is_valid:
    logger.error(f"评分权重配置错误: {_error_msg}")
    raise ValueError(f"评分权重配置错误: {_error_msg}")


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
from .valuation import calculate_valuation_score


# ============== 2. 业绩表现评分 (20分) ==============
from .performance import calculate_performance_score


# ============== 3. 风险控制评分 (15分) ==============
from .risk_control import calculate_risk_control_score


# ============== 4. 动量趋势评分 (15分) ==============
from .momentum import calculate_momentum_score


# ============== 5. 市场情绪评分 (10分) ==============
from .sentiment import calculate_sentiment_score

# ============== 6. 板块景气评分 (8分) ==============
from .sector import calculate_sector_score

# ============== 7. 基金经理评分 (4分) ==============
from .manager import calculate_manager_score

# ============== 8. 流动性评分 (3分) ==============
from .liquidity import calculate_liquidity_score


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
    
    # 权重校验
    validation_errors = []
    
    # 1. 检查各维度分数是否超过权重上限
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
    
    # 2. 检查总分范围
    if total_score < 0 or total_score > 100:
        validation_errors.append(f"总分{total_score}超出范围[0, 100]")
    
    # 3. 检查各维度分数之和是否等于总分
    calculated_total = sum(dimension_scores.values())
    if abs(calculated_total - total_score) > 0.001:
        validation_errors.append(f"维度分数之和{calculated_total}与总分{total_score}不一致")
    
    # 如果有校验错误，记录日志
    if validation_errors:
        logger.warning(f"评分校验警告 {fund_code}: {', '.join(validation_errors)}")
        # 修复明显错误：如果分数超过上限，则限制到上限
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
        
        # 重新计算总分
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
        "base_score": total_score,  # 初始时基础分等于总分
        "ranking_bonus": 0,         # 排名加分，初始为0
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
    
    # 计算维度分数之和
    dimension_scores = sum(detail.get('score', 0) for detail in details.values())
    
    lines = [
        f"📊 基金综合评分报告",
        "=" * 40,
        f"总分: {scoring_result['total_score']}/100 ({scoring_result.get('grade', 'N/A')}级)",
    ]
    
    # 如果有排名加分，显示详细信息
    if scoring_result.get('ranking_bonus', 0) > 0:
        base_score = scoring_result.get('base_score', dimension_scores)
        ranking_bonus = scoring_result.get('ranking_bonus', 0)
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
    
    # 验证一致性
    if abs(dimension_scores - scoring_result.get('total_score', 0)) > 0.001:
        lines.append(f"  ⚠️  注意: 维度分数之和({dimension_scores})与总分({scoring_result.get('total_score', 0)})不一致")
    
    lines.append("")
    
    return "\n".join(lines)


def apply_ranking_bonus(funds: List[Dict]) -> List[Dict]:
    """
    根据持仓内排名加分，拉开分数差距
    
    修改：添加 ranking_bonus 字段，保持总分 = 维度分数之和 + ranking_bonus
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
        if 'score_100' not in fund:
            continue
            
        score_100 = fund['score_100']
        base_score = score_100.get('total_score', 0)
        if not base_score:
            continue
        
        # 计算排名加分
        ranking_bonus = 0
        
        # 涨幅排名前25%加8分
        if i < len(funds) * 0.25:
            ranking_bonus += 8
        elif i < len(funds) * 0.5:
            ranking_bonus += 4
        
        # 近1月排名前25%加8分
        idx_m1 = next((j for j, x in enumerate(m1_returns) if x[0] == funds.index(fund)), -1)
        if idx_m1 >= 0 and idx_m1 < len(funds) * 0.25:
            ranking_bonus += 8
        elif idx_m1 >= 0 and idx_m1 < len(funds) * 0.5:
            ranking_bonus += 4
        
        # 应用加分（不超过100分）
        total_score = min(base_score + ranking_bonus, 100)
        
        # 更新评分结果
        score_100['total_score'] = total_score
        score_100['ranking_bonus'] = ranking_bonus
        score_100['base_score'] = base_score
        
        # 更新等级
        score_100['grade'] = _get_grade(total_score)
    
    return funds


# ============== 新版评分函数（使用数据类） ==============
def calculate_score_v2(input_data: ScoreInput) -> Dict:
    """
    新版评分函数，使用ScoreInput数据类封装参数
    
    Args:
        input_data: ScoreInput对象，包含所有评分参数
        
    Returns:
        评分结果字典
    """
    # 调用原有的calculate_total_score函数，保持逻辑一致
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
        fund_code=input_data.fund_code
    )


# 导出列表
__all__ = [
    'validate_weights',
    'calculate_valuation_score',
    'calculate_performance_score',
    'calculate_risk_control_score',
    'calculate_momentum_score',
    'calculate_sentiment_score',
    'calculate_sector_score',
    'calculate_manager_score',
    'calculate_liquidity_score',
    'calculate_total_score',
    'format_score_report',
    'apply_ranking_bonus',
    'calculate_score_v2',
    'ScoreInput',
    'ScoreResult'
]
