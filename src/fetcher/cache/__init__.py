"""
Cache Fetcher Module
"""

from .fetcher import (
    get_cache,
    set_cache,
    clear_cache,
    get_cache_stats,
)

__all__ = [
    "get_cache",
    "set_cache",
    "clear_cache",
    "get_cache_stats",
]
