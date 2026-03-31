"""
评分系统数据模型
用于封装评分函数的参数，减少参数数量
"""

from dataclasses import dataclass


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
class ScoreResult:
    """评分结果封装"""

    total_score: int
    grade: str
    details: dict
    from_cache: bool = False

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {"score": self.total_score, "grade": self.grade, "details": self.details, "from_cache": self.from_cache}
