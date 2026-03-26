"""
抽象接口定义
使用依赖注入减少耦合，提高可测试性
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FundData:
    """基金数据模型"""

    code: str
    name: str
    net_value: float
    daily_change: float
    return_1y: float
    return_6m: float
    return_3m: float
    return_1m: float  # 近一月收益率
    risk_level: str
    manager: str
    scale: float
    raw_data: Dict[str, Any]


@dataclass
class MarketData:
    """市场数据模型"""

    sentiment: str
    score: float
    commodity_sentiment: str
    hot_sectors: List[Dict[str, Any]]
    news: List[Dict[str, Any]]


@dataclass
class ScoreResult:
    """评分结果模型"""

    total_score: float
    breakdown: Dict[str, float]
    grade: str
    details: Dict[str, Any]


class IFetcher(ABC):
    """数据获取接口"""

    @abstractmethod
    def fetch_fund_data(self, code: str) -> Optional[FundData]:
        """获取基金数据"""
        pass

    @abstractmethod
    def fetch_fund_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """获取基金详情"""
        pass

    @abstractmethod
    def fetch_fund_manager(self, code: str) -> Optional[Dict[str, Any]]:
        """获取基金经理信息"""
        pass

    @abstractmethod
    def fetch_fund_scale(self, code: str) -> Optional[float]:
        """获取基金规模"""
        pass

    @abstractmethod
    def fetch_hot_sectors(self) -> List[Dict[str, Any]]:
        """获取热门板块"""
        pass

    @abstractmethod
    def fetch_market_news(self) -> List[Dict[str, Any]]:
        """获取市场新闻"""
        pass


class IAnalyzer(ABC):
    """数据分析接口"""

    @abstractmethod
    def calculate_risk_metrics(self, fund_data: FundData) -> Dict[str, Any]:
        """计算风险指标"""
        pass

    @abstractmethod
    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪"""
        pass

    @abstractmethod
    def get_commodity_sentiment(self) -> Dict[str, Any]:
        """获取商品情绪"""
        pass


class IScorer(ABC):
    """评分计算接口"""

    @abstractmethod
    def calculate_score(self, fund_data: FundData, market_data: MarketData) -> ScoreResult:
        """计算基金评分"""
        pass

    @abstractmethod
    def normalize_returns(self, raw_data: Dict[str, Any]) -> Dict[str, float]:
        """标准化收益率数据"""
        pass


class ICache(ABC):
    """缓存接口"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass


class IScoreService(ABC):
    """评分服务接口"""

    @abstractmethod
    def calculate_score(self, fund_code: str, use_cache: bool = True) -> ScoreResult:
        """计算基金评分"""
        pass

    @abstractmethod
    def batch_calculate_scores(self, fund_codes: List[str]) -> Dict[str, ScoreResult]:
        """批量计算评分"""
        pass


# 工厂函数
def create_fetcher() -> IFetcher:
    """创建数据获取器实例"""
    from src.fetcher_adapter import FetcherAdapter

    return FetcherAdapter()


def create_analyzer() -> IAnalyzer:
    """创建分析器实例"""
    from src.analyzer_impl import AnalyzerImpl

    return AnalyzerImpl()


def create_scorer() -> IScorer:
    """创建评分器实例"""
    from src.scorer_impl import ScorerImpl

    return ScorerImpl()


def create_cache() -> ICache:
    """创建缓存实例"""
    from src.cache_impl import CacheImpl

    return CacheImpl()


def create_score_service(
    fetcher: Optional[IFetcher] = None,
    analyzer: Optional[IAnalyzer] = None,
    scorer: Optional[IScorer] = None,
    cache: Optional[ICache] = None,
) -> IScoreService:
    """创建评分服务实例"""
    from src.services.score_service_impl import ScoreServiceImpl

    return ScoreServiceImpl(
        fetcher=fetcher or create_fetcher(),
        analyzer=analyzer or create_analyzer(),
        scorer=scorer or create_scorer(),
        cache=cache or create_cache(),
    )
