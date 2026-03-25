"""
评分器实现
适配现有scoring模块到接口
"""

import logging
from typing import Dict, Any, Union
from .interfaces import IScorer, FundData, MarketData, ScoreResult
from .scoring import calculate_total_score
from .scoring.utils import normalize_returns as original_normalize_returns

logger = logging.getLogger(__name__)


class ScorerImpl(IScorer):
    """评分器实现类"""
    
    def calculate_score(self, fund_data: Union[FundData, Dict], market_data: MarketData) -> ScoreResult:
        """计算基金评分"""
        try:
            # 兼容 dict 和 FundData 对象
            if isinstance(fund_data, dict):
                fund_code = fund_data.get('fundcode') or fund_data.get('fund_code') or fund_data.get('code', '')
                fund_name = fund_data.get('name', '')
                daily_change = float(fund_data.get('gszzl') or fund_data.get('daily_change') or 0)
                raw_data = fund_data
            else:
                fund_code = fund_data.code
                fund_name = getattr(fund_data, 'name', '')
                daily_change = getattr(fund_data, 'daily_change', 0.0)
                raw_data = getattr(fund_data, 'raw_data', {})
            
            # 需要获取基金详情数据（因为calculate_total_score需要fund_detail）
            from .fetcher import fetch_fund_detail
            fund_detail = fetch_fund_detail(fund_code)
            
            if not fund_detail:
                logger.warning(f"无法获取基金详情: {fund_code}")
                fund_detail = {
                    "code": fund_code,
                    "name": fund_name,
                }
            
            # 准备评分输入数据
            # 注意：calculate_total_score需要完整的参数列表
            # 合并 fund_detail 和 fund_data，确保评分函数能获取到收益率数据
            # 优先使用 raw_data 中的收益率数据（来自 fetch_fund_data 的 _fetch_fund_returns）
            # 只有当 raw_data 中没有时，才尝试从 fund_detail 获取
            merged_fund_data = dict(raw_data) if raw_data else {}
            if fund_detail:
                # 只在 raw_data 没有数据时才从 fund_detail 补充（且值不为 None）
                if merged_fund_data.get('return_1y') is None and fund_detail.get('syl_1n') is not None:
                    merged_fund_data['return_1y'] = fund_detail.get('syl_1n')
                if merged_fund_data.get('return_3m') is None and fund_detail.get('syl_3y') is not None:
                    merged_fund_data['return_3m'] = fund_detail.get('syl_3y')
                if merged_fund_data.get('return_1m') is None and fund_detail.get('syl_1y') is not None:
                    merged_fund_data['return_1m'] = fund_detail.get('syl_1y')
                if merged_fund_data.get('return_6m') is None and fund_detail.get('syl_6y') is not None:
                    merged_fund_data['return_6m'] = fund_detail.get('syl_6y')
            
            raw_result = calculate_total_score(
                fund_detail=fund_detail,
                risk_metrics={"volatility": 0.0, "max_drawdown": 0.0, "sharpe_ratio": 0.0},
                market_sentiment=market_data.sentiment,
                market_score=market_data.score,
                news=market_data.news,
                hot_sectors=market_data.hot_sectors,
                commodity_sentiment=market_data.commodity_sentiment,
                fund_manager={},  # 需要获取基金经理信息
                fund_type="stock",  # 默认为股票型基金
                fund_scale=10.0,  # 默认10亿
                daily_change=daily_change,
                fund_data=merged_fund_data,
                fund_code=fund_code  # 用于缓存
            )
            
            # 转换为ScoreResult
            return ScoreResult(
                total_score=raw_result.get("total_score", 0.0),
                breakdown=raw_result.get("breakdown", {}),
                grade=raw_result.get("grade", "E"),
                details=raw_result
            )
        except Exception as e:
            logger.error(f"计算评分异常: {e}")
            import traceback
            traceback.print_exc()
            return ScoreResult(
                total_score=0.0,
                breakdown={},
                grade="E",
                details={"error": str(e)}
            )
    
    def normalize_returns(self, raw_data: Dict[str, Any]) -> Dict[str, float]:
        """标准化收益率数据"""
        try:
            return original_normalize_returns(raw_data)
        except Exception as e:
            logger.error(f"标准化收益率数据异常: {e}")
            return {
                "return_1y": 0.0,
                "return_6m": 0.0,
                "return_3m": 0.0
            }
