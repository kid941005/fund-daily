"""
Tests for OCR module
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ocr import (
    FundOcrParser,
    validate_fund_code,
    parse_ocr_result,
    OcrResult
)


class TestValidateFundCode:
    """Tests for fund code validation"""
    
    def test_valid_codes(self):
        """Test valid fund codes"""
        assert validate_fund_code("000001") == True
        assert validate_fund_code("110022") == True
        assert validate_fund_code("161725") == True
        assert validate_fund_code("250001") == True
        assert validate_fund_code("510500") == True
    
    def test_invalid_codes(self):
        """Test invalid fund codes"""
        assert validate_fund_code("12345") == False   # Too short
        assert validate_fund_code("1234567") == False # Too long
        assert validate_fund_code("abcdef") == False   # Not digits
        assert validate_fund_code("900001") == False   # Invalid first digit
        assert validate_fund_code("000000") == False   # Invalid first digit
    
    def test_edge_cases(self):
        """Test edge cases"""
        assert validate_fund_code("") == False
        assert validate_fund_code("12345a") == False


class TestFundOcrParser:
    """Tests for OCR parser"""
    
    def test_keyword_based_parsing(self):
        """Test keyword-based parsing"""
        parser = FundOcrParser()
        
        text = """
        基金持仓
        000001 华夏成长混合
        持有金额 10,000.00
        110022 易方达消费
        持仓金额 20,000.00
        """
        
        results = parser.parse(text)
        
        assert len(results) >= 2
        
        # Should find at least one fund
        codes = [r.code for r in results]
        assert "000001" in codes or "110022" in codes
    
    def test_pattern_based_parsing(self):
        """Test pattern-based parsing"""
        parser = FundOcrParser()
        
        # Text with code + amount on same line
        text = "000001 ¥15,000.00 基金名称"
        
        results = parser.parse(text)
        
        assert len(results) > 0
        assert results[0].code == "000001"
    
    def test_sequential_parsing(self):
        """Test sequential parsing fallback"""
        parser = FundOcrParser()
        
        text = """
        000001
        10,000
        
        110022
        20,000
        """
        
        results = parser.parse(text)
        
        # Should find codes and amounts
        codes = [r.code for r in results]
        assert "000001" in codes
    
    def test_deduplication(self):
        """Test duplicate removal"""
        parser = FundOcrParser()
        
        # Same code appears multiple times
        text = """
        000001 10,000
        000001 ¥10,000.00
        000001 持仓金额 10000
        """
        
        results = parser.parse(text)
        
        # Should have only one entry for 000001
        codes = [r.code for r in results]
        assert codes.count("000001") == 1
    
    def test_amount_validation(self):
        """Test amount range validation"""
        parser = FundOcrParser()
        
        # Amount too small
        text = "000001 10"
        results = parser.parse(text)
        
        # Should not include invalid amounts
        for r in results:
            assert r.amount >= 100
    
    def test_empty_text(self):
        """Test empty input"""
        parser = FundOcrParser()
        
        results = parser.parse("")
        assert len(results) == 0
        
        results = parser.parse("   ")
        assert len(results) == 0


class TestParseOcrResult:
    """Tests for main OCR parsing function"""
    
    def test_valid_funds(self):
        """Test with valid fund text"""
        text = """
        基金持仓页面
        000001 华夏成长 持有金额 10,000元
        110022 易方达消费 持仓金额 20,000元
        161725 白酒指数 资产 15,000元
        """
        
        result = parse_ocr_result(text)
        
        assert result['success'] == True
        assert result['count'] >= 3
        
        # Check all codes are valid
        for fund in result['funds']:
            assert validate_fund_code(fund['code'])
    
    def test_invalid_codes_filtered(self):
        """Test that invalid codes are filtered out"""
        text = """
        123456 10,000  # Invalid first digit
        000001 10,000  # Valid
        """
        
        result = parse_ocr_result(text)
        
        # Only valid code should remain
        for fund in result['funds']:
            assert validate_fund_code(fund['code'])
    
    def test_no_funds_found(self):
        """Test when no funds found"""
        text = """
        这是一段普通的文字
        没有任何基金代码
        1234567890
        """
        
        result = parse_ocr_result(text)
        
        assert result['count'] == 0
        assert result['funds'] == []
