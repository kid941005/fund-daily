"""
Constants module for Fund Daily
统一管理项目中的常量定义
"""

# 评分阈值
SCORE_THRESHOLDS = {
    "BUY": 60,
    "HOLD": 40,
    "SELL": 20,
    "HIGH": 70,
    "MEDIUM": 50,
    "LOW": 30,
    "ACTIVE": 55
}

# 评分权重配置
WEIGHT_CONFIG = {
    "valuation": 25,      # 估值面
    "performance": 20,    # 业绩
    "risk_control": 15,  # 风控
    "momentum": 15,      # 动量
    "sentiment": 10,    # 情绪
    "sector": 8,        # 板块
    "manager": 4,        # 经理
    "liquidity": 3       # 流动性
}

# 持仓分配比例
ALLOCATION_RATIOS = {
    "HIGH": 0.30,    # 高评分上限30%
    "MEDIUM": 0.20,  # 中评分上限20%
    "LOW": 0.10      # 低评分上限10%
}

# 别名（保持向后兼容）
ST = SCORE_THRESHOLDS

