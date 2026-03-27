"""
基金服务类

提供基金相关的业务逻辑，包括：
1. 基金数据获取与分析
2. 基金评分计算
3. 持仓管理
4. 投资建议生成
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

from src.advice import generate_advice
from src.cache.manager import get_cache_manager
from src.fetcher import fetch_fund_data
from src.services.metrics_service import timed_metric
from src.utils.error_handling import handle_errors

logger = logging.getLogger(__name__)

# ============== 辅助函数 ==============


def _fetch_holding_fund(code: str, holding: Dict, get_fund_data_fn) -> Dict:
    """获取单个持仓基金的数据（用于并行批量获取）"""
    try:
        fund_data = get_fund_data_fn(code, use_cache=True)
        fund_data["amount"] = holding.get("amount", 0)
        if not fund_data.get("fund_code"):
            fund_data["fund_code"] = code
        fund_name = fund_data.get("fund_name") or fund_data.get("name")
        if not fund_name:
            fund_data["fund_name"] = holding.get("name", f"基金{code}")
        else:
            fund_data["fund_name"] = fund_name
        return fund_data
    except Exception as e:
        logger.warning(f"Failed to get data for fund {code}: {e}")
        return {
            "fund_code": code,
            "fund_name": holding.get("name", f"基金{code}"),
            "name": holding.get("name", f"基金{code}"),
            "amount": holding.get("amount", 0),
            "nav": 0,
            "estimate_nav": 0,
            "daily_change": 0,
            "error": str(e),
        }


def _batch_fetch_holdings(fund_codes: List[str], holdings: List[Dict], get_fund_data_fn) -> List[Dict]:
    """并行批量获取持仓基金数据"""
    holding_map = {h["code"]: h for h in holdings}
    results = []

    def fetch_one(code: str) -> Dict:
        return _fetch_holding_fund(code, holding_map.get(code, {}), get_fund_data_fn)

    with ThreadPoolExecutor(max_workers=min(len(fund_codes), 4)) as executor:
        futures = {executor.submit(fetch_one, code): code for code in fund_codes}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    return results


def _compute_target_allocations(funds_data: List[Dict], total_amount: float) -> None:
    """计算目标持仓比例（去弱留强策略，修改原列表）"""
    scored_funds = []
    for fund in funds_data:
        score_data = fund.get("score_100", {})
        total_score = max(score_data.get("total_score", 0), 0)
        scored_funds.append((fund, total_score))

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
            target_ratio = max(0, min(target_ratio, 1.0))
            fund["target_amount"] = round(total_amount * target_ratio, 2)
            fund["target_pct"] = round(target_ratio * 100, 1)
    else:
        equal_pct = round(100 / len(funds_data), 1) if funds_data else 0
        for fund in funds_data:
            fund["target_pct"] = equal_pct


# ============== 服务类 ==============


class FundService:
    """基金服务"""

    def __init__(self, cache_enabled: bool = True):
        from src.constants import CACHE_PREFIXES

        self.cache_enabled = cache_enabled
        self.cache_manager = get_cache_manager()
        self.cache_prefix = CACHE_PREFIXES.get("fund", "fund_daily:v2:")
        self.market_cache_key = f"{self.cache_prefix}market_data"
        self.max_workers = 4

    def _fund_cache_key(self, fund_code: str) -> str:
        return f"fund:data:v2:{fund_code}"

    def get_fund_data(self, fund_code: str, use_cache: bool = True) -> Dict:
        """获取基金数据"""
        if use_cache:
            cached = self.cache_manager.get(self._fund_cache_key(fund_code))
            if cached:
                return cached

        data = fetch_fund_data(fund_code, use_cache=False)
        if "error" not in data:
            self.cache_manager.set(self._fund_cache_key(fund_code), data, ttl=600)
        return data

    def get_fund_score(self, fund_code: str, use_cache: bool = True) -> Dict:
        """获取基金评分"""
        try:
            from src.services.score_service import get_score_service

            service = get_score_service()
            return service.calculate_score(fund_code, use_cache=use_cache)
        except Exception as e:
            logger.error(f"Failed to get fund score: {e}")
            return {"error": str(e)}

    def get_multiple_fund_scores(self, fund_codes: List[str], use_cache: bool = True) -> Dict[str, Dict]:
        """批量获取基金评分"""
        results = {}
        for code in fund_codes:
            try:
                results[code] = self.get_fund_score(code, use_cache=use_cache)
            except Exception:
                results[code] = {"error": "获取评分失败"}
        return results

    def get_market_data(self, use_cache: bool = True) -> Dict:
        """获取市场数据"""
        try:
            from src.services.market_service import get_market_service

            market_service = get_market_service(cache_enabled=self.cache_enabled and use_cache)
            return market_service.get_full_market_data(use_cache=use_cache)
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return {
                "market_sentiment": "平稳",
                "market_score": 0,
                "commodity_sentiment": "平稳",
                "commodity_score": 0,
                "hot_sectors": [],
                "market_news": [],
                "fetched_at": datetime.now().isoformat(),
                "error": str(e),
            }

    @timed_metric(metric_type="external_api", name="calculate_holdings_advice")
    @handle_errors(
        default_return={
            "funds": [],
            "advice": {"advice": "服务暂时不可用", "action": "观望", "risk_level": "中等风险"},
            "error": True,
        },
        log_level="error",
    )
    def calculate_holdings_advice(self, holdings: List[Dict]) -> Dict:
        """计算持仓投资建议"""
        if not holdings:
            return {"funds": [], "advice": generate_advice([]), "message": "暂无持仓"}

        # 提取基金代码
        fund_codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
        if not fund_codes:
            return {"funds": [], "advice": generate_advice([]), "message": "暂无有效持仓"}

        # 并行获取基金数据
        funds_data = _batch_fetch_holdings(fund_codes, holdings, self.get_fund_data)
        if not funds_data:
            return {"funds": [], "advice": generate_advice([]), "message": "无法获取持仓基金数据"}

        # 批量获取评分
        scores = self.get_multiple_fund_scores([f.get("fund_code", "") for f in funds_data], use_cache=True)

        # 合并评分
        for fund in funds_data:
            code = fund.get("fund_code", "")
            if code in scores:
                fund["score_100"] = scores[code]

        # 计算持仓比例
        total_amount = sum(f.get("amount", 0) for f in funds_data)
        for fund in funds_data:
            amount = fund.get("amount", 0)
            fund["current_pct"] = round(amount / total_amount * 100, 1) if total_amount > 0 else 0

        # 目标持仓比例（去弱留强）
        if funds_data and total_amount > 0:
            _compute_target_allocations(funds_data, total_amount)

        # 应用排名加分
        try:
            from src.scoring import apply_ranking_bonus

            funds_data = apply_ranking_bonus(funds_data)
        except Exception as e:
            logger.warning(f"Failed to apply ranking bonus: {e}")

        # 生成投资建议
        advice = generate_advice(funds_data)

        return {
            "funds": funds_data,
            "advice": advice,
            "total_amount": total_amount,
            "fetched_at": datetime.now().isoformat(),
        }


_fund_service_instance = None


def get_fund_service(cache_enabled: bool = True) -> FundService:
    """获取基金服务实例（单例模式）"""
    global _fund_service_instance
    if _fund_service_instance is None:
        _fund_service_instance = FundService(cache_enabled=cache_enabled)
    return _fund_service_instance
