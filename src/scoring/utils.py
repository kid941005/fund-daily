"""
评分系统工具函数
"""

import logging
from typing import Optional, Dict, Tuple, List, Any

logger = logging.getLogger(__name__)


def normalize_returns(fund_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化收益率字段
    
    将API返回的字段映射到评分系统需要的字段
    解决字段名不一致问题
    """
    result = fund_data.copy()
    
    # 收益率字段映射
    field_mappings = {
        'syl_1n': 'return_1y',   # 近1年
        'syl_6y': 'return_6m',   # 近6月
        'syl_3y': 'return_3y',   # 近3年
        'syl_1y': 'return_1m',   # 近1月
    }
    
    for old_field, new_field in field_mappings.items():
        if old_field in result and new_field not in result:
            result[new_field] = result[old_field]
    
    # 确保return_3m有值
    if 'return_3m' not in result or result['return_3m'] is None:
        result['return_3m'] = 0
    
    return result


# 缓存相关函数
try:
    from ..fetcher import get_cache, set_cache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    logger.warning("Fetcher not available, scoring cache disabled")


def get_cache_key(fund_code: str, cache_prefix: str) -> str:
    """生成缓存key"""
    return f"{cache_prefix}{fund_code}"


def get_cached_score(fund_code: str, cache_prefix: str) -> Optional[Dict]:
    """获取缓存的评分"""
    if not HAS_CACHE:
        return None
    try:
        return get_cache(get_cache_key(fund_code, cache_prefix))
    except Exception as e:
        logger.warning(f"获取缓存失败: {e}")
        return None


def set_cached_score(fund_code: str, score: Dict, cache_prefix: str, ttl: int) -> None:
    """设置评分缓存"""
    if not HAS_CACHE:
        return
    try:
        set_cache(get_cache_key(fund_code, cache_prefix), score, ttl=ttl)
    except Exception as e:
        logger.warning(f"设置缓存失败: {e}")


def get_grade(score: int) -> str:
    """
    根据分数获取等级
    
    Args:
        score: 分数 (0-100)
        
    Returns:
        等级: A+(95-100), A(90-94), B+(85-89), B(80-84), 
              C+(75-79), C(70-74), D+(65-69), D(60-64), F(0-59)
    """
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "B+"
    elif score >= 80:
        return "B"
    elif score >= 75:
        return "C+"
    elif score >= 70:
        return "C"
    elif score >= 65:
        return "D+"
    elif score >= 60:
        return "D"
    else:
        return "F"