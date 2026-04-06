"""
评分权重管理模块
"""

# 评分权重配置 - 100分制
SCORE_WEIGHTS = {
    "valuation": 25,  # 估值面 (25分)
    "performance": 20,  # 业绩表现 (20分)
    "risk_control": 15,  # 风险控制 (15分)
    "momentum": 15,  # 动量趋势 (15分)
    "sentiment": 10,  # 市场情绪 (10分)
    "sector": 8,  # 板块景气 (8分)
    "manager": 4,  # 基金经理 (4分)
    "liquidity": 3,  # 流动性 (3分)
}
# 总计: 25+20+15+15+10+8+4+3 = 100分


def validate_weights() -> tuple[bool, str]:
    """
    校验权重配置是否合法

    Returns:
        (是否有效, 错误信息)
    """
    import logging

    logger = logging.getLogger(__name__)

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

    # 4. 检查维度是否完整
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

    # 5. 检查是否有多余的维度
    extra_dims = set(SCORE_WEIGHTS.keys()) - set(required_dimensions)
    if extra_dims:
        logger.warning(f"评分系统包含额外的维度: {', '.join(extra_dims)}")

    # 6. 检查权重分布是否合理
    major_dims = ["valuation", "performance", "risk_control", "momentum"]
    major_total = sum(SCORE_WEIGHTS.get(dim, 0) for dim in major_dims)
    if major_total < 60:
        logger.warning(f"主要维度（估值、业绩、风控、动量）总分仅{major_total}分，建议至少60分")

    return True, "权重配置有效"


def get_weight(dim: str) -> float:
    """
    获取指定维度的权重

    Args:
        dim: 维度名称

    Returns:
        权重值，如果维度不存在返回0
    """
    return SCORE_WEIGHTS.get(dim, 0)


def get_all_weights() -> dict[str, float]:
    """获取所有权重配置"""
    return SCORE_WEIGHTS.copy()


def get_total_weight() -> int:
    """获取权重总和"""
    return sum(SCORE_WEIGHTS.values())
