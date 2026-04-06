"""
数据健康度指标模块
评估基金数据的时效性和可用性
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataHealthIndicator:
    """数据健康度指标"""

    fund_code: str
    nav_updated_at: datetime | None  # 净值数据最后更新时间
    score_updated_at: datetime | None  # 评分数据最后更新时间
    nav_freshness: int  # 净值数据新鲜度 0-100
    score_freshness: int  # 评分数据新鲜度 0-100
    overall_score: int  # 综合健康度 0-100
    is_stale: bool  # 数据是否过时
    stale_reason: str | None  # 过时原因
    market_day: bool  # 当前是否为交易日

    def to_dict(self) -> dict:
        return {
            "fund_code": self.fund_code,
            "nav_updated_at": self.nav_updated_at.isoformat() if self.nav_updated_at else None,
            "score_updated_at": self.score_updated_at.isoformat() if self.score_updated_at else None,
            "nav_freshness": self.nav_freshness,
            "score_freshness": self.score_freshness,
            "overall_score": self.overall_score,
            "is_stale": self.is_stale,
            "stale_reason": self.stale_reason,
            "freshness_label": self._get_freshness_label(),
        }

    def _get_freshness_label(self) -> str:
        """获取新鲜度标签"""
        if self.overall_score >= 90:
            return "🟢 优秀"
        elif self.overall_score >= 70:
            return "🟡 良好"
        elif self.overall_score >= 50:
            return "🟠 一般"
        else:
            return "🔴 较差"


def calculate_nav_freshness(nav_updated_at: datetime | None, market_day: bool = False) -> tuple[int, str | None]:
    """
    计算净值数据新鲜度

    Args:
        nav_updated_at: 净值数据最后更新时间
        market_day: 当前是否为交易日

    Returns:
        (freshness_score, stale_reason)
    """
    if nav_updated_at is None:
        return 0, "净值数据缺失"

    now = datetime.now()
    age = now - nav_updated_at
    age_hours = age.total_seconds() / 3600

    if market_day:
        # 交易日判断标准
        if age_hours < 2:
            return 100, None  # 2小时内，数据很新鲜
        elif age_hours < 4:
            # 盘中，数据较新
            market_open = nav_updated_at.replace(hour=9, minute=30, second=0, microsecond=0)
            if now.hour >= 15:
                return 80, None  # 收盘后正常
            return 90, None
        elif age_hours < 12:
            return 60, None  # 半天内，可接受
        elif age_hours < 24:
            return 40, None  # 1天内，数据偏旧
        elif age_hours < 48:
            return 20, f"净值数据超过{int(age_hours)}小时未更新"
        else:
            return 0, f"净值数据超过{int(age_hours)}小时未更新"
    else:
        # 非交易日（周末/节假日）
        if age_hours < 24:
            return 100, None  # 24小时内正常
        elif age_hours < 48:
            return 80, None  # 周末正常
        elif age_hours < 72:
            return 60, None  # 偏旧但可接受
        elif age_hours < 120:
            return 30, f"净值数据超过{int(age_hours)}小时未更新"
        else:
            return 0, f"净值数据超过{int(age_hours)}小时未更新"


def calculate_score_freshness(score_updated_at: datetime | None, market_day: bool = False) -> tuple[int, str | None]:
    """
    计算评分数据新鲜度

    Args:
        score_updated_at: 评分数据最后更新时间
        market_day: 当前是否为交易日

    Returns:
        (freshness_score, stale_reason)
    """
    if score_updated_at is None:
        return 0, "评分数据缺失"

    now = datetime.now()
    age = now - score_updated_at
    age_hours = age.total_seconds() / 3600

    if market_day:
        # 交易日判断标准
        if age_hours < 2:
            return 100, None  # 2小时内，数据很新鲜
        elif age_hours < 4:
            return 95, None  # 盘中正常
        elif age_hours < 8:
            return 80, None  # 半天内
        elif age_hours < 12:
            return 60, None  # 半天以上
        elif age_hours < 24:
            return 40, None  # 1天内，可接受
        elif age_hours < 48:
            return 20, f"评分数据超过{int(age_hours)}小时未更新"
        else:
            return 0, f"评分数据超过{int(age_hours)}小时未更新"
    else:
        # 非交易日
        if age_hours < 24:
            return 100, None
        elif age_hours < 48:
            return 90, None
        elif age_hours < 72:
            return 70, None
        elif age_hours < 120:
            return 40, f"评分数据超过{int(age_hours)}小时未更新"
        else:
            return 0, f"评分数据超过{int(age_hours)}小时未更新"


def is_market_day() -> bool:
    """判断今天是否为交易日（简单判断，不考虑节假日）"""
    now = datetime.now()
    # 周末
    if now.weekday() >= 5:
        return False
    # 工作日 9:00-15:00 视为交易日
    if 9 <= now.hour < 15:
        return True
    # 收盘后2小时内也算当日交易日
    if now.hour >= 15 and now.hour < 17:
        return True
    return False


def calculate_data_health(
    fund_code: str,
    nav_updated_at: datetime | None = None,
    score_updated_at: datetime | None = None,
    nav_date: str | None = None,
    stale_threshold_hours: int = 24,
) -> DataHealthIndicator:
    """
    计算基金数据健康度

    Args:
        fund_code: 基金代码
        nav_updated_at: 净值数据最后更新时间
        score_updated_at: 评分数据最后更新时间
        nav_date: 净值日期（可选，用于交叉验证）
        stale_threshold_hours: 过时阈值小时数，默认24小时

    Returns:
        DataHealthIndicator 数据健康度指标
    """
    market_day = is_market_day()

    # 计算各维度新鲜度
    nav_freshness, nav_stale_reason = calculate_nav_freshness(nav_updated_at, market_day)
    score_freshness, score_stale_reason = calculate_score_freshness(score_updated_at, market_day)

    # 综合评分（净值权重 40%，评分权重 60%）
    overall_score = int(nav_freshness * 0.4 + score_freshness * 0.6)

    # 判断是否过时
    is_stale = overall_score < 50 or nav_freshness == 0 or score_freshness == 0

    # 生成过时原因
    stale_reason = nav_stale_reason or score_stale_reason
    if is_stale and not stale_reason:
        if overall_score < 50:
            stale_reason = f"综合数据健康度较低({overall_score}分)"
        elif nav_freshness == 0:
            stale_reason = "净值数据完全缺失"
        elif score_freshness == 0:
            stale_reason = "评分数据完全缺失"

    return DataHealthIndicator(
        fund_code=fund_code,
        nav_updated_at=nav_updated_at,
        score_updated_at=score_updated_at,
        nav_freshness=nav_freshness,
        score_freshness=score_freshness,
        overall_score=overall_score,
        is_stale=is_stale,
        stale_reason=stale_reason,
        market_day=market_day,
    )


def get_health_alert_level(freshness: int, is_stale: bool, market_day: bool) -> str:
    """
    根据新鲜度和是否过时返回告警级别

    Args:
        freshness: 新鲜度评分 (0-100)
        is_stale: 是否过时
        market_day: 是否为交易日

    Returns:
        告警级别: none / info / warning / critical
    """
    if is_stale:
        return "critical"

    if not market_day:
        # 非交易日标准更宽松
        if freshness < 50:
            return "warning"
        elif freshness < 70:
            return "info"
        return "none"
    else:
        # 交易日更严格
        if freshness < 60:
            return "warning"
        elif freshness < 80:
            return "info"
        return "none"


def generate_health_report(health_indicators: list[DataHealthIndicator]) -> dict:
    """
    生成健康度报告，包含告警信息

    Args:
        health_indicators: 健康度指标列表

    Returns:
        健康度报告字典
    """
    critical_alerts = []
    warning_alerts = []
    info_alerts = []

    for health in health_indicators:
        alert_level = get_health_alert_level(health.overall_score, health.is_stale, health.market_day)

        alert_entry = {
            "fund_code": health.fund_code,
            "overall_score": health.overall_score,
            "freshness_label": health.to_dict()["freshness_label"],
            "is_stale": health.is_stale,
            "stale_reason": health.stale_reason,
            "alert_level": alert_level,
        }

        if alert_level == "critical":
            critical_alerts.append(alert_entry)
        elif alert_level == "warning":
            warning_alerts.append(alert_entry)
        elif alert_level == "info":
            info_alerts.append(alert_entry)

    return {
        "total_funds": len(health_indicators),
        "critical_count": len(critical_alerts),
        "warning_count": len(warning_alerts),
        "info_count": len(info_alerts),
        "healthy_count": len(health_indicators) - len(critical_alerts) - len(warning_alerts) - len(info_alerts),
        "market_day": health_indicators[0].market_day if health_indicators else False,
        "alerts": {
            "critical": critical_alerts,
            "warning": warning_alerts,
            "info": info_alerts,
        },
        "has_alerts": len(critical_alerts) + len(warning_alerts) + len(info_alerts) > 0,
    }
