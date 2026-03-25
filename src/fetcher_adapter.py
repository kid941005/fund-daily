"""
Fetcher 适配器
将函数式接口适配为类接口（兼容 IFetcher）
"""

from typing import Dict, Any, Optional, List
from .interfaces import IFetcher, FundData
from .fetcher import (
    fetch_fund_data as _fetch_fund_data,
    fetch_fund_detail as _fetch_fund_detail,
    fetch_fund_manager as _fetch_fund_manager,
    fetch_fund_scale as _fetch_fund_scale,
    fetch_hot_sectors as _fetch_hot_sectors,
    fetch_market_news as _fetch_market_news,
)


class FetcherAdapter(IFetcher):
    """Fetcher 函数模块的适配器"""
    
    def fetch_fund_data(self, code: str) -> Optional[FundData]:
        """获取基金数据"""
        data = _fetch_fund_data(code)
        if not data:
            return None
        return FundData(
            code=data.get('code', code),
            name=data.get('name', ''),
            net_value=float(data.get('nav') or 0),
            daily_change=float(data.get('estimated_change', 0) or 0),
            return_1y=float(data.get('return_1y') or 0),
            return_6m=float(data.get('return_6m') or 0),
            return_3m=float(data.get('return_3m') or 0),
            return_1m=float(data.get('return_1m') or 0),
            risk_level=data.get('risk_level', '未知'),
            manager=data.get('manager', ''),
            scale=float(data.get('scale') or 0),
            raw_data=data
        )
    
    def fetch_fund_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """获取基金详情"""
        return _fetch_fund_detail(code)
    
    def fetch_fund_manager(self, code: str) -> Optional[Dict[str, Any]]:
        """获取基金经理信息"""
        return _fetch_fund_manager(code)
    
    def fetch_fund_scale(self, code: str) -> Optional[float]:
        """获取基金规模"""
        return _fetch_fund_scale(code)
    
    def fetch_hot_sectors(self) -> List[Dict[str, Any]]:
        """获取热门板块"""
        return _fetch_hot_sectors()
    
    def fetch_market_news(self) -> List[Dict[str, Any]]:
        """获取市场新闻"""
        return _fetch_market_news()
