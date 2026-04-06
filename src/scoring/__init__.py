"""
Fund Daily 评分系统
支持 8 大维度 100 分制综合评分
"""

from .calculator import (
    apply_ranking_bonus,
    calculate_score_v2,
    calculate_total_score,
    calculate_total_score_with_audit,
    format_score_report,
)
from .health import (
    DataHealthIndicator,
    calculate_data_health,
    generate_health_report,
    get_health_alert_level,
    is_market_day,
)
from .config import validate_weights_compat
from .liquidity import calculate_liquidity_score
from .manager import calculate_manager_score
from .models import SCORE_VERSION, ScoreAudit, ScoreInput, ScoreResult
from .momentum import calculate_momentum_score
from .performance import calculate_performance_score
from .risk_control import calculate_risk_control_score
from .sector import calculate_sector_score
from .sentiment import calculate_sentiment_score
from .valuation import calculate_valuation_score
from .weights import SCORE_WEIGHTS, get_all_weights, get_total_weight, get_weight, validate_weights

__all__ = [
    # weights
    "SCORE_WEIGHTS",
    "validate_weights",
    "get_weight",
    "get_all_weights",
    "get_total_weight",
    "validate_weights_compat",
    # models
    "SCORE_VERSION",
    "ScoreAudit",
    "ScoreInput",
    "ScoreResult",
    # indicators
    "calculate_valuation_score",
    "calculate_performance_score",
    "calculate_risk_control_score",
    "calculate_momentum_score",
    "calculate_sentiment_score",
    "calculate_sector_score",
    "calculate_manager_score",
    "calculate_liquidity_score",
    # calculator
    "calculate_total_score",
    "calculate_total_score_with_audit",
    "calculate_score_v2",
    "format_score_report",
    "apply_ranking_bonus",
    # health
    "DataHealthIndicator",
    "calculate_data_health",
    "generate_health_report",
    "get_health_alert_level",
    "is_market_day",
]
