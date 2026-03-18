"""
统一的评分服务 - 所有评分调用的单一入口（依赖注入版本）
向后兼容的适配器层
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ScoreService:
    """统一的评分服务（兼容性适配器）"""
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        
        # 使用新的依赖注入实现
        from src.interfaces import create_score_service
        self._impl = create_score_service()
    
    def calculate_score(self, fund_code: str, use_cache: bool = True) -> Dict[str, Any]:
        """计算基金评分（兼容旧接口）"""
        try:
            # 调用新的实现
            result = self._impl.calculate_score(fund_code, use_cache)
            
            # 转换为旧格式
            return {
                "total_score": result.total_score,
                "breakdown": result.breakdown,
                "grade": result.grade,
                "details": result.details,
                "fund_code": fund_code,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"计算评分失败: {fund_code}, {e}")
            return {
                "total_score": 0.0,
                "breakdown": {},
                "grade": "E",
                "details": {"error": str(e)},
                "fund_code": fund_code,
                "timestamp": datetime.now().isoformat()
            }
    
    def batch_calculate_scores(self, fund_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量计算评分（兼容旧接口）"""
        try:
            # 调用新的实现
            results = self._impl.batch_calculate_scores(fund_codes)
            
            # 转换为旧格式
            formatted_results = {}
            for code, result in results.items():
                formatted_results[code] = {
                    "total_score": result.total_score,
                    "breakdown": result.breakdown,
                    "grade": result.grade,
                    "details": result.details,
                    "fund_code": code,
                    "timestamp": datetime.now().isoformat()
                }
            
            return formatted_results
        except Exception as e:
            logger.error(f"批量计算评分失败: {e}")
            return {}


# 单例模式（保持向后兼容）
_score_service_instance = None


def get_score_service() -> ScoreService:
    """获取评分服务实例（单例模式）"""
    global _score_service_instance
    if _score_service_instance is None:
        _score_service_instance = ScoreService(cache_enabled=True)
        logger.info("评分服务初始化完成（依赖注入版本）")
    return _score_service_instance


# 测试函数
def test_score_service():
    """测试评分服务"""
    try:
        service = get_score_service()
        result = service.calculate_score("000001")
        print(f"✅ 评分服务测试成功: {result.get('total_score', 0)}分")
        return True
    except Exception as e:
        print(f"❌ 评分服务测试失败: {e}")
        return False


if __name__ == "__main__":
    test_score_service()