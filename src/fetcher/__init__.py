"""
Data fetcher module for Fund Daily
Fetches fund data from East Money with caching support
"""

import re
import os
import json
import time
import ssl
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ============== Cache Configuration ==============
# 缓存时间：默认30分钟
CACHE_DURATION = int(os.environ.get("FUND_DAILY_CACHE_DURATION", 1800))
REQUEST_INTERVAL = float(os.environ.get("FUND_DAILY_REQUEST_INTERVAL", 0.5))

# 内存缓存（备用）
_cache = {}
_last_request_time = 0.0

# Redis 缓存优先，内存作为备用
try:
    from src.cache.redis_cache import redis_get, redis_set, redis_clear as redis_clear
    HAS_REDIS = True
    logger.info("✅ 使用 Redis 缓存")
except ImportError:
    HAS_REDIS = False
    logger.info("⚠️ 使用内存缓存")


def get_cache(key: str) -> Optional[Any]:
    """Get value from cache (Redis 优先，内存备用)"""
    # 先尝试 Redis
    if HAS_REDIS:
        value = redis_get(key)
        if value is not None:
            logger.debug(f"Redis cache hit: {key}")
            # 回填内存缓存
            _cache[key] = (value, time.time())
            return value
    
    # Redis 未命中，尝试内存缓存
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            logger.debug(f"Memory cache hit: {key}")
            return value
        else:
            del _cache[key]
            logger.debug(f"Cache expired: {key}")
    return None


def set_cache(key: str, value: Any) -> None:
    """Set value in cache (同时写入 Redis 和内存)"""
    # 写入内存
    _cache[key] = (value, time.time())
    
    # 尝试写入 Redis
    if HAS_REDIS:
        redis_set(key, value, CACHE_DURATION)
    
    logger.debug(f"Cache set: {key}")


def clear_cache() -> None:
    """Clear all cache"""
    global _cache
    _cache = {}
    
    if HAS_REDIS:
        redis_clear()
    
    logger.info("Cache cleared")


# ============== SSL ==============
def _get_ssl_context() -> ssl.SSLContext:
    """Get SSL context based on configuration"""
    if os.environ.get("FUND_DAILY_SSL_VERIFY", "1") == "0":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()
    return ctx


_ctx = _get_ssl_context()


# ============== HTTP Helpers ==============
def _make_request(url: str, timeout: int = 10) -> Optional[str]:
    """Make HTTP request with error handling and rate limiting"""
    global _last_request_time

    # Rate limiting: wait if needed
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        sleep_time = REQUEST_INTERVAL - elapsed
        logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://fund.eastmoney.com/",
            },
        )
        with urllib.request.urlopen(req, context=_ctx, timeout=timeout) as response:
            _last_request_time = time.time()  # 更新请求时间
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP error: {e.code} {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return None


# ============== Fund Data ==============
def fetch_fund_data(fund_code: str) -> Dict:
    """
    Fetch fund data from East Money

    Args:
        fund_code: 6-digit fund code

    Returns:
        dict: Fund data or error
    """
    cache_key = f"fund:{fund_code}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching fund data: {fund_code}")

    # East Money web API
    url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js?rt=1463558676006"
    content = _make_request(url)

    if not content:
        return {"error": "Failed to fetch data"}

    # Parse JSONP format: jsonpgz({...})
    if content.startswith("jsonpgz("):
        try:
            json_str = content[8:-2]
            result = json.loads(json_str)
            set_cache(cache_key, result)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {"error": "Invalid response format"}

    logger.warning(f"Invalid response format for fund {fund_code}")
    return {"error": "Invalid response format"}


def fetch_fund_detail(fund_code: str) -> Dict:
    """
    Fetch detailed fund information from East Money

    Args:
        fund_code: 6-digit fund code

    Returns:
        dict: Detailed fund data or error
    """
    # Check cache first
    cache_key = f"fund_detail:{fund_code}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    
    # First get basic data
    basic_data = fetch_fund_data(fund_code)
    if "error" in basic_data:
        return basic_data

    # Then get detailed data
    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    content = _make_request(url)

    if not content:
        return {**basic_data, "error": "Failed to fetch detail"}

    # Extract metrics using regex
    patterns = {
        "syl_1n": r'syl_1n="([^"]+)"',
        "syl_6y": r'syl_6y="([^"]+)"',
        "syl_3y": r'syl_3y="([^"]+)"',
        "syl_1y": r'syl_1y="([^"]+)"',
        "syl_1z": r'syl_1z="([^"]+)"',
        "syl_2z": r'syl_2z="([^"]+)"',
        "syl_5z": r'syl_5z="([^"]+)"',
        "syl_10z": r'syl_10z="([^"]+)"',
        "dwlz": r'dwjz="([^"]+)"',
        "ljjz": r'ljjz="([^"]+)"',
        "fund_sourceRate": r'fund_sourceRate="([^"]+)"',
        "fund_Rate": r'fund_Rate="([^"]+)"',
    }

    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            result[key] = match.group(1)

    final_result = {
        **basic_data,
        **result,
        "fund_code": fund_code,
    }
    
    # Cache the result
    set_cache(cache_key, final_result)
    
    return final_result


# ============== Market Data ==============
def fetch_market_news(limit: int = 8) -> List[Dict]:
    """
    Fetch market hot news

    Args:
        limit: Number of news to fetch

    Returns:
        list: News items
    """
    cache_key = f"news:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching market news, limit={limit}")

    url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
    content = _make_request(url)

    if not content:
        return []

    try:
        if "var ajaxResult=" in content:
            json_str = content.split("var ajaxResult=")[1].rstrip(";")
            data = json.loads(json_str)

            news_list = []
            for item in data.get("LivesList", [])[:limit]:
                url = item.get("url_w", "") or item.get("url_m", "") or item.get("url_unique", "")
                news_list.append(
                    {
                        "title": item.get("title", ""),
                        "time": item.get("showtime", ""),
                        "source": item.get("source", "东方财富"),
                        "summary": item.get("digest", "")[:100] if item.get("digest") else "",
                        "url": url,
                    }
                )
            set_cache(cache_key, news_list)
            return news_list
    except Exception as e:
        logger.error(f"News parse error: {str(e)}")

    return []


def fetch_hot_sectors(limit: int = 10) -> List[Dict]:
    """
    Fetch hot sectors from East Money

    Args:
        limit: Number of sectors to fetch

    Returns:
        list: Sector data
    """
    cache_key = f"sectors:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching hot sectors, limit={limit}")

    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": limit,
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        "fs": "m:90+t:2",
        "fields": "f1,f2,f3,f4,f12,f13,f14",
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{url}?{query_string}"

    content = _make_request(url)

    if not content:
        return []

    try:
        data = json.loads(content)
        diff = data.get("data", {}).get("diff", [])

        sectors = []
        for item in diff:
            sectors.append({"name": item.get("f14", ""), "change": item.get("f3", 0), "code": item.get("f12", "")})

        set_cache(cache_key, sectors)
        return sectors[:limit]

    except Exception as e:
        logger.error(f"Sector parse error: {str(e)}")
        return []


# ============== Commodity Data ==============
def fetch_commodity_prices() -> Dict:
    """
    Fetch commodity prices via ETFs

    Returns:
        dict: Commodity price data
    """
    cache_key = "commodity_prices"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    # 大宗商品ETF映射：代码 -> (名称, 权重)
    commodity_etfs = {
        "gold": ("518880", "华安黄金ETF", 0.4),
        "silver": ("161226", "白银基金", 0.15),
        "energy": ("159867", "能源化工ETF", 0.25),
        "copper": ("159997", "有色金属ETF", 0.2),
    }

    commodities = {}

    for key, (code, name, weight) in commodity_etfs.items():
        url = f"https://fundgz.1234567.com.cn/js/{code}.js"
        content = _make_request(url, timeout=8)

        if content and content.startswith("jsonpgz("):
            try:
                data = json.loads(content[8:-2])
                change = float(data.get("gszzl", 0) or 0)
                commodities[key] = {
                    "name": name,
                    "code": code,
                    "price": data.get("gsz"),
                    "change": change,
                    "weight": weight,
                }
            except Exception as e:
                logger.debug(f"Commodity ETF {code} parse error: {e}")

    set_cache(cache_key, commodities)
    return commodities


# ============== Historical NAV Data ==============


def fetch_fund_nav_history(fund_code: str, days: int = 90) -> List[Dict]:
    """
    Fetch historical NAV data for a fund

    Args:
        fund_code: 6-digit fund code
        days: Number of days to fetch (default 90)

    Returns:
        List of dict with 'date', 'nav', 'acc_nav' keys
    """
    from datetime import datetime

    # East Money historical NAV API
    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8")

        # Find Data_netWorthTrend - contains historical NAV with timestamps
        pattern = r"Data_netWorthTrend\s*=\s*\[([^\]]+)\]"
        match = re.search(pattern, content)

        if not match:
            logger.warning(f"No historical data found for {fund_code}")
            return []

        data_str = match.group(1)
        # Parse: {"x":timestamp,"y":nav_value}
        items = re.findall(r'\{"x":(\d+),"y":([\d.]+)', data_str)

        results = []
        for ts, nav in items[-days:]:
            try:
                dt = datetime.fromtimestamp(int(ts) / 1000)
                results.append(
                    {
                        "date": dt.strftime("%Y-%m-%d"),
                        "nav": float(nav),
                        "acc_nav": float(nav),  # Same as nav for this API
                    }
                )
            except (ValueError, OSError):
                continue

        logger.info(f"Fetched {len(results)} historical records for {fund_code}")
        return results

    except Exception as e:
        logger.error(f"Failed to fetch historical data for {fund_code}: {e}")
        return []


def calculate_technical_from_history(closes: List[float]) -> Dict:
    """
    Calculate technical indicators from historical NAV data

    Args:
        closes: List of NAV values (oldest to newest)

    Returns:
        Technical indicators dict
    """
    if len(closes) < 5:
        return {"ma5": None, "ma10": None, "ma20": None, "macd": {}, "rsi": None}

    from src.advice import calculate_ma, calculate_macd, calculate_rsi

    # Calculate moving averages
    ma5 = calculate_ma(closes, 5)
    ma10 = calculate_ma(closes, 10)
    ma20 = calculate_ma(closes, 20)

    # Calculate MACD
    macd = calculate_macd(closes)

    # Calculate RSI
    rsi = calculate_rsi(closes, 14)

    return {"ma5": ma5, "ma10": ma10, "ma20": ma20, "macd": macd, "rsi": rsi}


# ============== Fund Manager Data ==============
def fetch_fund_manager(fund_code: str) -> Optional[Dict]:
    """
    Fetch fund manager information

    Args:
        fund_code: 6-digit fund code

    Returns:
        dict: Fund manager data or None
    """
    cache_key = f"fund_manager:{fund_code}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    logger.info(f"Fetching fund manager: {fund_code}")

    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    content = _make_request(url)

    if not content:
        return None

    try:
        # 提取基金经理信息
        pattern = r"var Data_currentFundManager\s*=\s*\[([^\]]+)\]"
        match = re.search(pattern, content)

        if match:
            manager_str = match.group(1)
            # 解析第一个基金经理
            name_match = re.search(r'"name":"([^"]+)"', manager_str)
            star_match = re.search(r'"star":(\d+)', manager_str)
            time_match = re.search(r'"workTime":"([^"]+)"', manager_str)

            manager = {}
            if name_match:
                manager["name"] = name_match.group(1)
            if star_match:
                manager["star"] = int(star_match.group(1))
            if time_match:
                manager["workTime"] = time_match.group(1)

            if manager.get("name"):
                set_cache(cache_key, manager)
                return manager
    except Exception as e:
        logger.warning(f"Parse manager error: {e}")

    return None


def fetch_fund_scale(fund_code: str) -> float:
    """
    Fetch fund scale (in 100 million yuan)

    Args:
        fund_code: 6-digit fund code

    Returns:
        float: Fund scale in 100 million yuan
    """
    cache_key = f"fund_scale:{fund_code}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    content = _make_request(url)

    if not content:
        return 0.0

    try:
        # 提取规模数据 (单位：亿元)
        pattern = r"var Data_fluctuationScale\s*=\s*\{[^}]*\"series\":\s*\[\{[^}]*\"y\":\s*([\d.]+)"
        match = re.search(pattern, content)

        if match:
            scale = float(match.group(1))
            set_cache(cache_key, scale)
            return scale
    except Exception as e:
        logger.warning(f"Parse scale error: {e}")

    return 0.0
