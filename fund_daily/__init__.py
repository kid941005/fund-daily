"""
Fund Daily - 每日基金分析工具
"""

from .storage import FundStorage, get_storage
from .holdings import HoldingsManager, get_holdings_manager
from .profit import calculate_total_profit, generate_profit_report
from .chart import generate_trend_chart, generate_comparison_chart

__version__ = "1.1.0"
__all__ = [
    "FundStorage", 
    "get_storage",
    "HoldingsManager",
    "get_holdings_manager",
    "calculate_total_profit",
    "generate_profit_report",
    "generate_trend_chart",
    "generate_comparison_chart"
]
