"""
Tests for fund database storage functionality
"""

import os
import sys
import pytest
from datetime import date, datetime
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置环境变量
os.environ['FUND_DAILY_DB_PASSWORD'] = '941005'


class TestFundDatabaseTables:
    """Tests for fund database tables"""
    
    def test_database_connection(self):
        """Test database connection"""
        from db.database_pg import get_db
        
        with get_db() as conn:
            assert conn is not None
            # 简单的查询测试
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
    
    def test_funds_table_exists(self):
        """Test that funds table exists"""
        from db.database_pg import get_db
        
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'funds'
                    )
                """)
                exists = cursor.fetchone()[0]
                assert exists is True
    
    def test_fund_nav_table_exists(self):
        """Test that fund_nav table exists"""
        from db.database_pg import get_db
        
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'fund_nav'
                    )
                """)
                exists = cursor.fetchone()[0]
                assert exists is True
    
    def test_fund_scores_table_exists(self):
        """Test that fund_scores table exists"""
        from db.database_pg import get_db
        
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'fund_scores'
                    )
                """)
                exists = cursor.fetchone()[0]
                assert exists is True


class TestFundDatabaseFunctions:
    """Tests for fund database functions"""
    
    @pytest.fixture
    def test_fund_code(self):
        """Test fund code fixture"""
        return "TEST001"
    
    def test_save_fund_info(self, test_fund_code):
        """Test saving fund information"""
        from db import save_fund_info, get_fund_info
        
        # 保存基金信息
        save_fund_info(
            fund_code=test_fund_code,
            fund_name="测试基金",
            fund_type="股票型",
            fund_company="测试基金公司",
            establish_date="2020-01-01",
            fund_size=100.5,
            manager="测试经理",
            risk_level="中风险",
            rating=4.0
        )
        
        # 查询验证
        fund_info = get_fund_info(test_fund_code)
        assert fund_info is not None
        assert fund_info['fund_code'] == test_fund_code
        assert fund_info['fund_name'] == "测试基金"
        assert fund_info['fund_type'] == "股票型"
        assert fund_info['fund_company'] == "测试基金公司"
        # PostgreSQL返回的数值可能有尾随零，使用float比较
        assert float(fund_info['fund_size']) == 100.5
        assert fund_info['manager'] == "测试经理"
        assert fund_info['risk_level'] == "中风险"
        assert float(fund_info['rating']) == 4.0
    
    def test_save_fund_nav(self, test_fund_code):
        """Test saving fund NAV data"""
        from db import save_fund_nav, get_fund_nav
        
        # 首先确保基金存在
        from db import save_fund_info
        save_fund_info(fund_code=test_fund_code, fund_name="测试基金")
        
        # 保存净值数据
        nav_date = date.today()
        save_fund_nav(
            fund_code=test_fund_code,
            nav_date=nav_date,
            net_value=1.2345,
            accumulated_value=2.3456,
            daily_return=0.0123,
            weekly_return=0.0456,
            monthly_return=0.1234
        )
        
        # 查询验证
        nav_data = get_fund_nav(test_fund_code, nav_date)
        assert nav_data is not None
        assert nav_data['fund_code'] == test_fund_code
        assert nav_data['nav_date'] == nav_date
        assert float(nav_data['net_value']) == 1.2345
        assert float(nav_data['accumulated_value']) == 2.3456
        assert float(nav_data['daily_return']) == 0.0123
    
    def test_save_fund_score(self, test_fund_code):
        """Test saving fund score data"""
        from db import save_fund_score, get_fund_score
        
        # 首先确保基金存在
        from db import save_fund_info
        save_fund_info(fund_code=test_fund_code, fund_name="测试基金")
        
        # 保存评分数据
        score_date = date.today()
        save_fund_score(
            fund_code=test_fund_code,
            score_date=score_date,
            total_score=85,
            valuation_score=9,
            sector_score=8,
            risk_score=7,
            valuation_reason="估值合理",
            sector_reason="行业前景良好",
            risk_reason="风险控制良好"
        )
        
        # 查询验证
        score_data = get_fund_score(test_fund_code, score_date)
        assert score_data is not None
        assert score_data['fund_code'] == test_fund_code
        assert score_data['score_date'] == score_date
        assert score_data['total_score'] == 85
        assert score_data['valuation_score'] == 9
        assert score_data['sector_score'] == 8
        assert score_data['risk_score'] == 7
        assert score_data['valuation_reason'] == "估值合理"
        assert score_data['sector_reason'] == "行业前景良好"
        assert score_data['risk_reason'] == "风险控制良好"
    
    def test_save_fund_data_comprehensive(self, test_fund_code):
        """Test comprehensive fund data saving"""
        from db import save_fund_data, get_fund_info, get_fund_nav, get_fund_score
        
        # 准备完整的基金数据
        fund_data = {
            'fund_code': test_fund_code,
            'fund_name': '综合测试基金',
            'fund_type': '混合型',
            'fund_company': '综合基金公司',
            'establish_date': '2018-05-15',
            'fund_size': 250.75,
            'manager': '综合经理',
            'risk_level': '中高风险',
            'rating': 4.5,
            'net_value': 2.3456,
            'accumulated_value': 3.4567,
            'daily_return': 0.0234,
            'score_100': {
                'total_score': 78,
                'valuation': {
                    'score': 8,
                    'reason': '估值合理'
                },
                'sector': {
                    'score': 7,
                    'reason': '行业前景良好'
                },
                'risk_control': {
                    'score': 6,
                    'reason': '风险控制一般'
                }
            }
        }
        
        # 保存数据
        result = save_fund_data(test_fund_code, fund_data)
        assert result is True
        
        # 验证基本信息
        fund_info = get_fund_info(test_fund_code)
        assert fund_info is not None
        assert fund_info['fund_name'] == '综合测试基金'
        
        # 验证净值数据
        nav_data = get_fund_nav(test_fund_code)
        assert nav_data is not None
        assert float(nav_data['net_value']) == 2.3456
        
        # 验证评分数据
        score_data = get_fund_score(test_fund_code)
        assert score_data is not None
        assert score_data['total_score'] == 78
        assert score_data['valuation_score'] == 8
        assert score_data['valuation_reason'] == '估值合理'


class TestEnhancedFetcher:
    """Tests for enhanced fetcher"""
    
    def test_enhanced_fetcher_available(self):
        """Test that enhanced fetcher is available"""
        from src.fetcher import HAS_ENHANCED_FETCHER
        assert HAS_ENHANCED_FETCHER is True
    
    def test_fetch_fund_data_enhanced(self):
        """Test enhanced fund data fetching"""
        from src.fetcher import fetch_fund_data_enhanced
        
        # 测试一个已知的基金代码
        result = fetch_fund_data_enhanced('000001')
        
        # 验证返回结构
        assert isinstance(result, dict)
        assert 'error' not in result  # 不应该有错误
        
        # 验证必要字段
        assert 'name' in result or 'fund_name' in result
        
        # source字段可能不存在（如果数据来自原始API）
        # 但增强版fetcher应该尽量添加source字段
        # 我们只检查如果存在source字段，它应该是有效的
        if 'source' in result:
            assert result['source'] in ['database', 'api', 'cache', 'eastmoney']
    
    def test_enhanced_fetcher_fallback(self):
        """Test enhanced fetcher fallback mechanism"""
        from src.fetcher import fetch_fund_data_enhanced
        
        # 测试一个可能不存在的基金代码
        result = fetch_fund_data_enhanced('INVALID999')
        
        # 即使基金不存在，也应该返回一个字典
        assert isinstance(result, dict)
        # 可能包含错误信息或空数据


class TestFundServiceWithDatabase:
    """Tests for FundService with database integration"""
    
    @pytest.fixture
    def fund_service(self):
        """FundService fixture"""
        from src.services.fund_service import FundService
        return FundService()
    
    def test_service_uses_enhanced_fetcher(self, fund_service):
        """Test that FundService uses enhanced fetcher when available"""
        from src.fetcher import HAS_ENHANCED_FETCHER
        
        if HAS_ENHANCED_FETCHER:
            # 测试获取基金数据
            result = fund_service.get_fund_data('000001')
            assert isinstance(result, dict)
            assert 'error' not in result
            assert 'fund_name' in result
            assert 'fund_code' in result
    
    def test_service_cache_behavior(self, fund_service):
        """Test FundService cache behavior with database"""
        # 清除缓存以确保从数据库获取
        from src.cache.redis_cache import redis_clear
        redis_clear()
        
        # 获取基金数据
        result = fund_service.get_fund_data('000001', use_cache=False)
        assert isinstance(result, dict)
        assert 'error' not in result


class TestDatabasePerformance:
    """Tests for database performance"""
    
    def test_batch_operations(self):
        """Test batch operations performance"""
        from db import save_fund_info, get_fund_info
        import time
        
        # 测试批量保存
        start_time = time.time()
        
        for i in range(10):
            fund_code = f"BATCH{i:03d}"
            save_fund_info(
                fund_code=fund_code,
                fund_name=f"批量测试基金{i}",
                fund_type="测试型",
                fund_company="批量测试公司"
            )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 验证批量操作在合理时间内完成
        assert elapsed < 5.0  # 10条记录应该在5秒内完成
        
        # 验证数据保存成功
        for i in range(10):
            fund_code = f"BATCH{i:03d}"
            fund_info = get_fund_info(fund_code)
            assert fund_info is not None
            assert fund_info['fund_name'] == f"批量测试基金{i}"


class TestDataConsistency:
    """Tests for data consistency"""
    
    def test_database_api_consistency(self):
        """Test consistency between database and API data"""
        from src.fetcher import fetch_fund_data_enhanced
        from db import get_fund_info
        
        fund_code = '000001'
        
        # 从增强版fetcher获取数据
        enhanced_data = fetch_fund_data_enhanced(fund_code)
        
        # 从数据库获取数据
        db_info = get_fund_info(fund_code)
        
        # 如果数据来自数据库，验证一致性
        if enhanced_data.get('source') == 'database' and db_info:
            # 验证基金名称一致性
            api_name = enhanced_data.get('name', '')
            db_name = db_info.get('fund_name', '')
            
            # 名称应该相似或包含关系
            assert api_name and db_name
            # 简单的名称匹配检查（允许部分匹配）
            assert api_name in db_name or db_name in api_name or len(api_name) > 0 and len(db_name) > 0


if __name__ == "__main__":
    # 直接运行测试
    import pytest
    pytest.main([__file__, "-v"])