"""
评分系统配置模块
包含权重配置、验证规则、缓存配置
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ============== 评分缓存配置 ==============
from src.constants import CACHE_PREFIXES, CACHE_TTL

SCORE_CACHE_TTL = CACHE_TTL.get("score_data", 600)
SCORE_CACHE_PREFIX = CACHE_PREFIXES.get("scoring", "fund_score:v2:")

# ============== 评分权重配置 ==============
from .weights import SCORE_WEIGHTS, get_all_weights, get_total_weight, get_weight, validate_weights


def validate_weights_compat() -> Tuple[bool, str]:
    """校验权重配置是否合法"""
    if not SCORE_WEIGHTS:
        return False, "权重配置为空"

    total = sum(SCORE_WEIGHTS.values())
    if total != 100:
        return False, f"权重总和应为100，实际为{total}"

    for dimension, weight in SCORE_WEIGHTS.items():
        if not isinstance(weight, (int, float)):
            return False, f"维度'{dimension}'的权重必须是数字"
        if weight <= 0:
            return False, f"维度'{dimension}'的权重必须为正数"
        if weight > 50:
            return False, f"维度'{dimension}'的权重过大（{weight}分），不应超过50分"

    required_dimensions = [
        "valuation",
        "performance",
        "risk_control",
        "momentum",
        "sentiment",
        "sector",
        "manager",
        "liquidity",
    ]
    for dim in required_dimensions:
        if dim not in SCORE_WEIGHTS:
            return False, f"缺失必要维度: {dim}"

    return True, "权重配置有效"


# 启动时自动校验
_is_valid, _error_msg = validate_weights()
if not _is_valid:
    logger.error(f"评分权重配置错误: {_error_msg}")
    raise ValueError(f"评分权重配置错误: {_error_msg}")


# ============== 缓存工具 ==============
def _get_cache_key(fund_code: str) -> str:
    """生成缓存key"""
    return f"{SCORE_CACHE_PREFIX}{fund_code}"


def _get_cached_score(fund_code: str) -> Optional[Dict]:
    """获取缓存的评分"""
    try:
        from ..fetcher import get_cache

        return get_cache(_get_cache_key(fund_code))
    except Exception:
        return None


def _set_cached_score(fund_code: str, score: Dict) -> None:
    """设置评分缓存"""
    try:
        from ..fetcher import set_cache

        set_cache(_get_cache_key(fund_code), score)
    except Exception:
        pass
