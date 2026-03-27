"""
Tests for fund service module
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.fund_service import FundService, get_fund_service


class TestFundService:
    """Tests for FundService"""

    def test_init(self):
        """Test service initialization"""
        service = FundService()
        assert service is not None

    def test_get_fund_service(self):
        """Test factory function returns FundService"""
        service = get_fund_service()
        assert isinstance(service, FundService)

    def test_service_has_required_methods(self):
        """Test service has all required methods"""
        service = FundService()

        assert hasattr(service, "get_fund_data")
        assert hasattr(service, "get_fund_score")
        assert hasattr(service, "get_market_data")
        assert hasattr(service, "calculate_holdings_advice")

    def test_max_workers_default(self):
        """Test default max_workers"""
        service = FundService()
        assert hasattr(service, "max_workers")
        assert service.max_workers == 4


class TestServiceConfiguration:
    """Tests for service configuration"""

    def test_cache_prefix(self):
        """Test cache prefix configuration"""
        service = FundService()
        assert hasattr(service, "cache_prefix")
        assert isinstance(service.cache_prefix, str)

    def test_cache_enabled(self):
        """Test cache can be disabled"""
        service = FundService(cache_enabled=False)
        # Just verify it doesn't crash
        assert service is not None
