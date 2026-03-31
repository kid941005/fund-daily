"""Quant-related business logic encapsulation and guarantees."""

import logging

from db import database_pg as db
from src.quant import (
    calculate_rebalancing,
    get_dynamic_weights,
    get_timing_signals,
    optimize_portfolio,
)
from src.services.fund_service import FundService, get_fund_service

logger = logging.getLogger(__name__)


class QuantServiceError(Exception):
    """Business-level exceptions raised by QuantService."""

    def __init__(self, message: str, http_status: int = 400):
        super().__init__(message)
        self.http_status = http_status


class QuantService:
    """Encapsulates quant-related domain logic and keeps controllers thin."""

    def __init__(self, fund_service: FundService | None = None):
        self.fund_service = fund_service or get_fund_service(cache_enabled=True)
        # Request-level cache for holdings advice to ensure consistent scores
        self._holdings_advice_cache: dict | None = None
        self._holdings_advice_user_id: str | None = None

    def _get_holdings_advice(self, holdings: list[dict], user_id: str | None) -> dict:
        """Get cached holdings advice or compute it. Ensures consistent scores within a request."""
        # Check if cached for the same user
        if self._holdings_advice_cache is not None and self._holdings_advice_user_id == user_id:
            logger.debug("Using cached holdings advice")
            return self._holdings_advice_cache

        # Compute fresh advice
        advice = self.fund_service.calculate_holdings_advice(holdings)

        # Cache it
        self._holdings_advice_cache = advice
        self._holdings_advice_user_id = user_id

        return advice

    def _fetch_user_holdings(self, user_id: str | None) -> list[dict]:
        if not user_id:
            return []
        holdings = db.get_holdings(user_id)
        filtered = [h for h in holdings if h.get("amount", 0) > 0]
        logger.debug("Fetched %d holdings for user %s", len(filtered), user_id)
        return filtered

    def _fetch_all_holdings(self) -> list[dict]:
        holdings: list[dict] = []
        try:
            with db.get_db() as conn:
                with db.get_cursor(conn) as cursor:
                    # 关联 funds 表获取基金名称
                    cursor.execute("""
                        SELECT h.fund_code, COALESCE(f.fund_name, CONCAT('基金', h.fund_code)) as fund_name,
                               h.amount
                        FROM holdings h
                        LEFT JOIN funds f ON h.fund_code = f.fund_code
                        WHERE h.amount > 0
                    """)
                    for row in cursor.fetchall():
                        holdings.append(
                            {
                                "code": row["fund_code"],
                                "name": row["fund_name"] or f"基金{row['fund_code']}",
                                "fund_name": row["fund_name"] or f"基金{row['fund_code']}",
                                "amount": float(row["amount"]),
                            }
                        )
        except Exception as exc:
            logger.exception("Failed to fetch all holdings")
            raise QuantServiceError("内部错误：持仓数据加载失败", http_status=500) from exc

        logger.debug("Fetched %d global holdings", len(holdings))
        return holdings

    def _require_holdings(self, holdings: list[dict]) -> None:
        if not holdings:
            raise QuantServiceError("暂无持仓数据，无法继续操作", http_status=400)

    def timing_signals(self, fund_codes: list[str] | None = None) -> dict:
        logger.debug("Generating timing signals for %s", fund_codes)
        return get_timing_signals(fund_codes or [])

    def optimize_portfolio(self, user_id: str | None) -> dict:
        holdings = self._fetch_user_holdings(user_id)
        self._require_holdings(holdings)

        advice = self._get_holdings_advice(holdings, user_id)
        funds = advice.get("funds", [])
        if len(funds) < 2:
            raise QuantServiceError("持仓基金不足，无法进行组合优化", http_status=400)

        logger.debug("Optimizing portfolio for user %s with %d funds", user_id, len(funds))
        return optimize_portfolio(funds)

    def rebalancing(self, user_id: str | None) -> dict:
        holdings = self._fetch_user_holdings(user_id)
        if not holdings and not user_id:
            holdings = self._fetch_all_holdings()
        self._require_holdings(holdings)

        advice = self._get_holdings_advice(holdings, user_id)
        funds = advice.get("funds") or []
        if not funds:
            funds = [
                {
                    "fund_code": h.get("code"),
                    "fund_name": h.get("name", f"基金{h.get('code')}"),
                    "amount": h.get("amount", 0),
                    "score_100": {"total_score": 50},
                }
                for h in holdings
            ]

        total_amount = sum(f.get("amount", 0) for f in funds)
        if total_amount <= 0:
            raise QuantServiceError("持仓金额为0，无法生成调仓建议", http_status=400)

        logger.debug("Generating rebalancing for user %s with total %.2f", user_id, total_amount)
        return calculate_rebalancing(funds, total_amount)

    def dynamic_weights(self) -> dict:
        logger.debug("Calculating dynamic weights")
        return get_dynamic_weights()

    def portfolio_analysis(self, user_id: str | None) -> dict:
        holdings = self._fetch_user_holdings(user_id)
        if not holdings and not user_id:
            holdings = self._fetch_all_holdings()
        self._require_holdings(holdings)

        advice = self._get_holdings_advice(holdings, user_id)
        funds = advice.get("funds", [])
        total_amount = sum(f.get("amount", 0) for f in funds)

        risk_scores = []
        returns_1y = []
        weights = []

        for fund in funds:
            score_data = fund.get("score_100", {})
            risk_scores.append(score_data.get("details", {}).get("risk_control", {}).get("score", 4))

            fund_data = fund.get("fund_data", {})
            returns_1y.append(float(fund_data.get("return_1y", 0) or 0))
            weights.append(fund.get("current_pct", 0))

        weighted_risk = (
            sum(r * w for r, w in zip(risk_scores, weights, strict=False)) / sum(weights)
            if sum(weights) > 0
            else (sum(risk_scores) / len(risk_scores) if risk_scores else 4)
        )
        weighted_return = (
            sum(r * w for r, w in zip(returns_1y, weights, strict=False)) / sum(weights)
            if sum(weights) > 0
            else (sum(returns_1y) / len(returns_1y) if returns_1y else 0)
        )

        if weighted_risk > 6:
            risk_level = "高风险"
        elif weighted_risk > 4:
            risk_level = "中高风险"
        elif weighted_risk > 2:
            risk_level = "中等风险"
        else:
            risk_level = "中低风险"

        fund_count = len(funds)
        if fund_count >= 5:
            diversification = "良好"
        elif fund_count >= 3:
            diversification = "一般"
        else:
            diversification = "需分散"

        analysis = {
            "risk_level": risk_level,
            "risk_score": round(weighted_risk, 1),
            "avg_return_1y": round(weighted_return, 2),
            "fund_count": fund_count,
            "diversification": diversification,
            "total_amount": total_amount,
            "funds": funds,
            "message": "分析完成",
            "advice": advice.get("advice"),
        }

        return analysis


_quant_service_instance: QuantService | None = None


def get_quant_service() -> QuantService:
    global _quant_service_instance
    if _quant_service_instance is None:
        _quant_service_instance = QuantService()
    return _quant_service_instance
