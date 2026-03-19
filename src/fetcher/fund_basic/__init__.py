"""
Fund Basic Fetcher Module
"""


from .fetcher import (
    fetch_fund_data,
    fetch_fund_detail,
    fetch_fund_nav_history,
)

__all__ = [
    "fetch_fund_data",
    "fetch_fund_detail",
    "fetch_fund_nav_history",
]
