"""
Tests for analyzer module
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analyzer import (
    calculate_risk_metrics,
    get_market_sentiment,
    get_commodity_sentiment,
    calculate_expected_return,
)


class TestCalculateRiskMetrics:
    """Tests for risk metrics calculation"""
    
    def test_high_risk_fund(self):
        """Test high risk fund detection"""
        # 股票型基金应该是高风险
        result = calculate_risk_metrics(15, 30, 50, "股票型")
        
        assert result["risk_level"] == "高风险"
        assert result["risk_score"] >= 7
    
    def test_low_risk_fund(self):
        """Test low risk fund detection"""
        result = calculate_risk_metrics(1, 3, 5)
        
        assert result["risk_level"] in ["中低风险", "中等风险"]
    
    def test_positive_sharpe_ratio(self):
        """Test positive Sharpe ratio"""
        result = calculate_risk_metrics(5, 15, 30)
        
        assert result["sharpe_ratio"] > 0
    
    def test_negative_sharpe_ratio(self):
        """Test negative Sharpe ratio"""
        result = calculate_risk_metrics(-5, -10, -15)
        
        assert result["sharpe_ratio"] <= 0
    
    def test_max_drawdown_estimation(self):
        """Test max drawdown estimation"""
        result = calculate_risk_metrics(10, 20, 25)
        
        # Volatility = 10, max_drawdown should be around 15 (volatility * 1.5, capped at 50)
        assert result["estimated_max_drawdown"] > 0
        assert result["estimated_max_drawdown"] <= 50
    
    def test_risk_suggestion(self):
        """Test risk suggestion content"""
        result = calculate_risk_metrics(20, 30, 40)
        
        assert "suggestion" in result
        assert len(result["suggestion"]) > 0


class TestGetMarketSentiment:
    """Tests for market sentiment analysis"""
    
    @patch('src.analyzer.sentiment.fetch_hot_sectors')
    @patch('src.analyzer.sentiment.fetch_market_news')
    def test_bullish_sentiment(self, mock_news, mock_sectors):
        """Test bullish market sentiment"""
        # More up sectors than down
        mock_sectors.return_value = [
            {"name": "新能源", "change": 8.0},
            {"name": "消费", "change": 6.0},
            {"name": "医药", "change": 5.0},
        ]
        mock_news.return_value = [
            {"title": "A股暴涨创新高"},
            {"title": "市场全面看好牛市来了"},
        ]
        
        result = get_market_sentiment()
        
        # Should be optimistic
        assert result["sentiment"] in ["乐观", "偏多"]
    
    @patch('src.analyzer.sentiment.fetch_hot_sectors')
    @patch('src.analyzer.sentiment.fetch_market_news')
    def test_bearish_sentiment(self, mock_news, mock_sectors):
        """Test bearish market sentiment"""
        mock_sectors.return_value = [
            {"name": "新能源", "change": -8.0},
            {"name": "消费", "change": -6.0},
            {"name": "医药", "change": -5.0},
        ]
        mock_news.return_value = [
            {"title": "A股暴跌创新低"},
            {"title": "市场恐慌崩盘了"},
        ]
        
        result = get_market_sentiment()
        
        # Should be pessimistic
        assert result["sentiment"] in ["偏空", "恐慌"]
    
    @patch('src.analyzer.sentiment.fetch_hot_sectors')
    @patch('src.analyzer.sentiment.fetch_market_news')
    def test_neutral_sentiment(self, mock_news, mock_sectors):
        """Test neutral market sentiment"""
        mock_sectors.return_value = [
            {"name": "板块1", "change": 0.5},
            {"name": "板块2", "change": -0.3},
        ]
        mock_news.return_value = []
        
        result = get_market_sentiment()
        
        # Should be neutral
        assert result["sentiment"] in ["平稳", "偏多", "偏空"]
    
    @patch('src.analyzer.fetch_hot_sectors')
    @patch('src.analyzer.fetch_market_news')
    def test_score_bounds(self, mock_news, mock_sectors):
        """Test sentiment score is within bounds"""
        # Extreme values
        mock_sectors.return_value = [
            {"name": "板块1", "change": 100.0},
        ] * 10
        mock_news.return_value = [{"title": "涨涨涨涨涨"}] * 10
        
        result = get_market_sentiment()
        
        # Score should be clamped to -100 to 100
        assert -100 <= result["score"] <= 100


class TestCalculateExpectedReturn:
    """Tests for expected return calculation"""
    
    @patch('src.analyzer.fetch_hot_sectors')
    def test_with_holdings(self, mock_sectors):
        """Test expected return with holdings"""
        mock_sectors.return_value = [
            {"name": "新能源", "change": 2.0},
            {"name": "消费", "change": 1.0},
        ]
        
        holdings = [
            {"code": "000001", "name": "华夏成长混合", "amount": 10000}
        ]
        
        funds_data = [
            {"fund_code": "000001", "daily_change": 1.5}
        ]
        
        result = calculate_expected_return(holdings, funds_data)
        
        assert "expected_return" in result
        assert "total_value" in result
        assert result["total_value"] == 10000
    
    def test_empty_holdings(self):
        """Test with empty holdings"""
        result = calculate_expected_return([], [])
        
        assert "expected_return" in result or "error" in result
    
    def test_empty_funds_data(self):
        """Test with empty funds data"""
        holdings = [
            {"code": "000001", "name": "测试", "amount": 10000}
        ]
        
        result = calculate_expected_return(holdings, [])
        
        assert "error" in result or "expected_return" in result
