"""
Tests for advice module
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.advice import (
    analyze_fund,
    generate_daily_report,
    format_report_for_share,
    generate_advice,
    get_fund_detail_info,
)


class TestAnalyzeFund:
    """Tests for fund analysis"""
    
    def test_analyze_fund_up(self, mock_fund_data_positive):
        """Test analyzing fund with positive change"""
        result = analyze_fund(mock_fund_data_positive)
        
        assert result["trend"] == "up"
        assert result["daily_change"] == 1.25
    
    def test_analyze_fund_down(self, mock_fund_data):
        """Test analyzing fund with negative change"""
        result = analyze_fund(mock_fund_data)
        
        assert result["trend"] == "down"
        assert result["daily_change"] == -0.69
    
    def test_analyze_fund_error(self):
        """Test analyzing fund with error data"""
        result = analyze_fund({"error": "Network error"})
        
        assert "error" in result
    
    def test_analyze_fund_no_data(self):
        """Test analyzing fund with no data"""
        result = analyze_fund({})
        
        assert "error" in result
    
    def test_generate_summary_positive(self):
        """Test summary generation for positive change"""
        fund_data = {"fundcode": "000001", "name": "测试基金", "dwjz": "1.5", "gszzl": "3.5"}
        
        result = analyze_fund(fund_data)
        
        assert "🚀" in result["summary"] or "📈" in result["summary"]
    
    def test_generate_summary_negative(self):
        """Test summary generation for negative change"""
        fund_data = {"fundcode": "000001", "name": "测试基金", "dwjz": "1.5", "gszzl": "-3.5"}
        
        result = analyze_fund(fund_data)
        
        assert "📉" in result["summary"] or "🔻" in result["summary"]


class TestGenerateDailyReport:
    """Tests for daily report generation"""
    
    @patch('src.advice.fetch_fund_data')
    def test_generate_report(self, mock_fetch):
        """Test report generation"""
        mock_fetch.return_value = {
            "fundcode": "000001",
            "name": "测试基金",
            "dwjz": "1.0",
            "gsz": "1.01",
            "gszzl": "1.0"
        }
        
        result = generate_daily_report(["000001"])
        
        assert "date" in result
        assert "funds" in result
        assert "summary" in result
        assert len(result["funds"]) > 0
    
    @patch('src.advice.fetch_fund_data')
    def test_report_summary_counts(self, mock_fetch):
        """Test report summary counts"""
        mock_fetch.return_value = {
            "fundcode": "000001",
            "name": "测试基金",
            "dwjz": "1.0",
            "gsz": "1.01",
            "gszzl": "1.0"
        }
        
        result = generate_daily_report(["000001"])
        
        summary = result["summary"]
        assert summary["total"] >= 1


class TestFormatReportForShare:
    """Tests for share formatting"""
    
    def test_format_report(self):
        """Test report formatting for sharing"""
        report = {
            "date": "2026-03-12",
            "funds": [
                {
                    "fund_code": "000001",
                    "fund_name": "测试基金",
                    "nav": "1.0",
                    "estimate_nav": "1.01",
                    "daily_change": 1.0,
                    "change_percent": "1.0%",
                    "summary": "📈 测试基金 今日上涨 1.0%，净值 1.0"
                }
            ],
            "summary": {
                "total": 1,
                "up": 1,
                "down": 0,
                "flat": 0,
                "market_sentiment": "乐观"
            }
        }
        
        result = format_report_for_share(report)
        
        assert "每日基金报告" in result
        assert "2026-03-12" in result
        assert "上涨" in result
        assert "仅供参考" in result


class TestGenerateAdvice:
    """Tests for advice generation"""
    
    def test_advice_with_empty_funds(self):
        """Test advice with no funds"""
        result = generate_advice([])
        
        assert "action" in result
        assert result["action"] == "观望"
    
    @patch('src.advice.get_market_sentiment')
    @patch('src.advice.fetch_fund_detail')
    def test_advice_bullish_market(self, mock_detail, mock_sentiment):
        """Test advice with bullish market"""
        mock_sentiment.return_value = {
            "sentiment": "乐观",
            "score": 50
        }
        mock_detail.return_value = {}
        
        funds = [
            {
                "fund_code": "000001",
                "fund_name": "测试基金",
                "daily_change": 2.0,
                "trend": "up"
            }
        ]
        
        result = generate_advice(funds)
        
        assert result["action"] in ["买入", "持有"]
        assert result["market_sentiment"] == "乐观"
    
    @patch('src.advice.get_market_sentiment')
    @patch('src.advice.fetch_fund_detail')
    def test_advice_bearish_market(self, mock_detail, mock_sentiment):
        """Test advice with bearish market"""
        mock_sentiment.return_value = {
            "sentiment": "恐慌",
            "score": -50
        }
        mock_detail.return_value = {}
        
        funds = [
            {
                "fund_code": "000001",
                "fund_name": "测试基金",
                "daily_change": -3.0,
                "trend": "down"
            }
        ]
        
        result = generate_advice(funds)
        
        assert result["action"] in ["减仓", "卖出"]
        assert result["market_sentiment"] == "恐慌"
    
    @patch('src.advice.get_market_sentiment')
    @patch('src.advice.fetch_fund_detail')
    def test_advice_high_position(self, mock_detail, mock_sentiment):
        """Test advice with high position ratio"""
        mock_sentiment.return_value = {
            "sentiment": "乐观",
            "score": 30
        }
        mock_detail.return_value = {}
        
        funds = [
            {
                "fund_code": "000001",
                "fund_name": "测试基金",
                "daily_change": 2.0,
                "trend": "up",
                "amount": 950000,  # High position
            }
        ]
        
        result = generate_advice(funds)
        
        # Should warn about high position
        assert "90" in str(result.get("position_ratio", 0)) or "持有" in result.get("action", "")
    
    @patch('src.advice.get_market_sentiment')
    @patch('src.advice.get_commodity_sentiment')
    @patch('src.advice.fetch_fund_detail')
    def test_advice_includes_commodity(self, mock_detail, mock_commodity, mock_sentiment):
        """Test advice includes commodity info"""
        mock_sentiment.return_value = {"sentiment": "平稳", "score": 0}
        mock_commodity.return_value = {
            "sentiment": "通胀",
            "score": 15,
            "details": {"gold": {"name": "黄金", "change": 1.0}}
        }
        mock_detail.return_value = {}
        
        funds = [{"fund_code": "000001", "fund_name": "测试", "daily_change": 0, "trend": "flat"}]
        
        result = generate_advice(funds)
        
        assert "commodity_sentiment" in result
        assert "commodity_score" in result


class TestGetFundDetailInfo:
    """Tests for fund detail info"""
    
    @patch('src.advice.fetch_fund_data')
    @patch('src.advice.fetch_fund_detail')
    def test_get_detail_success(self, mock_fetch_detail, mock_fetch_data):
        """Test successful detail fetch"""
        mock_fetch_data.return_value = {
            "fundcode": "000001",
            "name": "测试基金"
        }
        mock_fetch_detail.return_value = {}
        
        result = get_fund_detail_info("000001")
        
        assert "fund_code" in result
        assert result["fund_code"] == "000001"
    
    @patch('src.advice.fetch_fund_data')
    def test_get_detail_error(self, mock_fetch_data):
        """Test detail fetch error"""
        mock_fetch_data.side_effect = Exception("Not found")
        
        result = get_fund_detail_info("000001")
        
        assert "error" in result
