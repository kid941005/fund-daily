"""
Tests for validation module
"""

import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.validation import (
    validate_fund_code,
    validate_limit,
    validate_page,
    validate_username,
    validate_password,
    ValidationError
)


class TestValidateFundCode:
    """Tests for fund code validation"""
    
    def test_valid_fund_code(self):
        """Test valid fund codes"""
        assert validate_fund_code("000001") == "000001"
        assert validate_fund_code("110022") == "110022"
        assert validate_fund_code("161725") == "161725"
    
    def test_invalid_length(self):
        """Test invalid length fund codes"""
        with pytest.raises(ValidationError) as exc:
            validate_fund_code("00001")
        assert "6位数字" in str(exc.value)
        
        with pytest.raises(ValidationError) as exc:
            validate_fund_code("0000001")
        assert "6位数字" in str(exc.value)
    
    def test_non_numeric(self):
        """Test non-numeric fund codes"""
        with pytest.raises(ValidationError) as exc:
            validate_fund_code("00000A")
        assert "6位数字" in str(exc.value)
    
    def test_empty_string(self):
        """Test empty fund code"""
        with pytest.raises(ValidationError) as exc:
            validate_fund_code("")
        assert "不能为空" in str(exc.value)
    
    def test_none_value(self):
        """Test None fund code"""
        with pytest.raises(ValidationError) as exc:
            validate_fund_code(None)
        assert "不能为空" in str(exc.value)


class TestValidateLimit:
    """Tests for limit validation"""
    
    def test_valid_limit(self):
        """Test valid limits"""
        assert validate_limit(10) == 10
        assert validate_limit(1) == 1
        assert validate_limit(100) == 100
    
    def test_invalid_limit(self):
        """Test invalid limits"""
        with pytest.raises(ValidationError) as exc:
            validate_limit(0)
        assert "1 到 100 之间" in str(exc.value)
        
        with pytest.raises(ValidationError) as exc:
            validate_limit(101)
        assert "1 到 100 之间" in str(exc.value)
    
    def test_custom_range(self):
        """Test custom range"""
        assert validate_limit(50, min_value=10, max_value=100) == 50
        
        with pytest.raises(ValidationError):
            validate_limit(5, min_value=10, max_value=100)


class TestValidatePage:
    """Tests for page validation"""
    
    def test_valid_page(self):
        """Test valid pages"""
        assert validate_page(1) == 1
        assert validate_page(10) == 10
    
    def test_invalid_page(self):
        """Test invalid pages"""
        with pytest.raises(ValidationError) as exc:
            validate_page(0)
        assert "大于等于 1" in str(exc.value)
        
        with pytest.raises(ValidationError) as exc:
            validate_page(-1)
        assert "大于等于 1" in str(exc.value)
    
    def test_custom_min(self):
        """Test custom minimum"""
        assert validate_page(5, min_value=5) == 5
        
        with pytest.raises(ValidationError):
            validate_page(4, min_value=5)


class TestValidateUsername:
    """Tests for username validation"""
    
    def test_valid_username(self):
        """Test valid usernames"""
        assert validate_username("testuser") == "testuser"
        assert validate_username("user123") == "user123"
        assert validate_username("test_user") == "test_user"
    
    def test_invalid_username(self):
        """Test invalid usernames"""
        # Too short
        with pytest.raises(ValidationError) as exc:
            validate_username("ab")
        assert "3 到 50" in str(exc.value)
        
        # Invalid characters
        with pytest.raises(ValidationError) as exc:
            validate_username("test@user")
        assert "字母、数字和下划线" in str(exc.value)
        
        # Empty
        with pytest.raises(ValidationError) as exc:
            validate_username("")
        assert "不能为空" in str(exc.value)


class TestValidatePassword:
    """Tests for password validation"""
    
    def test_valid_password(self):
        """Test valid passwords"""
        assert validate_password("password123") == "password123"
        assert validate_password("secret") == "secret"  # 最小长度6
    
    def test_invalid_password(self):
        """Test invalid passwords"""
        # Too short
        with pytest.raises(ValidationError) as exc:
            validate_password("12345")
        assert "至少为 6" in str(exc.value)
        
        # Contains space
        with pytest.raises(ValidationError) as exc:
            validate_password("pass word")
        assert "不能包含空格" in str(exc.value)
        
        # Empty
        with pytest.raises(ValidationError) as exc:
            validate_password("")
        assert "不能为空" in str(exc.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])