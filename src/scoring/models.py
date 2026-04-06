"""
评分系统数据模型
用于封装评分函数的参数，减少参数数量
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

SCORE_VERSION = "2.7.18"  # 评分算法版本


@dataclass
class ScoreInput:
    """评分输入参数封装"""

    fund_detail: dict
    risk_metrics: dict
    market_sentiment: str
    market_score: int
    news: list[dict]
    hot_sectors: list[dict]
    commodity_sentiment: str
    fund_manager: dict | None
    fund_type: str
    fund_scale: float
    daily_change: float
    fund_data: dict | None = None
    fund_code: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ScoreInput":
        """从字典创建ScoreInput"""
        return cls(
            fund_detail=data.get("fund_detail", {}),
            risk_metrics=data.get("risk_metrics", {}),
            market_sentiment=data.get("market_sentiment", "neutral"),
            market_score=data.get("market_score", 50),
            news=data.get("news", []),
            hot_sectors=data.get("hot_sectors", []),
            commodity_sentiment=data.get("commodity_sentiment", "neutral"),
            fund_manager=data.get("fund_manager"),
            fund_type=data.get("fund_type", "混合型"),
            fund_scale=data.get("fund_scale", 0.0),
            daily_change=data.get("daily_change", 0.0),
            fund_data=data.get("fund_data"),
            fund_code=data.get("fund_code", ""),
        )


@dataclass
class ScoreAudit:
    """评分审计信息"""

    data_source: str = "unknown"  # api/cache/db
    data_fetched_at: datetime | None = None  # 数据抓取时间
    nav_date: str | None = None  # 净值数据日期
    calculation_version: str = SCORE_VERSION  # 算法版本
    calculation_time: datetime = field(default_factory=datetime.now)  # 计算时间

    def to_dict(self) -> dict:
        return {
            "data_source": self.data_source,
            "data_fetched_at": self.data_fetched_at.isoformat() if self.data_fetched_at else None,
            "nav_date": self.nav_date,
            "calculation_version": self.calculation_version,
            "calculation_time": self.calculation_time.isoformat(),
        }


@dataclass
class ScoreResult:
    """评分结果封装（增强版：含审计追踪信息）"""

    total_score: int
    grade: str
    details: dict
    from_cache: bool = False
    audit: ScoreAudit = field(default_factory=ScoreAudit)

    def to_dict(self) -> dict:
        """转换为字典格式（含审计字段）"""
        return {
            "score": self.total_score,
            "grade": self.grade,
            "details": self.details,
            "from_cache": self.from_cache,
            "audit": self.audit.to_dict(),
        }

    def to_db_dict(self) -> dict:
        """转换为数据库存储格式"""
        d = self.details
        return {
            # 主评分
            "total_score": self.total_score,
            # 8维度分数
            "valuation_score": d.get("valuation", {}).get("score", 0),
            "performance_score": d.get("performance", {}).get("score", 0),
            "risk_score": d.get("risk_control", {}).get("score", 0),
            "momentum_score": d.get("momentum", {}).get("score", 0),
            "sentiment_score": d.get("sentiment", {}).get("score", 0),
            "sector_score": d.get("sector", {}).get("score", 0),
            "manager_score": d.get("manager", {}).get("score", 0),
            "liquidity_score": d.get("liquidity", {}).get("score", 0),
            # 8维度原因
            "valuation_reason": d.get("valuation", {}).get("reason", ""),
            "performance_reason": d.get("performance", {}).get("reason", ""),
            "risk_reason": d.get("risk_control", {}).get("reason", ""),
            "momentum_reason": d.get("momentum", {}).get("reason", ""),
            "sentiment_reason": d.get("sentiment", {}).get("reason", ""),
            "sector_reason": d.get("sector", {}).get("reason", ""),
            "manager_reason": d.get("manager", {}).get("reason", ""),
            "liquidity_reason": d.get("liquidity", {}).get("reason", ""),
            # 审计字段
            "data_source": self.audit.data_source,
            "data_fetched_at": self.audit.data_fetched_at,
            "calculation_version": self.audit.calculation_version,
            # 原始输入快照（可选，降低存储成本可关闭）
            "dimension_inputs": self._extract_inputs(),
        }

    def _extract_inputs(self) -> dict[str, Any]:
        """提取各维度原始输入用于追溯"""
        inputs = {}
        for dim_name, dim_data in self.details.items():
            if isinstance(dim_data, dict) and "input" in dim_data:
                inputs[dim_name] = dim_data["input"]
        return inputs
