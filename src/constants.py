"""
Constants module for Fund Daily
统一管理项目中的常量定义
"""

import os

# 评分阈值
SCORE_THRESHOLDS = {
    "BUY": 60,
    "HOLD": 40,
    "SELL": 20,
    "HIGH": 70,
    "MEDIUM": 50,
    "LOW": 30,
    "ACTIVE": 55,
    "VERY_LOW": 40,
    "LOWER": 45
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
    "HIGH": 0.30,
    "MEDIUM": 0.20,
    "LOW": 0.10
}

# 缓存配置
CACHE_DURATION = int(os.environ.get('FUND_DAILY_CACHE_DURATION', 600))

# 缓存键前缀（统一版本控制）
CACHE_PREFIXES = {
    "fund": "fund_daily:v2:",
    "score": "score:v2:",
    "market": "market:v2:",
    "scoring": "fund_score:v2:"
}

# 缓存时间配置（秒）
CACHE_TTL = {
    "fund_data": 600,           # 10分钟
    "market_data": 300,         # 5分钟
    "score_data": 3600,         # 1小时
    "sentiment": 1800,          # 30分钟
    "hot_sectors": 900,         # 15分钟
    "news": 1200,               # 20分钟
}

# 别名（保持向后兼容）
ST = SCORE_THRESHOLDS
