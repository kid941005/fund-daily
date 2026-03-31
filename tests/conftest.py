"""
Pytest fixtures and configuration
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_fund_data():
    """Mock fund data from East Money API"""
    return {
        "code": "000001",
        "name": "华夏成长混合",
        "jzrq": "2026-03-11",
        "nav": 1.1080,
        "estimated_nav": 1.1003,
        "estimated_change": -0.69,
        "estimated_change_percent": -0.69,
        "update_time": "2026-03-12 15:00",
        "source": "eastmoney",
    }


@pytest.fixture
def mock_fund_data_positive():
    """Mock fund data with positive change"""
    return {
        "code": "110022",
        "name": "易方达消费行业股票",
        "jzrq": "2026-03-11",
        "nav": 3.2430,
        "estimated_nav": 3.2835,
        "estimated_change": 1.25,
        "estimated_change_percent": 1.25,
        "update_time": "2026-03-12 15:00",
        "source": "eastmoney",
    }


@pytest.fixture
def mock_holdings():
    """Mock user holdings"""
    return [
        {"code": "000001", "name": "华夏成长混合", "amount": 10000},
        {"code": "110022", "name": "易方达消费行业股票", "amount": 20000},
    ]


@pytest.fixture
def mock_sectors():
    """Mock sector data"""
    return [
        {"name": "新能源", "change": 2.5, "code": "8801"},
        {"name": "半导体", "change": -1.2, "code": "8802"},
        {"name": "医药", "change": 0.8, "code": "8803"},
    ]


@pytest.fixture
def mock_news():
    """Mock market news"""
    return [
        {"title": "A股今日大涨", "time": "2026-03-12 14:00", "source": "东方财富"},
        {"title": "新能源板块爆发", "time": "2026-03-12 13:00", "source": "东方财富"},
    ]


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test"""
    from src.fetcher import clear_cache

    clear_cache()
    yield
    clear_cache()
