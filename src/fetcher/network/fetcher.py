"""
Network Fetcher Functions
"""

import logging
import ssl
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
import requests
import json

from src.config import get_config

logger = logging.getLogger(__name__)


def _get_ssl_context() -> ssl.SSLContext:
    """Get SSL context based on configuration"""
    config = get_config()
    if not config.security.ssl_verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()
    return ctx


def _make_request(url: str, timeout: int = 10) -> Optional[str]:
    """Make HTTP request with error handling and rate limiting"""
    # 使用线程安全的速率限制器
    from src.utils.rate_limiter import wait_if_needed

    wait_if_needed()

    try:
        # 获取SSL上下文
        ctx = _get_ssl_context()

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://fund.eastmoney.com/",
            },
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP error: {e.code} {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return None
