"""
分析器实现
适配现有analyzer模块到接口
"""

import logging
from typing import Dict, Any
from .interfaces import IAnalyzer, FundData
from .analyzer import (
    calculate_risk_metrics as original_calculate_risk_metrics,
    get_market_sentiment as original_get_market_sentiment,
    get_commodity_sentiment as original_get_commodity_sentiment,
)

logger = logging.getLogger(__name__)


class AnalyzerImpl(IAnalyzer):
    """分析器实现类"""
    
    def calculate_risk_metrics(self, fund_data: FundData) -> Dict[str, Any]:
        """计算风险指标"""
        try:
            # 使用原始数据计算风险指标
            return original_calculate_risk_metrics(fund_data.raw_data)
        except Exception as e:
            logger.error(f"计算风险指标异常: {fund_data.code}, {e}")
            return {
                "volatility": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "error": str(e)
            }
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪"""
        try:
            return original_get_market_sentiment()
        except Exception as e:
            logger.error(f"获取市场情绪异常: {e}")
            return {
                "sentiment": "neutral",
                "score": 50.0,
                "error": str(e)
            }
    
    def get_commodity_sentiment(self) -> Dict[str, Any]:
        """获取商品情绪"""
        try:
            return original_get_commodity_sentiment()
        except Exception as e:
            logger.error(f"获取商品情绪异常: {e}")
            return {
                "sentiment": "neutral",
                "score": 50.0,
                "error": str(e)
            }