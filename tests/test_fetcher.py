"""
Tests for fetcher module
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fetcher import (
    fetch_fund_data,
    fetch_fund_detail,
    fetch_market_news,
    fetch_hot_sectors,
    fetch_commodity_prices,
    get_cache,
    set_cache,
    clear_cache,
)


class TestCache:
    """Tests for cache functionality"""

    def test_set_and_get_cache(self):
        """Test basic cache operations"""
        set_cache("test_key", {"value": 123})
        result = get_cache("test_key")
        assert result == {"value": 123}

    def test_cache_expiry(self):
        """Test cache expiration"""
        import time
        from src.cache.lru_cache import LRUCache

        # 创建短期缓存测试过期
        short_cache = LRUCache(max_size=100, default_ttl=1)
        short_cache.set("test_key", "test_value")

        result = short_cache.get("test_key")
        assert result == "test_value"

        # 等待过期
        time.sleep(1.5)

        result = short_cache.get("test_key")
        assert result is None, "Cache should expire"

    def test_clear_cache(self):
        """Test cache clearing"""
        set_cache("key1", "value1")
        set_cache("key2", "value2")

        # Get value before clearing
        value1 = get_cache("key1")
        assert value1 == "value1"

        clear_cache()

        # After clearing, cache should be empty
        value1_after = get_cache("key1")
        value2_after = get_cache("key2")
        assert value1_after is None
        assert value2_after is None


class TestFetchFundData:
    """Tests for fund data fetching"""

    @patch('src.fetcher.fund_basic.fetcher._make_request')
    def test_fetch_fund_data_success(self, mock_request):
        """Test successful fund data fetch"""
        mock_request.return_value = 'jsonpgz({"fundcode":"000001","name":"测试基金","dwjz":"1.500","gsz":"1.520","gszzl":"1.5","gztime":"2026-03-20 10:00"});'

        result = fetch_fund_data("000001")

        assert result["code"] == "000001"
        assert result["name"] == "测试基金"
        assert result["estimated_change"] == 1.5

    @patch('src.fetcher.fund_basic.fetcher._make_request')
    def test_fetch_fund_data_error(self, mock_request):
        """Test fund data fetch error"""
        mock_request.return_value = None

        result = fetch_fund_data("000001")

        assert "error" in result

    @patch('src.fetcher.fund_basic.fetcher._make_request')
    def test_fetch_fund_data_invalid_format(self, mock_request):
        """Test invalid response format"""
        mock_request.return_value = "invalid data"

        result = fetch_fund_data("000001")

        assert "error" in result

    @patch('src.fetcher.fund_basic.fetcher._make_request')
    @patch('src.fetcher.fund_basic.fetcher.get_cache')
    @patch('src.fetcher.fund_basic.fetcher.set_cache')
    def test_fetch_uses_cache(self, mock_set_cache, mock_get_cache, mock_request):
        """Test that cache is used"""
        mock_request.return_value = 'jsonpgz({"fundcode":"000001","name":"测试","dwjz":"1.000","gsz":"1.010","gszzl":"1.0","gztime":"2026-03-20 10:00"});'
        
        # First call: cache miss, should call API
        mock_get_cache.return_value = None
        fetch_fund_data("000001")
        
        # Second call: cache hit, should NOT call API
        mock_get_cache.return_value = {"fundcode": "000001", "name": "测试", "dwjz": "1.000", "gsz": "1.010"}
        fetch_fund_data("000001")

        # Should only call API once
        assert mock_request.call_count == 1


class TestFetchMarketNews:
    """Tests for market news fetching"""

    @patch('src.fetcher.market_data.fetcher._make_request')
    def test_fetch_market_news_success(self, mock_request):
        """Test successful news fetch"""
        mock_request.return_value = 'var ajaxResult={"LivesList":[{"title":"测试新闻","showtime":"2026-03-12","source":"东方财富","digest":"摘要"}]}'

        result = fetch_market_news(5)

        assert len(result) > 0
        assert result[0]["title"] == "测试新闻"


class TestFetchHotSectors:
    """Tests for sector data fetching"""

    @patch('src.fetcher.market_data.fetcher._make_request')
    def test_fetch_hot_sectors_success(self, mock_request):
        """Test successful sectors fetch"""
        mock_request.return_value = '{"data":{"diff":[{"f14":"新能源","f3":2.5,"f12":"8801"},{"f14":"医药","f3":-1.2,"f12":"8802"}]}}'

        result = fetch_hot_sectors(10)

        assert len(result) == 2
        assert result[0]["name"] == "新能源"
        assert result[0]["change"] == 2.5
