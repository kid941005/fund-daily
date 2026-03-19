"""
Fund Advanced Fetcher Module
"""


from .fetcher import (
    calculate_technical_from_history,
    fetch_fund_manager,
    fetch_fund_scale,
)

__all__ = [
    "calculate_technical_from_history",
    "fetch_fund_manager",
    "fetch_fund_scale",
]
