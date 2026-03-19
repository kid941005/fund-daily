"""
基金服务类

提供基金相关的业务逻辑，包括：
1. 基金数据获取与分析
2. 基金评分计算
3. 持仓管理
4. 投资建议生成
"""

import logging
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from src.utils.error_handling import handle_errors, handle_network_errors
from src.fetcher import fetch_fund_data, fetch_fund_detail, fetch_fund_manager, fetch_fund_scale
from src.fetcher import fetch_fund_data_enhanced, fetch_fund_detail_enhanced
from src.advice import analyze_fund, generate_advice
from src.analyzer import get_market_sentiment, get_commodity_sentiment
from src.fetcher import fetch_hot_sectors, fetch_market_news
from src.services.score_service import get_score_service
from src.services.metrics_service import get_metrics_service, timed_metric
from src.cache.manager import get_cache_manager
from src.error import (
    FundServiceError, MarketServiceError, ErrorCode,
    fund_not_found, fund_data_fetch_failed, market_data_fetch_failed,
    cache_operation_failed
)

logger = logging.getLogger(__name__)


class FundService:
    """基金服务"""
    
    def __init__(self, cache_enabled: bool = True):
        """
        初始化基金服务
        
        Args:
            cache_enabled: 是否启用缓存
        """
        self.cache_enabled = cache_enabled
        self.cache_manager = get_cache_manager()
        self.score_service = get_score_service()
        self.metrics_service = get_metrics_service()
        
        # 缓存配置 - 使用统一的常量配置
        from src.constants import CACHE_PREFIXES, CACHE_TTL
        self.cache_prefix = CACHE_PREFIXES.get("fund", "fund_daily:v2:")
        self.market_cache_key = f"{self.cache_prefix}market_data"
        self.market_cache_ttl = CACHE_TTL.get("market_data", 300)  # 5分钟
        
        # 并行工作线程数
        self.max_workers = 4
    
    @timed_metric(metric_type="external_api", name="get_fund_data")
    @handle_errors(default_return={"error": "服务暂时不可用"}, log_level="error")
    def get_fund_data(self, fund_code: str, use_cache: bool = True) -> Dict:
        """
        获取基金数据（带错误处理）
        
        Args:
            fund_code: 基金代码
            use_cache: 是否使用缓存
        
        Returns:
            基金数据字典
        
        Raises:
            FundServiceError: 基金数据获取失败
        """
        try:
            # 尝试从缓存获取
            if use_cache and self.cache_enabled:
                cache_key = f"{self.cache_prefix}fund:{fund_code}"
                cached = self.cache_manager.get(cache_key)
                if cached:
                    logger.debug(f"Using cached data for {fund_code}")
                    # 记录缓存命中
                    self.metrics_service.record_cache_hit("fund_data", hit=True)
                    return cached
                else:
                    # 记录缓存未命中
                    self.metrics_service.record_cache_hit("fund_data", hit=False)
            
            # 优先尝试使用增强版fetcher（如果可用）
            fund_data = None
            if fetch_fund_data_enhanced is not None:
                try:
                    fund_data = fetch_fund_data_enhanced(fund_code, use_cache=use_cache)
                    logger.debug(f"Using enhanced fetcher for {fund_code}")
                except Exception as e:
                    logger.warning(f"Enhanced fetcher failed for {fund_code}: {e}")
            
            # 如果增强版fetcher不可用或失败，回退到原始fetcher
            if fund_data is None or fund_data.get("error"):
                fund_data = fetch_fund_data(fund_code)
            
            if not fund_data or fund_data.get("error"):
                raise fund_not_found(fund_code)
            
            # 分析基金
            analyzed = analyze_fund(fund_data)
            if not analyzed:
                raise fund_data_fetch_failed(fund_code)
            
            # 设置缓存
            if use_cache and self.cache_enabled:
                try:
                    self.cache_manager.set(cache_key, analyzed, ttl=600)  # 10分钟
                except Exception as e:
                    logger.warning(f"Failed to cache fund data: {e}")
            
            return analyzed
            
        except FundServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to get fund data for {fund_code}: {e}")
            raise fund_data_fetch_failed(fund_code, e)
    
    @timed_metric(metric_type="external_api", name="get_fund_score")
    def get_fund_score(self, fund_code: str, use_cache: bool = True) -> Dict:
        """
        获取基金评分（使用统一评分服务）
        
        Args:
            fund_code: 基金代码
            use_cache: 是否使用缓存
        
        Returns:
            评分结果字典
        """
        try:
            return self.score_service.calculate_score(fund_code, use_cache)
        except Exception as e:
            logger.error(f"Failed to calculate score for {fund_code}: {e}")
            # 返回降级结果
            return {
                "total_score": 0,
                "base_score": 0,
                "ranking_bonus": 0,
                "grade": "D",
                "error": str(e),
                "calculated_at": datetime.now().isoformat()
            }
    
    @timed_metric(metric_type="external_api", name="get_multiple_fund_scores")
    def get_multiple_fund_scores(self, fund_codes: List[str], use_cache: bool = True) -> Dict[str, Dict]:
        """
        批量获取基金评分（并行）
        
        Args:
            fund_codes: 基金代码列表
            use_cache: 是否使用缓存
        
        Returns:
            基金代码到评分结果的映射
        """
        if not fund_codes:
            return {}
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(len(fund_codes), self.max_workers)) as executor:
            # 提交所有任务
            future_to_code = {
                executor.submit(self.get_fund_score, code, use_cache): code
                for code in fund_codes
            }
            
            # 收集结果
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    results[code] = future.result()
                except Exception as e:
                    logger.error(f"Failed to get score for {code}: {e}")
                    results[code] = {
                        "total_score": 0,
                        "base_score": 0,
                        "ranking_bonus": 0,
                        "grade": "D",
                        "error": str(e),
                        "calculated_at": datetime.now().isoformat()
                    }
        
        return results
    
    @timed_metric(metric_type="external_api", name="get_market_data")
    @handle_errors(default_return={"market_sentiment": "平稳", "market_score": 0, "commodity_sentiment": "平稳", "commodity_score": 0, "hot_sectors": [], "market_news": [], "error": True}, log_level="error")
    def get_market_data(self, use_cache: bool = True) -> Dict:
        """
        获取市场数据（情绪、商品、热点板块等）
        
        Args:
            use_cache: 是否使用缓存
        
        Returns:
            市场数据字典
        """
        try:
            # 导入市场服务（避免循环导入）
            from src.services.market_service import get_market_service
            
            # 获取市场服务实例
            market_service = get_market_service(cache_enabled=self.cache_enabled and use_cache)
            
            # 获取完整市场数据
            market_data = market_service.get_full_market_data(use_cache=use_cache)
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            # 返回降级数据，不抛出异常，避免影响主流程
            return {
                "market_sentiment": "平稳",
                "market_score": 0,
                "commodity_sentiment": "平稳",
                "commodity_score": 0,
                "hot_sectors": [],
                "market_news": [],
                "fetched_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    @timed_metric(metric_type="external_api", name="calculate_holdings_advice")
    @handle_errors(default_return={"funds": [], "advice": {"advice": "服务暂时不可用", "action": "观望", "risk_level": "中等风险"}, "error": True}, log_level="error")
    def calculate_holdings_advice(self, holdings: List[Dict]) -> Dict:
        """
        计算持仓投资建议
        
        Args:
            holdings: 持仓列表，每个持仓包含 code, amount
            
        Returns:
            投资建议字典
        """
        if not holdings:
            return {
                "funds": [],
                "advice": generate_advice([]),
                "message": "暂无持仓"
            }
        
        try:
            # 提取基金代码
            fund_codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
            if not fund_codes:
                return {
                    "funds": [],
                    "advice": generate_advice([]),
                    "message": "暂无有效持仓"
                }
            
            # 获取基金数据
            funds_data = []
            for code in fund_codes:
                try:
                    fund_data = self.get_fund_data(code, use_cache=True)
                    # 获取持仓信息
                    holding = next((h for h in holdings if h["code"] == code), {})
                    fund_data["amount"] = holding.get("amount", 0)
                    funds_data.append(fund_data)
                except Exception as e:
                    logger.warning(f"Failed to get data for fund {code}: {e}")
            
            if not funds_data:
                return {
                    "funds": [],
                    "advice": generate_advice([]),
                    "message": "无法获取持仓基金数据"
                }
            
            # 批量获取评分
            scores = self.get_multiple_fund_scores(
                [f.get("fund_code", "") for f in funds_data],
                use_cache=True
            )
            
            # 合并评分数据
            for fund in funds_data:
                code = fund.get("fund_code", "")
                if code in scores:
                    fund["score_100"] = scores[code]
            
            # 计算持仓比例
            total_amount = sum(f.get("amount", 0) for f in funds_data)
            for fund in funds_data:
                amount = fund.get("amount", 0)
                fund["current_pct"] = round(amount / total_amount * 100, 1) if total_amount > 0 else 0
            
            # 计算目标持仓比例（去弱留强策略）
            if funds_data and total_amount > 0:
                # 获取每只基金的总分
                scored_funds = []
                for fund in funds_data:
                    score_data = fund.get("score_100", {})
                    total_score = score_data.get("total_score", 0)
                    # 使用max(score, 0)避免负分影响计算
                    scored_funds.append((fund, max(total_score, 0)))
                
                total_score = sum(score for _, score in scored_funds)
                
                if total_score > 0:
                    for fund, score in scored_funds:
                        base_ratio = score / total_score
                        
                        # 去弱留强策略
                        if score >= 60:
                            target_ratio = base_ratio * 1.5
                        elif score >= 50:
                            target_ratio = base_ratio * 1.2
                        else:
                            target_ratio = base_ratio * 0.8
                        
                        # 确保比例合理
                        target_ratio = max(0, min(target_ratio, 1.0))
                        fund["target_amount"] = round(total_amount * target_ratio, 2)
                        fund["target_pct"] = round(target_ratio * 100, 1)
                else:
                    # 所有基金评分都为0，平均分配
                    equal_pct = round(100 / len(funds_data), 1) if funds_data else 0
                    for fund in funds_data:
                        fund["target_pct"] = equal_pct
            else:
                for fund in funds_data:
                    fund["target_pct"] = 0
            
            # 应用排名加分（如果需要）
            try:
                from src.scoring import apply_ranking_bonus
                funds_data = apply_ranking_bonus(funds_data)
                logger.debug("Applied ranking bonus to funds")
            except ImportError:
                logger.warning("apply_ranking_bonus not available, skipping")
            except Exception as e:
                logger.warning(f"Failed to apply ranking bonus: {e}")
            
            # 生成投资建议
            advice = generate_advice(funds_data)
            
            return {
                "funds": funds_data,
                "advice": advice,
                "total_amount": total_amount,
                "fetched_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate holdings advice: {e}")
            # 返回降级结果
            return {
                "funds": [],
                "advice": generate_advice([]),
                "error": str(e),
                "message": "投资建议计算失败"
            }


# 全局服务实例
_fund_service_instance = None


def get_fund_service(cache_enabled: bool = True) -> FundService:
    """获取基金服务实例（单例模式）"""
    global _fund_service_instance
    if _fund_service_instance is None:
        _fund_service_instance = FundService(cache_enabled=cache_enabled)
    return _fund_service_instance