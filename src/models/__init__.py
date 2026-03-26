"""
Data models for Fund Daily
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class FundData:
    """基金基础数据"""

    fund_code: str
    fund_name: str
    nav: Optional[float] = None  # 单位净值
    estimate_nav: Optional[float] = None  # 估算净值
    daily_change: float = 0.0  # 估算涨跌幅
    date: Optional[str] = None  # 净值日期
    estimate_date: Optional[str] = None  # 估算时间

    @property
    def trend(self) -> str:
        if self.daily_change > 0:
            return "up"
        elif self.daily_change < 0:
            return "down"
        return "flat"


@dataclass
class FundDetail:
    """基金详细信息"""

    fund_code: str
    fund_name: str
    nav: Optional[float] = None
    acc_nav: Optional[float] = None
    estimate_nav: Optional[float] = None
    daily_change: Optional[float] = None

    # 收益率
    return_1w: Optional[float] = None
    return_2w: Optional[float] = None
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_6m: Optional[float] = None
    return_1y: Optional[float] = None

    # 费率
    fee_rate: Optional[float] = None
    source_rate: Optional[float] = None

    # 风险指标
    risk_metrics: Optional[Dict] = None


@dataclass
class RiskMetrics:
    """风险指标"""

    risk_level: str = "中等风险"
    risk_score: float = 4.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    estimated_max_drawdown: float = 0.0
    return_ratio: float = 0.0
    suggestion: str = ""


@dataclass
class MarketSentiment:
    """市场情绪"""

    sentiment: str = "平稳"  # 乐观/偏多/平稳/偏空/恐慌
    score: float = 0.0  # -100 to 100
    sector_up: int = 0
    sector_down: int = 0
    sector_total: int = 0
    news_hope: int = 0
    news_fear: int = 0
    commodity_sentiment: str = "平稳"
    commodity_score: float = 0.0
    timestamp: str = ""


@dataclass
class Sector:
    """板块数据"""

    name: str
    change: float
    code: str = ""


@dataclass
class News:
    """新闻数据"""

    title: str
    time: str
    source: str = "东方财富"
    summary: str = ""
    url: str = ""


@dataclass
class Holding:
    """持仓"""

    code: str
    name: str
    amount: float
    buy_nav: Optional[float] = None
    buy_date: Optional[str] = None


@dataclass
class Advice:
    """投资建议"""

    action: str = "持有"  # 买入/持有/减仓/卖出
    advice: str = ""
    risk_level: str = "中等风险"

    # 市场
    market_sentiment: str = "平稳"
    market_score: float = 0.0

    # 基金表现
    up_count: int = 0
    down_count: int = 0
    avg_change: float = 0.0

    # 风险指标
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    risk_score: float = 4.0

    # 大宗商品
    commodity_sentiment: str = "平稳"
    commodity_score: float = 0.0

    # 仓位
    position_ratio: float = 0.0
    avg_profit_pct: float = 0.0
    total_value: float = 0.0


@dataclass
class DailyReport:
    """每日报告"""

    date: str
    funds: List[FundData]
    summary: Dict

    @property
    def up_count(self) -> int:
        return sum(1 for f in self.funds if f.trend == "up")

    @property
    def down_count(self) -> int:
        return sum(1 for f in self.funds if f.trend == "down")

    @property
    def flat_count(self) -> int:
        return sum(1 for f in self.funds if f.trend == "flat")
