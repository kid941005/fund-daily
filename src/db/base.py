"""
AsyncBase - SQLAlchemy 异步模型基类
声明式基类和通用 Mixin 类
"""

from datetime import datetime, date
from typing import Any, Optional

from sqlalchemy import (
    Column, String, Integer, BigInteger, Numeric, Boolean,
    DateTime, Date, Text, JSON, Index, ForeignKey, func
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
    AsyncAttrs
)


class Base(AsyncAttrs, DeclarativeBase):
    """SQLAlchemy 异步声明式基类"""
    pass


# ==================== Mixin 类 ====================

class TimestampMixin:
    """时间戳 Mixin"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class UserMixin:
    """用户关联 Mixin"""
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


# ==================== 表模型 ====================

class User(Base, TimestampMixin):
    """用户表"""
    __tablename__ = "users"
    
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)


class Holding(Base, UserMixin, TimestampMixin):
    """持仓表"""
    __tablename__ = "holdings"
    __table_args__ = (
        Index("idx_holdings_user_code", "user_id", "code", unique=True),
        Index("idx_holdings_code", "code"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), server_default="")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), server_default="0")
    buy_nav: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    buy_date: Mapped[Optional[date]] = mapped_column(Date)


class Fund(Base, TimestampMixin):
    """基金基本信息表"""
    __tablename__ = "funds"
    __table_args__ = (
        Index("idx_funds_name_trgm", "fund_name", postgresql_using="gin", postgresql_ops={"fund_name": "gin_trgm_ops"}),
        Index("idx_funds_code_trgm", "fund_code", postgresql_using="gin", postgresql_ops={"fund_code": "gin_trgm_ops"}),
        Index("idx_funds_updated_at", "updated_at"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    fund_name: Mapped[str] = mapped_column(String(200), nullable=False)
    fund_type: Mapped[Optional[str]] = mapped_column(String(50))
    fund_company: Mapped[Optional[str]] = mapped_column(String(100))
    establish_date: Mapped[Optional[date]] = mapped_column(Date)
    fund_size: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    manager: Mapped[Optional[str]] = mapped_column(String(100))
    risk_level: Mapped[Optional[str]] = mapped_column(String(20))
    rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")


class FundNav(Base):
    """基金净值表"""
    __tablename__ = "fund_nav"
    __table_args__ = (
        Index("idx_fund_nav_code_date", "fund_code", "nav_date", unique=True),
        Index("idx_fund_nav_date", "nav_date"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("funds.fund_code", ondelete="CASCADE"), nullable=False
    )
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    net_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    accumulated_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    daily_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    weekly_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    monthly_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    quarterly_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    yearly_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FundScore(Base):
    """基金评分表"""
    __tablename__ = "fund_scores"
    __table_args__ = (
        Index("idx_fund_scores_code_date", "fund_code", "score_date", unique=True),
        Index("idx_fund_scores_date", "score_date"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("funds.fund_code", ondelete="CASCADE"), nullable=False
    )
    score_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_score: Mapped[Optional[int]] = mapped_column(Integer)
    valuation_score: Mapped[Optional[int]] = mapped_column(Integer)
    sector_score: Mapped[Optional[int]] = mapped_column(Integer)
    risk_score: Mapped[Optional[int]] = mapped_column(Integer)
    valuation_reason: Mapped[Optional[str]] = mapped_column(Text)
    sector_reason: Mapped[Optional[str]] = mapped_column(Text)
    risk_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Config(Base):
    """用户配置表"""
    __tablename__ = "config"
    
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Watchlist(Base, UserMixin):
    """监控列表表"""
    __tablename__ = "watchlist"
    __table_args__ = (
        Index("idx_watchlist_user_code", "user_id", "code", unique=True),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class History(Base, UserMixin):
    """历史记录表"""
    __tablename__ = "history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ==================== 异步引擎和会话工厂 ====================

_async_engine = None
_async_session_factory = None


def create_async_engine_from_url(
    url: str,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    **kwargs
):
    """创建异步引擎（PostgreSQL 使用 postgresql+asyncpg://）"""
    global _async_engine, _async_session_factory
    
    _async_engine = create_async_engine(
        url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        **kwargs
    )
    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return _async_engine


def get_async_session_factory() -> async_sessionmaker:
    """获取异步会话工厂"""
    if _async_session_factory is None:
        raise RuntimeError("Async engine not initialized. Call create_async_engine_from_url first.")
    return _async_session_factory


def get_async_session() -> AsyncSession:
    """获取新的异步会话（需配合 async with 使用）"""
    return get_async_session_factory()()


__all__ = [
    "Base",
    "TimestampMixin",
    "UserMixin",
    "User",
    "Holding",
    "Fund",
    "FundNav",
    "FundScore",
    "Config",
    "Watchlist",
    "History",
    "create_async_engine_from_url",
    "get_async_session_factory",
    "get_async_session",
]
