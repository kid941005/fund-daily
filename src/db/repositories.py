"""
Repositories - Repository 模式实现
基于 SQLAlchemy 异步 ORM 的数据访问层
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import (
    Base,
    Config,
    Fund,
    FundNav,
    FundScore,
    History,
    Holding,
    User,
    Watchlist,
    get_async_session,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


# ==================== 基础 Repository ====================


class AsyncRepository(Generic[T]):
    """异步 Repository 基类"""

    model: type[Base] = Base

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: Any) -> Optional[T]:
        """根据 ID 获取"""
        stmt = select(self.model).where(self.model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """获取所有记录"""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, **kwargs) -> T:
        """添加记录"""
        instance = self.model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, id: Any, **kwargs) -> int:
        """更新记录"""
        stmt = update(self.model).where(self.model.id == id).values(**kwargs)
        result = await self._session.execute(stmt)
        return result.rowcount

    async def delete(self, id: Any) -> int:
        """删除记录"""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self._session.execute(stmt)
        return result.rowcount

    async def count(self) -> int:
        """计数"""
        stmt = select(func.count()).select_from(self.model)
        result = await self._session.execute(stmt)
        return result.scalar_one()


# ==================== UserRepository ====================


class UserRepository(AsyncRepository[User]):
    """用户 Repository"""

    model = User

    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取"""
        stmt = select(User).where(User.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Optional[User]:
        """根据 user_id 获取"""
        stmt = select(User).where(User.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user_id: str, username: str, password_hash: str) -> User:
        """创建用户"""
        user = User(user_id=user_id, username=username, password=password_hash)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update_password(self, user_id: str, password_hash: str) -> int:
        """更新密码"""
        stmt = update(User).where(User.user_id == user_id).values(password=password_hash, updated_at=datetime.now())
        result = await self._session.execute(stmt)
        return result.rowcount

    async def verify_password(self, username: str, password: str) -> Optional[User]:
        """验证密码"""
        from src.auth import verify_password

        user = await self.get_by_username(username)
        if user and verify_password(password, user.password):
            return user
        return None


# ==================== HoldingsRepository ====================


class HoldingsRepository(AsyncRepository[Holding]):
    """持仓 Repository"""

    model = Holding

    async def get_by_user(self, user_id: str) -> List[Holding]:
        """获取用户持仓"""
        stmt = select(Holding).where(Holding.user_id == user_id).order_by(Holding.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_code(self, user_id: str, code: str) -> Optional[Holding]:
        """根据用户和代码获取持仓"""
        stmt = select(Holding).where(and_(Holding.user_id == user_id, Holding.code == code))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: str,
        code: str,
        name: str = "",
        amount: float = 0,
        buy_nav: Optional[float] = None,
        buy_date: Optional[date] = None,
    ) -> Holding:
        """upsert 持仓"""
        existing = await self.get_by_user_and_code(user_id, code)
        if existing:
            existing.name = name
            existing.amount = amount
            existing.buy_nav = buy_nav
            existing.buy_date = buy_date
            existing.updated_at = datetime.now()
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        else:
            return await self.add(
                user_id=user_id,
                code=code,
                name=name,
                amount=amount,
                buy_nav=buy_nav,
                buy_date=buy_date,
            )

    async def delete_by_user(self, user_id: str, code: str) -> int:
        """删除持仓"""
        stmt = delete(Holding).where(and_(Holding.user_id == user_id, Holding.code == code))
        result = await self._session.execute(stmt)
        return result.rowcount

    async def clear_by_user(self, user_id: str) -> int:
        """清空用户持仓"""
        stmt = delete(Holding).where(Holding.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.rowcount


# ==================== FundsRepository ====================


class FundsRepository(AsyncRepository[Fund]):
    """基金 Repository"""

    model = Fund

    async def get_by_code(self, fund_code: str) -> Optional[Fund]:
        """根据代码获取基金"""
        stmt = select(Fund).where(Fund.fund_code == fund_code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> List[Fund]:
        """搜索基金"""
        stmt = (
            select(Fund).where(or_(Fund.fund_code.ilike(f"%{query}%"), Fund.fund_name.ilike(f"%{query}%"))).limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, days: int = 7) -> List[Fund]:
        """获取最近更新的基金"""
        since = datetime.now() - timedelta(days=days)
        stmt = select(Fund).where(Fund.updated_at >= since).order_by(Fund.updated_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class FundNavRepository(AsyncRepository[FundNav]):
    """基金净值 Repository"""

    model = FundNav

    async def get_latest(self, fund_code: str) -> Optional[FundNav]:
        """获取最新净值"""
        stmt = select(FundNav).where(FundNav.fund_code == fund_code).order_by(FundNav.nav_date.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(self, fund_code: str, days: int = 30) -> List[FundNav]:
        """获取历史净值"""
        since = date.today() - timedelta(days=days)
        stmt = (
            select(FundNav)
            .where(and_(FundNav.fund_code == fund_code, FundNav.nav_date >= since))
            .order_by(FundNav.nav_date.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, fund_code: str, nav_date: date, net_value: Optional[float] = None, **kwargs) -> FundNav:
        """upsert 净值"""
        stmt = select(FundNav).where(and_(FundNav.fund_code == fund_code, FundNav.nav_date == nav_date))
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        else:
            return await self.add(fund_code=fund_code, nav_date=nav_date, net_value=net_value, **kwargs)


class FundScoreRepository(AsyncRepository[FundScore]):
    """基金评分 Repository"""

    model = FundScore

    async def get_latest(self, fund_code: str) -> Optional[FundScore]:
        """获取最新评分"""
        stmt = select(FundScore).where(FundScore.fund_code == fund_code).order_by(FundScore.score_date.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


# ==================== ConfigRepository ====================


class ConfigRepository(AsyncRepository[Config]):
    """配置 Repository"""

    model = Config

    async def get_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户配置"""
        stmt = select(Config).where(Config.user_id == user_id)
        result = await self._session.execute(stmt)
        config = result.scalar_one_or_none()
        return config.config if config else None

    async def save_by_user(self, user_id: str, config_data: Dict[str, Any]) -> Config:
        """保存用户配置"""
        stmt = select(Config).where(Config.user_id == user_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.config = config_data
            existing.updated_at = datetime.now()
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        else:
            return await self.add(user_id=user_id, config=config_data)


# ==================== WatchlistRepository ====================


class WatchlistRepository(AsyncRepository[Watchlist]):
    """监控列表 Repository"""

    model = Watchlist

    async def get_by_user(self, user_id: str) -> List[str]:
        """获取用户监控列表"""
        stmt = select(Watchlist.code).where(Watchlist.user_id == user_id).order_by(Watchlist.created_at)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def add(self, user_id: str, code: str) -> Watchlist:
        """添加监控"""
        stmt = select(Watchlist).where(and_(Watchlist.user_id == user_id, Watchlist.code == code))
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing
        return await super().add(user_id=user_id, code=code)

    async def remove(self, user_id: str, code: str) -> int:
        """移除监控"""
        stmt = delete(Watchlist).where(and_(Watchlist.user_id == user_id, Watchlist.code == code))
        result = await self._session.execute(stmt)
        return result.rowcount


# ==================== HistoryRepository ====================


class HistoryRepository(AsyncRepository[History]):
    """历史记录 Repository"""

    model = History

    async def add_record(
        self,
        user_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> History:
        """添加历史记录"""
        return await self.add(user_id=user_id, action=action, details=details)

    async def get_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[History]:
        """获取用户历史记录"""
        stmt = (
            select(History)
            .where(History.user_id == user_id)
            .order_by(History.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# 辅助函数
from datetime import timedelta

__all__ = [
    "AsyncRepository",
    "UserRepository",
    "HoldingsRepository",
    "FundsRepository",
    "FundNavRepository",
    "FundScoreRepository",
    "ConfigRepository",
    "WatchlistRepository",
    "HistoryRepository",
]
