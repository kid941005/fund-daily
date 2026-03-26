#!/usr/bin/env python3
"""
缓存键生成工具

提供统一的缓存键生成函数，避免重复的缓存键生成逻辑。
"""

from typing import List, Optional, Union

from src.constants import CACHE_PREFIXES


class CacheKeyGenerator:
    """缓存键生成器"""

    @staticmethod
    def fund_data(fund_code: str) -> str:
        """生成基金数据缓存键"""
        prefix = CACHE_PREFIXES.get("fund", "fund_daily:v2:")
        return f"{prefix}data:{fund_code}"

    @staticmethod
    def fund_detail(fund_code: str) -> str:
        """生成基金详情缓存键"""
        prefix = CACHE_PREFIXES.get("fund", "fund_daily:v2:")
        return f"{prefix}detail:{fund_code}"

    @staticmethod
    def fund_score(fund_code: str) -> str:
        """生成基金评分缓存键"""
        prefix = CACHE_PREFIXES.get("scoring", "fund_score:v2:")
        return f"{prefix}{fund_code}"

    @staticmethod
    def market_sentiment(category: Optional[str] = None) -> str:
        """生成市场情绪缓存键

        Args:
            category: 可选分类，如 "commodity"
        """
        prefix = CACHE_PREFIXES.get("market", "market:v2:")
        if category:
            return f"{prefix}sentiment:{category}"
        return f"{prefix}sentiment"

    @staticmethod
    def market_news(limit: Optional[int] = None) -> str:
        """生成市场新闻缓存键"""
        prefix = CACHE_PREFIXES.get("market", "market:v2:")
        if limit:
            return f"{prefix}news:{limit}"
        return f"{prefix}news"

    @staticmethod
    def hot_sectors(limit: Optional[int] = None) -> str:
        """生成热点板块缓存键"""
        prefix = CACHE_PREFIXES.get("market", "market:v2:")
        if limit:
            return f"{prefix}sectors:{limit}"
        return f"{prefix}sectors"

    @staticmethod
    def fund_manager(fund_code: str) -> str:
        """生成基金经理缓存键"""
        prefix = CACHE_PREFIXES.get("fund", "fund_daily:v2:")
        return f"{prefix}manager:{fund_code}"

    @staticmethod
    def user_holdings(user_id: str) -> str:
        """生成用户持仓缓存键"""
        return f"user:holdings:{user_id}"

    @staticmethod
    def user_watchlist(user_id: str) -> str:
        """生成用户关注列表缓存键"""
        return f"user:watchlist:{user_id}"

    @staticmethod
    def custom(prefix_key: str, *parts: Union[str, int]) -> str:
        """
        生成自定义缓存键

        Args:
            prefix_key: CACHE_PREFIXES 中的键
            *parts: 缓存键的组成部分

        Returns:
            格式化的缓存键
        """
        prefix = CACHE_PREFIXES.get(prefix_key, f"{prefix_key}:v2:")
        parts_str = ":".join(str(part) for part in parts if part is not None)
        return f"{prefix}{parts_str}" if parts_str else prefix


# 创建单例实例
cache_keys = CacheKeyGenerator()


# 向后兼容的函数
def get_fund_data_key(fund_code: str) -> str:
    """获取基金数据缓存键（向后兼容）"""
    return cache_keys.fund_data(fund_code)


def get_fund_score_key(fund_code: str) -> str:
    """获取基金评分缓存键（向后兼容）"""
    return cache_keys.fund_score(fund_code)


def get_market_news_key(limit: Optional[int] = None) -> str:
    """获取市场新闻缓存键（向后兼容）"""
    return cache_keys.market_news(limit)


if __name__ == "__main__":
    # 测试缓存键生成
    test_cases = [
        ("000001", cache_keys.fund_data("000001")),
        ("000001", cache_keys.fund_detail("000001")),
        ("000001", cache_keys.fund_score("000001")),
        (None, cache_keys.market_sentiment()),
        (10, cache_keys.market_news(10)),
        (5, cache_keys.hot_sectors(5)),
        ("000001", cache_keys.fund_manager("000001")),
        ("user123", cache_keys.user_holdings("user123")),
        ("custom", cache_keys.custom("test", "key", 1, "value")),
    ]

    print("🔑 缓存键生成测试:")
    for input_val, key in test_cases:
        if input_val:
            print(f"  输入: {input_val} → 键: {key}")
        else:
            print(f"  键: {key}")

    print(f"\n✅ 缓存键生成器测试完成")
