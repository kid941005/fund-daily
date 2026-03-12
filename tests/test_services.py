"""
Tests for fund service module
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from web.services import fund_service


class TestGetFundsForUser:
    """Tests for get_funds_for_user"""
    
    @patch('web.services.fund_service.fetch_fund_data')
    @patch('web.services.fund_service.analyze_fund')
    def test_with_holdings(self, mock_analyze, mock_fetch):
        """Test with user holdings"""
        mock_fetch.return_value = {
            "fundcode": "000001",
            "name": "测试基金",
            "gszzl": "1.0"
        }
        mock_analyze.return_value = {
            "fund_code": "000001",
            "fund_name": "测试基金",
            "trend": "up",
            "daily_change": 1.0
        }
        
        holdings = [{"code": "000001", "amount": 10000}]
        result = fund_service.get_funds_for_user(holdings)
        
        assert len(result) > 0
    
    @patch('web.services.fund_service.fetch_fund_data')
    @patch('web.services.fund_service.analyze_fund')
    def test_with_default_codes(self, mock_analyze, mock_fetch):
        """Test with default codes"""
        mock_fetch.return_value = {"fundcode": "000001", "name": "测试", "gszzl": "1.0"}
        mock_analyze.return_value = {"fund_code": "000001", "trend": "up"}
        
        result = fund_service.get_funds_for_user([])
        
        assert isinstance(result, list)


class TestCalculateSummary:
    """Tests for calculate_summary"""
    
    def test_all_up(self):
        """Test with all funds up"""
        funds = [
            {"trend": "up"},
            {"trend": "up"},
            {"trend": "up"},
        ]
        
        result = fund_service.calculate_summary(funds)
        
        assert result["up"] == 3
        assert result["sentiment"] == "乐观"
    
    def test_all_down(self):
        """Test with all funds down"""
        funds = [
            {"trend": "down"},
            {"trend": "down"},
        ]
        
        result = fund_service.calculate_summary(funds)
        
        assert result["down"] == 2
        assert result["sentiment"] == "谨慎"
    
    def test_mixed(self):
        """Test with mixed trends"""
        funds = [
            {"trend": "up"},
            {"trend": "down"},
            {"trend": "flat"},
        ]
        
        result = fund_service.calculate_summary(funds)
        
        assert result["up"] == 1
        assert result["down"] == 1
        assert result["flat"] == 1


class TestAnalyzePortfolioRisk:
    """Tests for portfolio risk analysis"""
    
    def test_empty_portfolio(self):
        """Test with empty portfolio"""
        result = fund_service.analyze_portfolio_risk([], 0)
        
        assert "message" in result
    
    def test_single_fund(self):
        """Test with single fund"""
        funds = [
            {
                "amount": 10000,
                "risk_metrics": {"risk_score": 5, "risk_level": "中高风险"}
            }
        ]
        
        result = fund_service.analyze_portfolio_risk(funds, 10000)
        
        assert "risk_level" in result
        assert result["fund_count"] == 1
    
    def test_diversification(self):
        """Test diversification scoring"""
        # 3 funds = 一般
        funds = [
            {"amount": 3333, "risk_metrics": {"risk_score": 4}},
            {"amount": 3333, "risk_metrics": {"risk_score": 4}},
            {"amount": 3334, "risk_metrics": {"risk_score": 4}},
        ]
        
        result = fund_service.analyze_portfolio_risk(funds, 10000)
        
        assert result["diversification"] == "一般"
    
    def test_good_diversification(self):
        """Test good diversification"""
        # 5+ funds = 良好
        funds = [
            {"amount": 2000, "risk_metrics": {"risk_score": 4}},
            {"amount": 2000, "risk_metrics": {"risk_score": 4}},
            {"amount": 2000, "risk_metrics": {"risk_score": 4}},
            {"amount": 2000, "risk_metrics": {"risk_score": 4}},
            {"amount": 2000, "risk_metrics": {"risk_score": 4}},
        ]
        
        result = fund_service.analyze_portfolio_risk(funds, 10000)
        
        assert result["diversification"] == "良好"


class TestSuggestAllocation:
    """Tests for allocation suggestions"""
    
    def test_empty_funds(self):
        """Test with empty funds"""
        result = fund_service.suggest_allocation([])
        
        assert "message" in result
    
    def test_high_risk_warning(self):
        """Test high risk warning"""
        funds = [
            {"risk_metrics": {"risk_level": "高风险"}},
            {"risk_metrics": {"risk_level": "高风险"}},
            {"risk_metrics": {"risk_level": "高风险"}},
        ]
        
        result = fund_service.suggest_allocation(funds)
        
        assert any("高风险" in s for s in result["suggestions"])
    
    def test_low_diversity_warning(self):
        """Test low diversity warning"""
        funds = [
            {"risk_metrics": {"risk_level": "中等风险"}},
            {"risk_metrics": {"risk_level": "中等风险"}},
        ]
        
        result = fund_service.suggest_allocation(funds)
        
        assert any("3-5" in s for s in result["suggestions"])
    
    def test_balanced_allocation(self):
        """Test balanced allocation"""
        funds = [
            {"risk_metrics": {"risk_level": "高风险"}},
            {"risk_metrics": {"risk_level": "中等风险"}},
            {"risk_metrics": {"risk_level": "中等风险"}},
            {"risk_metrics": {"risk_level": "中低风险"}},
            {"risk_metrics": {"risk_level": "中低风险"}},
        ]
        
        result = fund_service.suggest_allocation(funds)
        
        # Should have balanced percentages
        assert result["high_risk_pct"] < 50
        assert result["low_risk_pct"] > 0
