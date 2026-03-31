"""
市场服务类

提供市场相关的业务逻辑，包括：
1. 市场情绪分析
2. 大宗商品情绪
3. 热点板块
4. 市场新闻
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from src.analyzer import get_commodity_sentiment, get_market_sentiment
from src.cache.manager import get_cache_manager
from src.cache.redis_cache import get_redis_client
from src.fetcher import fetch_hot_sectors, fetch_market_news
from src.services.metrics_service import get_metrics_service, timed_metric

logger = logging.getLogger(__name__)


class MarketService:
    """市场服务"""

    def __init__(self, cache_enabled: bool = True):
        """
        初始化市场服务

        Args:
            cache_enabled: 是否启用缓存
        """
        self.cache_enabled = cache_enabled
        self.metrics_service = get_metrics_service()
        self.cache_manager = get_cache_manager()

        # 缓存配置 - 使用统一的常量配置
        from src.constants import CACHE_PREFIXES, CACHE_TTL

        self.cache_prefix = CACHE_PREFIXES.get("market", "market:v2:")
        self.market_data_key = f"{self.cache_prefix}full_data"
        self.sectors_key = f"{self.cache_prefix}hot_sectors"
        self.news_key = f"{self.cache_prefix}market_news"

        # 缓存时间 - 使用统一配置
        self.market_data_ttl = CACHE_TTL.get("market_data", 300)  # 5分钟
        self.sectors_ttl = CACHE_TTL.get("hot_sectors", 600)  # 10分钟
        self.news_ttl = CACHE_TTL.get("news", 900)  # 15分钟

        # 并行工作线程数
        self.max_workers = 4

    @timed_metric(metric_type="external_api", name="get_market_sentiment")
    def get_market_sentiment(self, use_cache: bool = True) -> dict:
        """
        获取市场情绪

        Args:
            use_cache: 是否使用缓存

        Returns:
            市场情绪数据
        """
        try:
            cache_key = f"{self.cache_prefix}sentiment"

            if use_cache and self.cache_enabled:
                cached = self.cache_manager.get(cache_key)
                if cached:
                    # 记录缓存命中
                    self.metrics_service.record_cache_hit("market_sentiment", hit=True)
                    return cached
                else:
                    # 记录缓存未命中
                    self.metrics_service.record_cache_hit("market_sentiment", hit=False)

            sentiment_data = get_market_sentiment()
            if not sentiment_data:
                sentiment_data = {"sentiment": "平稳", "score": 0}

            if use_cache and self.cache_enabled:
                try:
                    self.cache_manager.set(cache_key, sentiment_data, ttl=self.market_data_ttl)
                except Exception as e:
                    logger.warning(f"Failed to cache market sentiment: {e}")

            return sentiment_data

        except Exception as e:
            logger.error(f"Failed to get market sentiment: {e}")
            # 返回降级数据
            return {"sentiment": "平稳", "score": 0, "error": str(e)}

    @timed_metric(metric_type="external_api", name="get_commodity_sentiment")
    def get_commodity_sentiment(self, use_cache: bool = True) -> dict:
        """
        获取大宗商品情绪

        Args:
            use_cache: 是否使用缓存

        Returns:
            商品情绪数据
        """
        try:
            cache_key = f"{self.cache_prefix}commodity"

            if use_cache and self.cache_enabled:
                cached = self.cache_manager.get(cache_key)
                if cached:
                    return cached

            commodity_data = get_commodity_sentiment()
            if not commodity_data:
                commodity_data = {"sentiment": "平稳", "score": 0}

            if use_cache and self.cache_enabled:
                try:
                    self.cache_manager.set(cache_key, commodity_data, ttl=self.market_data_ttl)
                except Exception as e:
                    logger.warning(f"Failed to cache commodity sentiment: {e}")

            return commodity_data

        except Exception as e:
            logger.error(f"Failed to get commodity sentiment: {e}")
            # 返回降级数据
            return {"sentiment": "平稳", "score": 0, "error": str(e)}

    @timed_metric(metric_type="external_api", name="get_hot_sectors")
    def get_hot_sectors(self, limit: int = 10, use_cache: bool = True) -> list[dict]:
        """
        获取热点板块

        Args:
            limit: 返回数量限制
            use_cache: 是否使用缓存

        Returns:
            热点板块列表
        """
        try:
            cache_key = f"{self.sectors_key}:{limit}"

            if use_cache and self.cache_enabled:
                cached = self.cache_manager.get(cache_key)
                if cached:
                    return cached

            sectors = fetch_hot_sectors(limit)
            if not sectors:
                sectors = []

            if use_cache and self.cache_enabled:
                try:
                    self.cache_manager.set(cache_key, sectors, ttl=self.sectors_ttl)
                except Exception as e:
                    logger.warning(f"Failed to cache hot sectors: {e}")

            return sectors

        except Exception as e:
            logger.error(f"Failed to get hot sectors: {e}")
            return []

    @timed_metric(metric_type="external_api", name="get_market_news")
    def get_market_news(self, limit: int = 10, use_cache: bool = True) -> list[dict]:
        """
        获取市场新闻

        Args:
            limit: 返回数量限制
            use_cache: 是否使用缓存

        Returns:
            市场新闻列表
        """
        try:
            cache_key = f"{self.news_key}:{limit}"

            if use_cache and self.cache_enabled:
                cached = self.cache_manager.get(cache_key)
                if cached:
                    return cached

            news = fetch_market_news(limit)
            if not news:
                news = []

            if use_cache and self.cache_enabled:
                try:
                    self.cache_manager.set(cache_key, news, ttl=self.news_ttl)
                except Exception as e:
                    logger.warning(f"Failed to cache market news: {e}")

            return news

        except Exception as e:
            logger.error(f"Failed to get market news: {e}")
            return []

    @timed_metric(metric_type="external_api", name="get_full_market_data")
    def get_full_market_data(self, use_cache: bool = True) -> dict:
        """
        获取完整市场数据（并行获取所有组件）

        Args:
            use_cache: 是否使用缓存

        Returns:
            完整市场数据字典
        """
        try:
            if use_cache and self.cache_enabled:
                cached = self.cache_manager.get(self.market_data_key)
                if cached:
                    logger.debug("Using cached full market data")
                    return cached

            # 并行获取所有市场数据
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                sentiment_future = executor.submit(self.get_market_sentiment, False)  # 不使用缓存，避免嵌套缓存
                commodity_future = executor.submit(self.get_commodity_sentiment, False)
                sectors_future = executor.submit(self.get_hot_sectors, 5, False)
                news_future = executor.submit(self.get_market_news, 10, False)

                sentiment = sentiment_future.result()
                commodity = commodity_future.result()
                sectors = sectors_future.result()
                news = news_future.result()

            # 构建完整市场数据
            market_data = {
                "market_sentiment": sentiment.get("sentiment", "平稳"),
                "market_score": sentiment.get("score", 0),
                "commodity_sentiment": commodity.get("sentiment", "平稳"),
                "commodity_score": commodity.get("score", 0),
                "hot_sectors": sectors,
                "market_news": news,
                "fetched_at": datetime.now().isoformat(),
            }

            # 设置缓存
            if use_cache and self.cache_enabled:
                try:
                    self.cache_manager.set(self.market_data_key, market_data, ttl=self.market_data_ttl)
                except Exception as e:
                    logger.warning(f"Failed to cache full market data: {e}")

            return market_data

        except Exception as e:
            logger.error(f"Failed to get full market data: {e}")
            # 返回降级数据
            return {
                "market_sentiment": "平稳",
                "market_score": 0,
                "commodity_sentiment": "平稳",
                "commodity_score": 0,
                "hot_sectors": [],
                "market_news": [],
                "fetched_at": datetime.now().isoformat(),
                "error": str(e),
            }

    def clear_cache(self, pattern: str = None) -> bool:
        """
        清理市场数据缓存

        Args:
            pattern: 缓存键模式，如 "market:v1:*"，None表示清理所有市场缓存

        Returns:
            是否成功
        """
        try:
            if not self.cache_enabled:
                return True

            redis_client = get_redis_client()
            if not redis_client:
                return False

            if pattern is None:
                pattern = f"{self.cache_prefix}*"

            # 查找匹配的键
            keys = []
            cursor = 0
            while True:
                cursor, found_keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
                keys.extend(found_keys)
                if cursor == 0:
                    break

            # 删除键
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys matching {pattern}")

            return True

        except Exception as e:
            logger.error(f"Failed to clear market cache: {e}")
            return False


# 全局服务实例
_market_service_instance = None


def get_market_service(cache_enabled: bool = True) -> MarketService:
    """获取市场服务实例（单例模式）"""
    global _market_service_instance
    if _market_service_instance is None:
        _market_service_instance = MarketService(cache_enabled=cache_enabled)
    return _market_service_instance
