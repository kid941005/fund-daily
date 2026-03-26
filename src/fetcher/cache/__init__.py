"""
Cache Fetcher Module
"""

from .fetcher import (
    clear_cache,
    get_cache,
    get_cache_stats,
    set_cache,
)

__all__ = [
    "get_cache",
    "set_cache",
    "clear_cache",
    "get_cache_stats",
]
