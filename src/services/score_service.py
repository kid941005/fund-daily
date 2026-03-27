"""
统一评分服务 - 直接使用具体模块（无接口层依赖）
向后兼容的适配器层，供 FundService 使用
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from src.utils.error_handling import handle_errors

logger = logging.getLogger(__name__)


def _get_cache_manager():
    """延迟导入，避免循环依赖"""
    from src.cache.manager import get_cache_manager

    return get_cache_manager()


class ScoreService:
    """统一评分服务（直接调用具体模块）"""

    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._config = None

    @property
    def config(self):
        if self._config is None:
            from src.config import get_config

            self._config = get_config()
        return self._config

    @handle_errors(default_return={"total_score": 0.0, "grade": "N/A", "error": True}, log_level="error")
    def calculate_score(self, fund_code: str, use_cache: bool = True) -> Dict[str, Any]:
        """计算基金评分（兼容旧接口）"""
        from src.cache.manager import get_cache_manager
        from src.fetcher import (
            fetch_commodity_prices,
            fetch_fund_data,
            fetch_hot_sectors,
            fetch_market_news,
        )
        from src.analyzer import get_enhanced_market_sentiment
        from src.scoring.calculator import calculate_total_score

        cache = get_cache_manager()
        cache_prefix = f"score:v3:{self.config.app.version}:"
        cache_ttl = self.config.cache.duration

        cache_key = f"{cache_prefix}{fund_code}"

        # 1. 尝试从缓存获取
        if use_cache:
            cached = cache.get(cache_key)
            if cached and isinstance(cached, dict):
                logger.info(f"评分缓存命中: {fund_code}")
                cached["from_cache"] = True
                return cached

        # 2. 获取基金数据
        fund_data = fetch_fund_data(fund_code, use_cache=use_cache)
        if not fund_data:
            return {"total_score": 0.0, "grade": "E", "details": {"error": "获取基金数据失败"}, "fund_code": fund_code}

        # 3. 获取市场数据
        try:
            sentiment_result = get_enhanced_market_sentiment()
        except Exception as e:
            logger.warning(f"获取市场情绪失败: {e}")
            sentiment_result = {"sentiment": "平稳", "score": 5}

        try:
            hot_sectors = fetch_hot_sectors()
        except Exception as e:
            logger.warning(f"获取热门板块失败: {e}")
            hot_sectors = []

        try:
            news = fetch_market_news()
        except Exception as e:
            logger.warning(f"获取市场新闻失败: {e}")
            news = []

        try:
            prices = fetch_commodity_prices()
            if prices:
                changes = [float(v) for v in prices.values() if v is not None]
                avg_change = sum(changes) / len(changes) if changes else 0
                if avg_change > 2:
                    commodity_sentiment = "乐观"
                elif avg_change > 0:
                    commodity_sentiment = "偏多"
                elif avg_change > -2:
                    commodity_sentiment = "平稳"
                else:
                    commodity_sentiment = "偏空"
            else:
                commodity_sentiment = "平稳"
        except Exception as e:
            logger.warning(f"获取商品情绪失败: {e}")
            commodity_sentiment = "平稳"

        # 4. 提取评分所需字段
        raw_data = fund_data.get("data", {}) if isinstance(fund_data, dict) else {}
        fund_detail = raw_data.get("detail", {})
        daily_change = float(raw_data.get("gszzl") or 0)

        # 5. 计算评分
        try:
            result = calculate_total_score(
                fund_detail=fund_detail or {},
                risk_metrics={"volatility": 0.0, "max_drawdown": 0.0, "sharpe_ratio": 0.0},
                market_sentiment=sentiment_result.get("sentiment", "平稳"),
                market_score=int(sentiment_result.get("score", 5)),
                news=news,
                hot_sectors=hot_sectors,
                commodity_sentiment=commodity_sentiment,
                fund_manager={},
                fund_type="stock",
                fund_scale=10.0,
                daily_change=daily_change,
                fund_data=raw_data,
                fund_code=fund_code,
                use_cache=use_cache,
            )
        except Exception as e:
            logger.error(f"计算评分异常: {fund_code}, {e}")
            result = {"total_score": 0, "grade": "E", "details": {"error": str(e)}}

        # 6. 格式化返回
        total_score = float(result.get("total_score", 0))
        breakdown = result.get("details", {})

        formatted = {
            "total_score": total_score,
            "breakdown": breakdown,  # 兼容旧接口
            "grade": result.get("grade", "E"),
            "details": result,
            "fund_code": fund_code,
            "timestamp": datetime.now().isoformat(),
        }

        # 7. 写入缓存
        if use_cache:
            cache.set(cache_key, formatted, cache_ttl)

        return formatted

    def batch_calculate_scores(self, fund_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量计算评分（兼容旧接口）"""
        results = {}
        for code in fund_codes:
            try:
                results[code] = self.calculate_score(code)
            except Exception as e:
                logger.error(f"批量计算评分失败: {code}, {e}")
                results[code] = {"total_score": 0.0, "grade": "E", "details": {"error": str(e)}}
        return results


# 单例模式
_score_service_instance = None


def get_score_service() -> ScoreService:
    """获取评分服务实例（单例）"""
    global _score_service_instance
    if _score_service_instance is None:
        _score_service_instance = ScoreService(cache_enabled=True)
        logger.info("评分服务初始化完成（v2 - 直接模块调用）")
    return _score_service_instance


def test_score_service():
    """测试评分服务"""
    try:
        service = get_score_service()
        result = service.calculate_score("000001")
        print(f"✅ 评分服务测试成功: {result.get('total_score', 0)}分 ({result.get('grade', 'N/A')})")
        return True
    except Exception as e:
        print(f"❌ 评分服务测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_score_service()
