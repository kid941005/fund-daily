"""
量化分析模块
包含：择时信号、组合优化、自动调仓建议
"""

from .signals import get_timing_signals, analyze_market_timing
from .optimizer import optimize_portfolio, calculate_efficient_frontier
from .rebalancing import calculate_rebalancing, generate_trade_orders

__all__ = [
    "get_timing_signals",
    "analyze_market_timing", 
    "optimize_portfolio",
    "calculate_efficient_frontier",
    "calculate_rebalancing",
    "generate_trade_orders",
]

# 动态权重
from .dynamic_weights import get_dynamic_weights, detect_market_cycle, adjust_score_by_cycle
