"""
Task Handlers Module

Provides task handlers for:
- data_fetch: Fund data fetching tasks
- cache_update: Cache update tasks
- calculation: Batch calculation tasks

Handlers are auto-registered via the @register_task decorator.
Import this module to ensure handlers are registered.
"""

from .data_fetch import fund_fetch_handler, nav_update_handler
from .cache_update import cache_warmup_handler
from .calculation import score_calculation_handler, batch_import_handler

__all__ = [
    "fund_fetch_handler",
    "nav_update_handler",
    "cache_warmup_handler",
    "score_calculation_handler",
    "batch_import_handler",
]
