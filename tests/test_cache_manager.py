"""
Tests for cache manager
"""

import sys
import os
import time
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.cache.manager import CacheManager, cached


class TestCacheManager:
    """Tests for CacheManager"""
    
    def test_init(self):
        """Test CacheManager initialization"""
        manager = CacheManager()
        assert manager is not None
        
        stats = manager.get_stats()
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'penetration_protected' in stats
    
    def test_get_set_memory_only(self):
        """Test get/set with memory cache only"""
        # Mock Redis import to simulate no Redis available
        with patch('src.cache.manager.redis_get', side_effect=ImportError("No module named 'redis'")):
            with patch('src.cache.manager.redis_set', side_effect=ImportError("No module named 'redis'")):
                with patch('src.cache.manager.redis_delete', side_effect=ImportError("No module named 'redis'")):
                    # Need to reload module to apply mocks
                    import importlib
                    import src.cache.manager
                    importlib.reload(src.cache.manager)
                    
                    manager = src.cache.manager.CacheManager()
                    
                    # Set value
                    manager.set("test_key", "test_value", 60)
                    
                    # Get value
                    value = manager.get("test_key")
                    assert value == "test_value"
                    
                    # Check stats
                    stats = manager.get_stats()
                    # Hits should be at least 1 (from the get call)
                    assert stats['hits'] >= 1
    
    def test_get_miss(self):
        """Test cache miss"""
        manager = CacheManager()
        
        value = manager.get("non_existent_key", "default")
        assert value == "default"
        
        stats = manager.get_stats()
        assert stats['misses'] == 1
    
    def test_delete(self):
        """Test cache deletion"""
        manager = CacheManager()
        
        manager.set("test_key", "test_value")
        assert manager.get("test_key") == "test_value"
        
        manager.delete("test_key")
        assert manager.get("test_key") is None
    
    def test_clear(self):
        """Test cache clearing"""
        manager = CacheManager()
        
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        
        manager.clear()
        
        assert manager.get("key1") is None
        assert manager.get("key2") is None
    
    def test_get_with_penetration_protection_valid(self):
        """Test penetration protection with valid data"""
        manager = CacheManager()
        
        # Mock loader that returns valid data
        loader = Mock(return_value="valid_data")
        
        # First call (cache miss, loads data)
        value = manager.get_with_penetration_protection(
            "test_key", loader, ttl=300, empty_ttl=60
        )
        assert value == "valid_data"
        assert loader.call_count == 1
        
        # Second call (cache hit)
        value = manager.get_with_penetration_protection(
            "test_key", loader, ttl=300, empty_ttl=60
        )
        assert value == "valid_data"
        assert loader.call_count == 1  # Should not call loader again
        
        stats = manager.get_stats()
        assert stats['hits'] >= 1
    
    def test_get_with_penetration_protection_empty(self):
        """Test penetration protection with empty data"""
        manager = CacheManager()
        
        # Mock loader that returns None
        loader = Mock(return_value=None)
        
        # First call (cache miss, loads empty data)
        value = manager.get_with_penetration_protection(
            "empty_key", loader, ttl=300, empty_ttl=60
        )
        assert value is None
        assert loader.call_count == 1
        
        # Second call (cache hit with empty marker)
        value = manager.get_with_penetration_protection(
            "empty_key", loader, ttl=300, empty_ttl=60
        )
        assert value is None
        assert loader.call_count == 1  # Should not call loader again
        
        stats = manager.get_stats()
        assert stats['penetration_protected'] >= 1
    
    def test_get_with_penetration_protection_error(self):
        """Test penetration protection with loader error"""
        manager = CacheManager()
        
        # Mock loader that raises exception
        loader = Mock(side_effect=ValueError("Loader error"))
        
        try:
            manager.get_with_penetration_protection(
                "error_key", loader, ttl=300, empty_ttl=60
            )
            assert False, "Should have raised exception"
        except ValueError:
            pass  # Expected
        
        assert loader.call_count == 1
    
    def test_stats_reset(self):
        """Test stats reset"""
        manager = CacheManager()
        
        manager.set("key", "value")
        manager.get("key")
        manager.get("non_existent")
        
        stats_before = manager.get_stats()
        assert stats_before['hits'] > 0 or stats_before['misses'] > 0
        
        manager.reset_stats()
        
        stats_after = manager.get_stats()
        assert stats_after['hits'] == 0
        assert stats_after['misses'] == 0
    
    def test_warm_up(self):
        """Test cache warm-up"""
        manager = CacheManager()
        
        loaders = {
            "key1": Mock(return_value="value1"),
            "key2": Mock(return_value="value2"),
            "key3": Mock(return_value=None),  # Empty value
        }
        
        manager.warm_up(loaders, ttl=600)
        
        # Check that loaders were called
        assert loaders["key1"].call_count == 1
        assert loaders["key2"].call_count == 1
        assert loaders["key3"].call_count == 1
        
        # Check that valid values were cached
        assert manager.get("key1") == "value1"
        assert manager.get("key2") == "value2"
        # key3 with None should not be cached (or cached as empty marker)


class TestCachedDecorator:
    """Tests for cached decorator"""
    
    def test_cached_basic(self):
        """Test basic caching with decorator"""
        call_count = 0
        
        @cached(ttl=60)
        def expensive_operation(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # First call (cache miss)
        result1 = expensive_operation(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call (cache hit)
        result2 = expensive_operation(1, 2)
        assert result2 == 3
        assert call_count == 1  # Should not call again
        
        # Different arguments (cache miss)
        result3 = expensive_operation(2, 3)
        assert result3 == 5
        assert call_count == 2
    
    def test_cached_with_key_prefix(self):
        """Test caching with key prefix"""
        call_count = 0
        
        @cached(ttl=60, key_prefix="test_prefix")
        def prefixed_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # Call function
        result = prefixed_function(5)
        assert result == 10
        assert call_count == 1
        
        # Call again (should be cached)
        result = prefixed_function(5)
        assert result == 10
        assert call_count == 1
    
    def test_cached_with_penetration_protection(self):
        """Test caching with penetration protection"""
        call_count = 0
        
        @cached(ttl=300, use_penetration_protection=True)
        def sometimes_empty(x):
            nonlocal call_count
            call_count += 1
            if x == 0:
                return None  # Empty result
            return f"value_{x}"
        
        # Call with normal value
        result1 = sometimes_empty(1)
        assert result1 == "value_1"
        assert call_count == 1
        
        # Call again (cache hit)
        result2 = sometimes_empty(1)
        assert result2 == "value_1"
        assert call_count == 1
        
        # Call with empty result
        result3 = sometimes_empty(0)
        assert result3 is None
        assert call_count == 2
        
        # Call again with empty result (should use penetration protection)
        result4 = sometimes_empty(0)
        assert result4 is None
        assert call_count == 2  # Should not call again


def test_get_cache_manager_singleton():
    """Test that get_cache_manager returns singleton"""
    from src.cache.manager import get_cache_manager, _cache_manager
    
    # Reset singleton
    global _cache_manager
    _cache_manager = None
    
    # First call should create instance
    manager1 = get_cache_manager()
    assert manager1 is not None
    
    # Second call should return same instance
    manager2 = get_cache_manager()
    assert manager2 is manager1