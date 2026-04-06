"""
市场时间感知调度模块

根据A股交易时间自动调整抓取频率：
- 开盘前 (09:00-09:30): 预热缓存，准备数据
- 盘中 (09:30-11:30, 13:00-15:00): 较高频率抓取
- 午间休市 (11:30-13:00): 低频率
- 收盘后 (15:00-16:00): 完整数据抓取
- 非交易时间: 低频率维护
"""

from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Callable


class MarketPhase(str, Enum):
    """市场阶段"""

    PRE_OPEN = "pre_open"  # 开盘前 (09:00-09:30)
    MORNING_SESSION = "morning_session"  # 早盘 (09:30-11:30)
    MIDDAY_BREAK = "midday_break"  # 午间休市 (11:30-13:00)
    AFTERNOON_SESSION = "afternoon_session"  # 午盘 (13:00-15:00)
    POST_CLOSE = "post_close"  # 收盘后 (15:00-16:00)
    AFTER_HOURS = "after_hours"  # 盘后 (16:00-09:00)


@dataclass
class MarketSchedule:
    """市场时间表"""

    phase: MarketPhase
    is_trading_hours: bool  # 是否在交易时间
    is_market_open: bool  # 是否开盘中
    minutes_to_next_event: int  # 距离下一个事件（分钟）
    next_event: str  # 下一个事件描述
    current_interval_minutes: int  # 当前建议的抓取间隔


# 交易时间配置
MARKET_OPEN = time(9, 30)  # 开盘时间
MARKET_CLOSE = time(15, 0)  # 收盘时间
PRE_OPEN_START = time(9, 0)  # 预热开始
CLOSE_PROCESS_END = time(16, 0)  # 收盘处理结束


def get_current_phase() -> MarketPhase:
    """获取当前市场阶段"""
    now = datetime.now()
    current_time = now.time()

    if now.weekday() >= 5:
        return MarketPhase.AFTER_HOURS

    if current_time < PRE_OPEN_START:
        return MarketPhase.AFTER_HOURS
    elif current_time < MARKET_OPEN:
        return MarketPhase.PRE_OPEN
    elif current_time < time(11, 30):
        return MarketPhase.MORNING_SESSION
    elif current_time < time(13, 0):
        return MarketPhase.MIDDAY_BREAK
    elif current_time < MARKET_CLOSE:
        return MarketPhase.AFTERNOON_SESSION
    elif current_time < CLOSE_PROCESS_END:
        return MarketPhase.POST_CLOSE
    else:
        return MarketPhase.AFTER_HOURS


def is_trading_day() -> bool:
    """判断今天是否为交易日（简单判断）"""
    now = datetime.now()
    return now.weekday() < 5  # 周一到周五


def is_market_open() -> bool:
    """判断当前是否在交易时间内"""
    phase = get_current_phase()
    return phase in (MarketPhase.MORNING_SESSION, MarketPhase.AFTERNOON_SESSION)


def get_market_schedule() -> MarketSchedule:
    """获取当前市场调度信息"""
    now = datetime.now()
    phase = get_current_phase()

    if now.weekday() >= 5:
        # 周末
        return MarketSchedule(
            phase=phase,
            is_trading_hours=False,
            is_market_open=False,
            minutes_to_next_event=0,
            next_event="周一开盘",
            current_interval_minutes=240,  # 4小时
        )

    current_time = now.time()

    if phase == MarketPhase.PRE_OPEN:
        # 距离开盘
        delta = datetime.combine(now.date(), MARKET_OPEN) - now
        return MarketSchedule(
            phase=phase,
            is_trading_hours=True,
            is_market_open=False,
            minutes_to_next_event=int(delta.total_seconds() / 60),
            next_event="开盘 (09:30)",
            current_interval_minutes=10,  # 每10分钟
        )
    elif phase == MarketPhase.MORNING_SESSION:
        # 距离午休
        delta = datetime.combine(now.date(), time(11, 30)) - now
        return MarketSchedule(
            phase=phase,
            is_trading_hours=True,
            is_market_open=True,
            minutes_to_next_event=int(delta.total_seconds() / 60),
            next_event="午休 (11:30)",
            current_interval_minutes=15,  # 每15分钟
        )
    elif phase == MarketPhase.MIDDAY_BREAK:
        # 距离下午开盘
        delta = datetime.combine(now.date(), time(13, 0)) - now
        return MarketSchedule(
            phase=phase,
            is_trading_hours=True,
            is_market_open=False,
            minutes_to_next_event=int(delta.total_seconds() / 60),
            next_event="下午开盘 (13:00)",
            current_interval_minutes=30,  # 每30分钟
        )
    elif phase == MarketPhase.AFTERNOON_SESSION:
        # 距离收盘
        delta = datetime.combine(now.date(), MARKET_CLOSE) - now
        return MarketSchedule(
            phase=phase,
            is_trading_hours=True,
            is_market_open=True,
            minutes_to_next_event=int(delta.total_seconds() / 60),
            next_event="收盘 (15:00)",
            current_interval_minutes=15,  # 每15分钟
        )
    elif phase == MarketPhase.POST_CLOSE:
        # 收盘处理
        delta = datetime.combine(now.date(), CLOSE_PROCESS_END) - now
        return MarketSchedule(
            phase=phase,
            is_trading_hours=False,
            is_market_open=False,
            minutes_to_next_event=int(delta.total_seconds() / 60),
            next_event="完成收盘处理",
            current_interval_minutes=30,
        )
    else:
        # 盘后等待明日
        # 计算距离明天9点
        tomorrow = now.date()
        if current_time >= CLOSE_PROCESS_END:
            tomorrow = tomorrow
        else:
            tomorrow = (now.replace(hour=9, minute=0, second=0) + timedelta(days=1)).date()

        delta = datetime.combine(tomorrow, PRE_OPEN_START) - now
        return MarketSchedule(
            phase=phase,
            is_trading_hours=False,
            is_market_open=False,
            minutes_to_next_event=int(delta.total_seconds() / 60),
            next_event="明日预热 (09:00)",
            current_interval_minutes=60,  # 每小时
        )


def get_dynamic_interval(base_interval_minutes: int) -> int:
    """
    根据市场阶段动态调整抓取间隔

    Args:
        base_interval_minutes: 基础间隔（分钟）

    Returns:
        调整后的间隔（分钟）
    """
    schedule = get_market_schedule()

    # 非交易日，延长间隔
    if not is_trading_day():
        return base_interval_minutes * 4

    # 根据阶段调整
    multipliers = {
        MarketPhase.PRE_OPEN: 0.5,  # 开盘前更频繁
        MarketPhase.MORNING_SESSION: 0.75,  # 盘中较频繁
        MarketPhase.MIDDAY_BREAK: 2.0,  # 午休降低频率
        MarketPhase.AFTERNOON_SESSION: 0.75,  # 午盘较频繁
        MarketPhase.POST_CLOSE: 1.5,  # 收盘后正常
        MarketPhase.AFTER_HOURS: 4.0,  # 盘后很低频率
    }

    multiplier = multipliers.get(schedule.phase, 1.0)
    interval = int(base_interval_minutes * multiplier)

    # 设置合理的上下限
    return max(5, min(interval, 240))  # 最少5分钟，最多4小时


def should_skip_market_job() -> bool:
    """
    判断是否应该跳过市场相关任务

    Returns:
        True 如果应该跳过（如非交易日的盘中任务）
    """
    phase = get_current_phase()

    # 午休和盘后不应该执行盘中任务
    if phase in (MarketPhase.MIDDAY_BREAK, MarketPhase.POST_CLOSE, MarketPhase.AFTER_HOURS):
        return True
    return False


def get_market_phase_display() -> str:
    """获取市场阶段的友好显示"""
    phase = get_current_phase()

    names = {
        MarketPhase.PRE_OPEN: "📊 预热中",
        MarketPhase.MORNING_SESSION: "🔔 早盘中",
        MarketPhase.MIDDAY_BREAK: "☕ 午间休市",
        MarketPhase.AFTERNOON_SESSION: "🔔 午盘中",
        MarketPhase.POST_CLOSE: "📝 收盘处理",
        MarketPhase.AFTER_HOURS: "🌙 盘后",
    }

    return names.get(phase, "未知")


    """获取市场阶段的友好显示"""
    phase = get_current_phase()

    names = {
        MarketPhase.PRE_OPEN: "📊 预热中",
        MarketPhase.MORNING_SESSION: "🔔 早盘中",
        MarketPhase.MIDDAY_BREAK: "☕ 午间休市",
        MarketPhase.AFTERNOON_SESSION: "🔔 午盘中",
        MarketPhase.POST_CLOSE: "📝 收盘处理",
        MarketPhase.AFTER_HOURS: "🌙 盘后",
    }

    return names.get(phase, "未知")


def get_market_status() -> dict:
    """
    获取市场状态信息

    Returns:
        包含市场状态和调度建议的字典
    """
    schedule = get_market_schedule()
    phase_display = get_market_phase_display()

    return {
        "is_trading_day": is_trading_day(),
        "is_market_open": is_market_open(),
        "phase": schedule.phase.value,
        "phase_display": phase_display,
        "minutes_to_next_event": schedule.minutes_to_next_event,
        "next_event": schedule.next_event,
        "suggested_fetch_interval_minutes": schedule.current_interval_minutes,
        "market_hours": {
            "pre_open": f"{PRE_OPEN_START.strftime('%H:%M')}-{MARKET_OPEN.strftime('%H:%M')}",
            "morning": f"{MARKET_OPEN.strftime('%H:%M')}-11:30",
            "midday_break": "11:30-13:00",
            "afternoon": "13:00-{MARKET_CLOSE.strftime('%H:%M')}",
            "post_close": f"{MARKET_CLOSE.strftime('%H:%M')}-{CLOSE_PROCESS_END.strftime('%H:%M')}",
        },
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def adjust_job_interval(base_interval_minutes: int) -> int:
    """
    根据市场条件调整任务间隔

    这个函数可以在定时任务中调用，以实现动态调整抓取频率

    Args:
        base_interval_minutes: 基础间隔（分钟）

    Returns:
        调整后的间隔（分钟）

    Example:
        # 在任务中动态调整间隔
        interval = adjust_job_interval(30)  # 基础30分钟
        if interval >= 60:
            logger.info(f"当前市场条件不适合执行，跳过")
            return
    """
    return get_dynamic_interval(base_interval_minutes)


def should_run_now() -> tuple[bool, str]:
    """
    判断当前是否应该执行任务

    Returns:
        (should_run, reason)
    """
    schedule = get_market_schedule()

    if not schedule.is_trading_hours:
        return False, f"非交易时间 ({schedule.phase.value})"

    if schedule.phase == MarketPhase.MIDDAY_BREAK:
        return False, "午间休市，降低频率"

    return True, "正常执行"


def get_next_run_strategy(base_minutes: int) -> dict:
    """
    获取下次运行的策略

    Returns:
        包含下次运行时间和间隔的字典
    """
    schedule = get_market_schedule()
    adjusted_interval = get_dynamic_interval(base_minutes)

    from datetime import timedelta

    next_run = datetime.now() + timedelta(minutes=adjusted_interval)

    return {
        "interval_minutes": adjusted_interval,
        "next_run_approx": next_run.strftime("%H:%M"),
        "phase": schedule.phase.value,
        "phase_display": get_market_phase_display(),
        "market_open": schedule.is_market_open,
    }
