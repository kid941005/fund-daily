"""
评分服务实现（依赖注入版本）
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..config import get_config
from ..interfaces import FundData, IAnalyzer, ICache, IFetcher, IScorer, IScoreService, MarketData, ScoreResult

logger = logging.getLogger(__name__)


class ScoreServiceImpl(IScoreService):
    """评分服务实现类（依赖注入）"""

    def __init__(self, fetcher: IFetcher, analyzer: IAnalyzer, scorer: IScorer, cache: ICache):
        self.fetcher = fetcher
        self.analyzer = analyzer
        self.scorer = scorer
        self.cache = cache

        # 配置
        config = get_config()
        self.cache_prefix = f"score:v3:{config.app.version}:"
        self.cache_ttl = config.cache.duration

    def calculate_score(self, fund_code: str, use_cache: bool = True) -> ScoreResult:
        """计算基金评分"""
        cache_key = f"{self.cache_prefix}{fund_code}"

        # 检查缓存
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"缓存命中: {fund_code}")
                return ScoreResult(**cached_result)

        try:
            # 获取数据（传递 use_cache 以控制缓存）
            fund_data = self.fetcher.fetch_fund_data(fund_code, use_cache=use_cache)
            if not fund_data:
                return ScoreResult(total_score=0.0, breakdown={}, grade="E", details={"error": "获取基金数据失败"})

            # 获取市场数据
            market_data = self._get_market_data()

            # 计算评分（传递 use_cache 以控制内部缓存）
            result = self.scorer.calculate_score(fund_data, market_data, use_cache=use_cache)

            # 缓存结果
            if use_cache:
                self.cache.set(cache_key, result.__dict__, self.cache_ttl)

            return result

        except Exception as e:
            logger.error(f"计算评分失败: {fund_code}, {e}")
            return ScoreResult(total_score=0.0, breakdown={}, grade="E", details={"error": str(e)})

    def batch_calculate_scores(self, fund_codes: List[str]) -> Dict[str, ScoreResult]:
        """批量计算评分"""
        results = {}

        for code in fund_codes:
            try:
                result = self.calculate_score(code)
                results[code] = result
            except Exception as e:
                logger.error(f"批量计算评分失败: {code}, {e}")
                results[code] = ScoreResult(total_score=0.0, breakdown={}, grade="E", details={"error": str(e)})

        return results

    def _get_market_data(self) -> MarketData:
        """获取市场数据"""
        try:
            # 获取市场情绪
            sentiment_result = self.analyzer.get_market_sentiment()
            commodity_result = self.analyzer.get_commodity_sentiment()

            # 获取热门板块和市场新闻
            hot_sectors = self.fetcher.fetch_hot_sectors()
            news = self.fetcher.fetch_market_news()

            return MarketData(
                sentiment=sentiment_result.get("sentiment", "neutral"),
                score=sentiment_result.get("score", 50.0),
                commodity_sentiment=commodity_result.get("sentiment", "neutral"),
                hot_sectors=hot_sectors,
                news=news,
            )
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return MarketData(sentiment="neutral", score=50.0, commodity_sentiment="neutral", hot_sectors=[], news=[])
