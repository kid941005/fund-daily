"""
AsyncCRUD - 异步数据库 CRUD 操作
与同步版本保持相同的函数签名，方便迁移
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from .async_database import AsyncDatabase

logger = logging.getLogger(__name__)

# 默认使用全局数据库实例
_default_db: Optional[AsyncDatabase] = None


async def _get_db() -> AsyncDatabase:
    """获取数据库实例"""
    global _default_db
    if _default_db is None:
        _default_db = await AsyncDatabase.from_env()
        await _default_db.initialize()
    return _default_db


async def get_async_db() -> AsyncDatabase:
    """获取异步数据库实例（公共接口）"""
    return await _get_db()


async def set_async_db(db: AsyncDatabase) -> None:
    """设置全局数据库实例"""
    global _default_db
    _default_db = db


# ==================== AsyncUserDB ====================


class AsyncUserDB:
    """异步用户数据库操作"""

    def __init__(self, db: Optional[AsyncDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncDatabase:
        """获取数据库实例"""
        return self._db if self._db else _get_db()

    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        sql = "SELECT * FROM users WHERE username = $1"
        return await self.db.fetch_one(sql, username)

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据用户ID获取用户"""
        sql = "SELECT * FROM users WHERE user_id = $1"
        return await self.db.fetch_one(sql, user_id)

    async def verify(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户登录"""
        from src.auth import verify_password

        user = await self.get_by_username(username)
        if not user:
            return None
        if verify_password(password, user.get("password", "")):
            return user
        return None

    async def create(self, user_id: str, username: str, password_hash: str) -> bool:
        """创建用户"""
        sql = """
            INSERT INTO users (user_id, username, password)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
        """
        result = await self.db.execute(sql, user_id, username, password_hash)
        return "INSERT 0 1" in result or result.endswith("1")

    async def update_password(self, user_id: str, new_password_hash: str) -> int:
        """更新密码"""
        sql = """
            UPDATE users 
            SET password = $2, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
        """
        return await self.db.execute_update(sql, user_id, new_password_hash)

    async def list_all(self) -> List[Dict[str, Any]]:
        """列出所有用户"""
        sql = "SELECT user_id, username, created_at, updated_at FROM users ORDER BY created_at DESC"
        return await self.db.fetch_all(sql)


# ==================== AsyncHoldingsDB ====================


class AsyncHoldingsDB:
    """异步持仓数据库操作"""

    def __init__(self, db: Optional[AsyncDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncDatabase:
        return self._db if self._db else _get_db()

    async def get_holdings(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户持仓列表"""
        sql = """
            SELECT code, name, amount, buy_nav, buy_date, created_at, updated_at
            FROM holdings
            WHERE user_id = $1
            ORDER BY created_at DESC
        """
        return await self.db.fetch_all(sql, user_id)

    async def save_holding(
        self,
        user_id: str,
        code: str,
        amount: float,
        name: str = "",
        buy_nav: Optional[float] = None,
        buy_date: Optional[date] = None,
    ) -> bool:
        """保存持仓"""
        sql = """
            INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id, code) DO UPDATE SET
                name = EXCLUDED.name,
                amount = EXCLUDED.amount,
                buy_nav = EXCLUDED.buy_nav,
                buy_date = EXCLUDED.buy_date,
                updated_at = CURRENT_TIMESTAMP
        """
        result = await self.db.execute(sql, user_id, code, name, amount, buy_nav, buy_date)
        return "INSERT 0 1" in result or result.endswith("1")

    async def delete_holding(self, user_id: str, code: str) -> int:
        """删除持仓"""
        sql = "DELETE FROM holdings WHERE user_id = $1 AND code = $2"
        return await self.db.execute_update(sql, user_id, code)

    async def clear_holdings(self, user_id: str) -> int:
        """清空用户所有持仓"""
        sql = "DELETE FROM holdings WHERE user_id = $1"
        return await self.db.execute_update(sql, user_id)

    async def save_holdings_batch(self, user_id: str, holdings: List[Dict[str, Any]]) -> int:
        """批量保存持仓"""
        if not holdings:
            return 0

        args_list = []
        for h in holdings:
            args_list.append(
                (
                    user_id,
                    h.get("code", ""),
                    h.get("name", ""),
                    h.get("amount", 0),
                    h.get("buy_nav") or h.get("buyNav"),
                    h.get("buy_date") or h.get("buyDate"),
                )
            )

        sql = """
            INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id, code) DO UPDATE SET
                name = EXCLUDED.name,
                amount = EXCLUDED.amount,
                buy_nav = EXCLUDED.buy_nav,
                buy_date = EXCLUDED.buy_date,
                updated_at = CURRENT_TIMESTAMP
        """

        async with self.db.acquire() as conn:
            async with conn.transaction():
                for args in args_list:
                    await conn.execute(sql, *args)
        return len(args_list)


# ==================== AsyncWatchlistDB ====================


class AsyncWatchlistDB:
    """异步监控列表操作"""

    def __init__(self, db: Optional[AsyncDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncDatabase:
        return self._db if self._db else _get_db()

    async def get_watchlist(self, user_id: str) -> List[str]:
        """获取监控列表"""
        sql = "SELECT code FROM watchlist WHERE user_id = $1 ORDER BY created_at"
        rows = await self.db.fetch_all(sql, user_id)
        return [r["code"] for r in rows]

    async def add_watchlist(self, user_id: str, code: str) -> bool:
        """添加监控"""
        sql = """
            INSERT INTO watchlist (user_id, code)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """
        result = await self.db.execute(sql, user_id, code)
        return result != "INSERT 0 0"

    async def remove_watchlist(self, user_id: str, code: str) -> int:
        """移除监控"""
        sql = "DELETE FROM watchlist WHERE user_id = $1 AND code = $2"
        return await self.db.execute_update(sql, user_id, code)


# ==================== AsyncConfigDB ====================


class AsyncConfigDB:
    """异步配置操作"""

    def __init__(self, db: Optional[AsyncDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncDatabase:
        return self._db if self._db else _get_db()

    async def get_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户配置"""
        sql = "SELECT config FROM config WHERE user_id = $1"
        row = await self.db.fetch_one(sql, user_id)
        return row["config"] if row else None

    async def save_config(self, user_id: str, config: Dict[str, Any]) -> bool:
        """保存用户配置"""
        sql = """
            INSERT INTO config (user_id, config, updated_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                config = EXCLUDED.config,
                updated_at = CURRENT_TIMESTAMP
        """
        result = await self.db.execute(sql, user_id, json.dumps(config))
        return "INSERT 0 1" in result or result.endswith("1")


# ==================== AsyncFundsDB ====================


class AsyncFundsDB:
    """异步基金数据库操作"""

    def __init__(self, db: Optional[AsyncDatabase] = None):
        self._db = db

    @property
    def db(self) -> AsyncDatabase:
        return self._db if self._db else _get_db()

    # --- 基金基本信息 ---

    async def save_fund_info(
        self,
        fund_code: str,
        fund_name: str,
        fund_type: Optional[str] = None,
        fund_company: Optional[str] = None,
        establish_date: Optional[date] = None,
        fund_size: Optional[float] = None,
        manager: Optional[str] = None,
        risk_level: Optional[str] = None,
        rating: Optional[float] = None,
    ) -> bool:
        """保存基金基本信息"""
        sql = """
            INSERT INTO funds (
                fund_code, fund_name, fund_type, fund_company,
                establish_date, fund_size, manager, risk_level, rating
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (fund_code) DO UPDATE SET
                fund_name = EXCLUDED.fund_name,
                fund_type = EXCLUDED.fund_type,
                fund_company = EXCLUDED.fund_company,
                establish_date = EXCLUDED.establish_date,
                fund_size = EXCLUDED.fund_size,
                manager = EXCLUDED.manager,
                risk_level = EXCLUDED.risk_level,
                rating = EXCLUDED.rating,
                updated_at = CURRENT_TIMESTAMP
        """
        result = await self.db.execute(
            sql, fund_code, fund_name, fund_type, fund_company, establish_date, fund_size, manager, risk_level, rating
        )
        return "INSERT 0 1" in result or result.endswith("1")

    async def get_fund_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金基本信息"""
        sql = "SELECT * FROM funds WHERE fund_code = $1"
        return await self.db.fetch_one(sql, fund_code)

    # --- 基金净值 ---

    async def save_fund_nav(
        self,
        fund_code: str,
        nav_date: date,
        net_value: Optional[float] = None,
        accumulated_value: Optional[float] = None,
        daily_return: Optional[float] = None,
        weekly_return: Optional[float] = None,
        monthly_return: Optional[float] = None,
        quarterly_return: Optional[float] = None,
        yearly_return: Optional[float] = None,
    ) -> bool:
        """保存基金净值数据"""
        # 先确保基金记录存在
        await self.db.execute(
            "INSERT INTO funds (fund_code, fund_name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            fund_code,
            f"基金{fund_code}",
        )

        sql = """
            INSERT INTO fund_nav (
                fund_code, nav_date, net_value, accumulated_value,
                daily_return, weekly_return, monthly_return,
                quarterly_return, yearly_return
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (fund_code, nav_date) DO UPDATE SET
                net_value = EXCLUDED.net_value,
                accumulated_value = EXCLUDED.accumulated_value,
                daily_return = EXCLUDED.daily_return,
                weekly_return = EXCLUDED.weekly_return,
                monthly_return = EXCLUDED.monthly_return,
                quarterly_return = EXCLUDED.quarterly_return,
                yearly_return = EXCLUDED.yearly_return,
                created_at = CURRENT_TIMESTAMP
        """
        result = await self.db.execute(
            sql,
            fund_code,
            nav_date,
            net_value,
            accumulated_value,
            daily_return,
            weekly_return,
            monthly_return,
            quarterly_return,
            yearly_return,
        )
        return "INSERT 0 1" in result or result.endswith("1")

    async def get_fund_nav(
        self,
        fund_code: str,
        nav_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取基金净值数据"""
        if nav_date:
            sql = "SELECT * FROM fund_nav WHERE fund_code = $1 AND nav_date = $2"
            return await self.db.fetch_one(sql, fund_code, nav_date)
        else:
            sql = """
                SELECT * FROM fund_nav
                WHERE fund_code = $1
                ORDER BY nav_date DESC LIMIT 1
            """
            return await self.db.fetch_one(sql, fund_code)

    # --- 基金评分 ---

    async def save_fund_score(
        self,
        fund_code: str,
        score_date: date,
        total_score: Optional[int] = None,
        valuation_score: Optional[int] = None,
        sector_score: Optional[int] = None,
        risk_score: Optional[int] = None,
        valuation_reason: Optional[str] = None,
        sector_reason: Optional[str] = None,
        risk_reason: Optional[str] = None,
    ) -> bool:
        """保存基金评分"""
        await self.db.execute(
            "INSERT INTO funds (fund_code, fund_name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            fund_code,
            f"基金{fund_code}",
        )

        sql = """
            INSERT INTO fund_scores (
                fund_code, score_date, total_score,
                valuation_score, sector_score, risk_score,
                valuation_reason, sector_reason, risk_reason
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (fund_code, score_date) DO UPDATE SET
                total_score = EXCLUDED.total_score,
                valuation_score = EXCLUDED.valuation_score,
                sector_score = EXCLUDED.sector_score,
                risk_score = EXCLUDED.risk_score,
                valuation_reason = EXCLUDED.valuation_reason,
                sector_reason = EXCLUDED.sector_reason,
                risk_reason = EXCLUDED.risk_reason,
                created_at = CURRENT_TIMESTAMP
        """
        result = await self.db.execute(
            sql,
            fund_code,
            score_date,
            total_score,
            valuation_score,
            sector_score,
            risk_score,
            valuation_reason,
            sector_reason,
            risk_reason,
        )
        return "INSERT 0 1" in result or result.endswith("1")

    async def get_fund_score(
        self,
        fund_code: str,
        score_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取基金评分"""
        if score_date:
            sql = "SELECT * FROM fund_scores WHERE fund_code = $1 AND score_date = $2"
            return await self.db.fetch_one(sql, fund_code, score_date)
        else:
            sql = """
                SELECT * FROM fund_scores
                WHERE fund_code = $1
                ORDER BY score_date DESC LIMIT 1
            """
            return await self.db.fetch_one(sql, fund_code)

    # --- 历史查询 ---

    async def get_recent_funds(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取最近有更新的基金"""
        sql = """
            WITH latest_nav AS (
                SELECT fund_code, nav_date, net_value,
                       ROW_NUMBER() OVER (PARTITION BY fund_code ORDER BY nav_date DESC) as rn
                FROM fund_nav
            ),
            latest_score AS (
                SELECT fund_code, score_date, total_score,
                       ROW_NUMBER() OVER (PARTITION BY fund_code ORDER BY score_date DESC) as rn
                FROM fund_scores
            )
            SELECT f.*,
                   ln.nav_date as last_nav_date,
                   ln.net_value as last_net_value,
                   ls.score_date as last_score_date,
                   ls.total_score as last_total_score
            FROM funds f
            LEFT JOIN latest_nav ln ON f.fund_code = ln.fund_code AND ln.rn = 1
            LEFT JOIN latest_score ls ON f.fund_code = ls.fund_code AND ls.rn = 1
            WHERE f.updated_at >= CURRENT_DATE - INTERVAL '1 day' * $1
            ORDER BY f.updated_at DESC
        """
        return await self.db.fetch_all(sql, days)

    async def search_funds(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索基金"""
        sql = """
            SELECT * FROM funds
            WHERE fund_code LIKE $1 OR fund_name LIKE $1
            ORDER BY fund_code
            LIMIT $2
        """
        return await self.db.fetch_all(sql, f"%{query}%", limit)

    async def get_fund_history(self, fund_code: str, days: int = 30) -> Dict[str, Any]:
        """获取基金历史数据"""
        sql = """
            SELECT
                f.fund_code, f.fund_name, f.fund_type, f.fund_company,
                f.manager, f.risk_level, f.rating,
                fn.nav_date, fn.net_value, fn.accumulated_value,
                fn.daily_return, fn.weekly_return, fn.monthly_return,
                fn.quarterly_return, fn.yearly_return,
                fs.score_date, fs.total_score,
                fs.valuation_score, fs.sector_score, fs.risk_score
            FROM funds f
            LEFT JOIN fund_nav fn ON f.fund_code = fn.fund_code
                AND fn.nav_date >= CURRENT_DATE - INTERVAL '1 day' * $2
            LEFT JOIN fund_scores fs ON f.fund_code = fs.fund_code
                AND fs.score_date >= CURRENT_DATE - INTERVAL '1 day' * $2
            WHERE f.fund_code = $1
            ORDER BY fn.nav_date DESC, fs.score_date DESC
        """
        rows = await self.db.fetch_all(sql, fund_code, days)

        if not rows:
            return {"fund_info": None, "nav_history": [], "score_history": []}

        first = rows[0]
        fund_info = {
            k: v
            for k, v in first.items()
            if k
            not in (
                "nav_date",
                "net_value",
                "accumulated_value",
                "daily_return",
                "weekly_return",
                "monthly_return",
                "quarterly_return",
                "yearly_return",
                "score_date",
                "total_score",
                "valuation_score",
                "sector_score",
                "risk_score",
            )
        }

        nav_history = [
            {
                k: v
                for k, v in dict(r).items()
                if k
                in (
                    "nav_date",
                    "net_value",
                    "accumulated_value",
                    "daily_return",
                    "weekly_return",
                    "monthly_return",
                    "quarterly_return",
                    "yearly_return",
                )
            }
            for r in rows
            if r["nav_date"]
        ]

        seen_scores = set()
        score_history = []
        for r in rows:
            if r["score_date"] and r["score_date"] not in seen_scores:
                seen_scores.add(r["score_date"])
                score_history.append(
                    {
                        "score_date": r["score_date"],
                        "total_score": r["total_score"],
                        "valuation_score": r["valuation_score"],
                        "sector_score": r["sector_score"],
                        "risk_score": r["risk_score"],
                    }
                )

        return {
            "fund_info": fund_info,
            "nav_history": nav_history,
            "score_history": score_history,
        }

    # --- 兼容层 ---

    async def save_fund_data(self, fund_code: str, fund_data: Dict[str, Any]) -> bool:
        """保存完整基金数据（兼容现有API格式）"""
        today = date.today()

        # 保存基本信息
        await self.save_fund_info(
            fund_code=fund_code,
            fund_name=fund_data.get("fund_name", f"基金{fund_code}"),
            fund_type=fund_data.get("fund_type"),
            fund_company=fund_data.get("fund_company"),
            establish_date=fund_data.get("establish_date"),
            fund_size=fund_data.get("fund_size"),
            manager=fund_data.get("manager"),
            risk_level=fund_data.get("risk_level"),
            rating=fund_data.get("rating"),
        )

        # 保存净值
        if "net_value" in fund_data:
            await self.save_fund_nav(
                fund_code=fund_code,
                nav_date=today,
                net_value=fund_data.get("net_value"),
                accumulated_value=fund_data.get("accumulated_value"),
                daily_return=fund_data.get("daily_return"),
                weekly_return=fund_data.get("weekly_return"),
                monthly_return=fund_data.get("monthly_return"),
                quarterly_return=fund_data.get("quarterly_return"),
                yearly_return=fund_data.get("yearly_return"),
            )

        # 保存评分
        score_100 = fund_data.get("score_100", {})
        if score_100:
            await self.save_fund_score(
                fund_code=fund_code,
                score_date=today,
                total_score=score_100.get("total_score"),
                valuation_score=score_100.get("valuation", {}).get("score"),
                sector_score=score_100.get("sector", {}).get("score"),
                risk_score=score_100.get("risk_control", {}).get("score"),
                valuation_reason=score_100.get("valuation", {}).get("reason"),
                sector_reason=score_100.get("sector", {}).get("reason"),
                risk_reason=score_100.get("risk_control", {}).get("reason"),
            )

        return True

    async def get_all_holdings(self) -> List[Dict[str, Any]]:
        """获取所有持仓"""
        sql = "SELECT * FROM holdings ORDER BY user_id, code"
        return await self.db.fetch_all(sql)


__all__ = [
    "AsyncUserDB",
    "AsyncHoldingsDB",
    "AsyncWatchlistDB",
    "AsyncConfigDB",
    "AsyncFundsDB",
    "get_async_db",
    "set_async_db",
]
