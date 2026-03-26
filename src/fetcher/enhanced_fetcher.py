"""
增强版基金数据获取器
优先从PostgreSQL数据库获取数据，数据库没有或数据过期时再从外部API获取
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 导入数据库函数
try:
    from db import (
        get_fund_history,
        get_fund_info,
        get_fund_nav,
        get_fund_score,
        save_fund_data,
        save_fund_info,
        save_fund_nav,
        save_fund_score,
    )

    HAS_DB = True
except ImportError as e:
    logger.warning(f"数据库模块导入失败: {e}")
    HAS_DB = False

# 导入原始fetcher（直接从子模块避免循环导入）
from .fund_basic.fetcher import fetch_fund_data as original_fetch_fund_data
from .fund_basic.fetcher import fetch_fund_detail as original_fetch_fund_detail


class EnhancedFetcher:
    """增强版基金数据获取器"""

    def __init__(self, db_fallback_hours=24):
        """
        初始化增强版fetcher

        Args:
            db_fallback_hours: 数据库数据过期时间（小时），超过此时间的数据视为过期
        """
        self.db_fallback_hours = db_fallback_hours
        self.has_db = HAS_DB

    def fetch_fund_data(self, fund_code: str, use_cache: bool = True, force_refresh: bool = False) -> Dict:
        """
        获取基金数据，优先从数据库

        Args:
            fund_code: 基金代码
            use_cache: 是否使用缓存
            force_refresh: 是否强制刷新（忽略数据库和缓存）

        Returns:
            基金数据字典
        """
        # 如果强制刷新，直接调用原始API
        if force_refresh:
            logger.info(f"强制刷新基金数据: {fund_code}")
            return self._fetch_from_api_and_save(fund_code)

        # 1. 首先尝试从数据库获取（如果数据库可用）
        if self.has_db:
            try:
                db_data = self._get_fund_data_from_db(fund_code)
                if db_data:
                    # 检查数据来源日期是否过期
                    data_date_str = db_data.get("jzrq") or db_data.get("nav_date")
                    if data_date_str:
                        from datetime import date, datetime

                        if isinstance(data_date_str, str):
                            try:
                                data_date = datetime.strptime(data_date_str, "%Y-%m-%d").date()
                                days_old = (date.today() - data_date).days
                                if days_old * 24 > self.db_fallback_hours:
                                    logger.info(f"数据库数据过期 ({days_old}天): {fund_code}，回退到API")
                                    db_data = None  # 标记为过期，重新获取
                            except ValueError:
                                pass  # 日期格式无法解析，使用数据库数据
                    if db_data:
                        logger.info(f"从数据库获取基金数据: {fund_code}")
                        return db_data
            except Exception as e:
                logger.warning(f"从数据库获取基金数据失败，回退到API: {fund_code}, {e}")

        # 2. 调用原始fetcher（会使用缓存）
        logger.info(f"从API获取基金数据: {fund_code}")
        api_data = original_fetch_fund_data(fund_code, use_cache)

        # 3. 保存到数据库（如果数据库可用）
        if self.has_db and "error" not in api_data:
            try:
                self._save_fund_data_to_db(fund_code, api_data)
            except Exception as e:
                logger.error(f"保存基金数据到数据库失败: {fund_code}, {e}")

        return api_data

    def fetch_fund_detail(self, fund_code: str, force_refresh: bool = False) -> Dict:
        """
        获取基金详情，优先从数据库

        Args:
            fund_code: 基金代码
            force_refresh: 是否强制刷新

        Returns:
            基金详情字典
        """
        # 如果强制刷新，直接调用原始API
        if force_refresh:
            return original_fetch_fund_detail(fund_code)

        # 1. 尝试从数据库获取基金基本信息
        if self.has_db:
            try:
                fund_info = get_fund_info(fund_code)
                if fund_info:
                    # 构造类似API返回的数据结构
                    db_data = {
                        "fund_code": fund_info.get("fund_code"),
                        "fund_name": fund_info.get("fund_name"),
                        "fund_type": fund_info.get("fund_type"),
                        "fund_company": fund_info.get("fund_company"),
                        "establish_date": fund_info.get("establish_date"),
                        "fund_size": float(fund_info.get("fund_size") or 0),
                        "manager": fund_info.get("manager"),
                        "risk_level": fund_info.get("risk_level"),
                        "rating": float(fund_info.get("rating") or 0),
                        "source": "database",
                    }

                    # 获取最新净值
                    nav_data = get_fund_nav(fund_code)
                    if nav_data:
                        db_data.update(
                            {
                                "net_value": float(nav_data.get("net_value") or 0),
                                "accumulated_value": float(nav_data.get("accumulated_value") or 0),
                                "daily_return": float(nav_data.get("daily_return") or 0),
                                "weekly_return": float(nav_data.get("weekly_return") or 0),
                                "monthly_return": float(nav_data.get("monthly_return") or 0),
                                "quarterly_return": float(nav_data.get("quarterly_return") or 0),
                                "yearly_return": float(nav_data.get("yearly_return") or 0),
                            }
                        )

                    # 获取最新评分
                    score_data = get_fund_score(fund_code)
                    if score_data:
                        db_data["score_100"] = {
                            "total_score": score_data.get("total_score"),
                            "valuation": {
                                "score": score_data.get("valuation_score"),
                                "reason": score_data.get("valuation_reason"),
                            },
                            "sector": {
                                "score": score_data.get("sector_score"),
                                "reason": score_data.get("sector_reason"),
                            },
                            "risk_control": {
                                "score": score_data.get("risk_score"),
                                "reason": score_data.get("risk_reason"),
                            },
                        }

                    logger.info(f"从数据库获取基金详情: {fund_code}")
                    return db_data
            except Exception as e:
                logger.warning(f"从数据库获取基金详情失败，回退到API: {fund_code}, {e}")

        # 2. 调用原始API
        api_data = original_fetch_fund_detail(fund_code)

        # 3. 保存到数据库
        if self.has_db and api_data and "error" not in api_data:
            try:
                save_fund_data(fund_code, api_data)
            except Exception as e:
                logger.error(f"保存基金详情到数据库失败: {fund_code}, {e}")

        return api_data

    def _get_fund_data_from_db(self, fund_code: str) -> Optional[Dict]:
        """从数据库获取基金数据"""
        if not self.has_db:
            return None

        try:
            # 获取基金基本信息
            fund_info = get_fund_info(fund_code)
            if not fund_info:
                return None

            # 获取最新净值（今天或最近）
            nav_date = date.today()
            nav_data = get_fund_nav(fund_code, nav_date)

            # 如果今天没有净值数据，获取最近的
            if not nav_data:
                nav_data = get_fund_nav(fund_code)
                if nav_data:
                    # 检查数据是否过期
                    data_date = nav_data.get("nav_date")
                    if isinstance(data_date, str):
                        data_date = datetime.strptime(data_date, "%Y-%m-%d").date()

                    if data_date and (date.today() - data_date).days > self.db_fallback_hours / 24:
                        logger.info(f"数据库净值数据过期: {fund_code}, 数据日期: {data_date}")
                        return None

            # 获取最新评分
            score_data = get_fund_score(fund_code)

            # 构造返回数据
            result = {
                "fundcode": fund_code,
                "name": fund_info.get("fund_name", f"基金{fund_code}"),
                "source": "database",
            }

            if nav_data:
                result.update(
                    {
                        "nav": float(nav_data.get("net_value") or 0),
                        "accnav": float(nav_data.get("accumulated_value") or 0),
                        "gszzl": float(nav_data.get("daily_return") or 0) * 100,  # 转换为百分比
                        "jzrq": nav_data.get("nav_date"),
                    }
                )

            if score_data:
                result["score_100"] = {
                    "total_score": score_data.get("total_score"),
                    "valuation": {
                        "score": score_data.get("valuation_score"),
                        "reason": score_data.get("valuation_reason"),
                    },
                }

            return result

        except Exception as e:
            logger.error(f"从数据库获取基金数据异常: {fund_code}, {e}")
            return None

    def _save_fund_data_to_db(self, fund_code: str, api_data: Dict):
        """保存API数据到数据库"""
        if not self.has_db or not api_data or "error" in api_data:
            return

        try:
            # 提取基金基本信息
            fund_name = api_data.get("name", f"基金{fund_code}")

            # 保存到数据库
            save_fund_data(
                fund_code,
                {
                    "fund_code": fund_code,
                    "fund_name": fund_name,
                    "net_value": float(api_data.get("nav") or 0),
                    "accumulated_value": float(api_data.get("accnav") or 0),
                    "daily_return": float(api_data.get("gszzl") or 0) / 100,  # 从百分比转换
                    "jzrq": api_data.get("jzrq", date.today().isoformat()),
                    # 其他字段可以从基金详情API获取
                },
            )

        except Exception as e:
            logger.error(f"保存基金数据到数据库失败: {fund_code}, {e}")

    def _fetch_from_api_and_save(self, fund_code: str) -> Dict:
        """从API获取数据并保存到数据库"""
        api_data = original_fetch_fund_data(fund_code, use_cache=False)

        if self.has_db and api_data and "error" not in api_data:
            self._save_fund_data_to_db(fund_code, api_data)

        return api_data

    def get_fund_history(self, fund_code: str, days: int = 30) -> Dict:
        """获取基金历史数据"""
        if self.has_db:
            try:
                history = get_fund_history(fund_code, days)
                if history:
                    history["source"] = "database"
                    return history
            except Exception as e:
                logger.warning(f"从数据库获取历史数据失败: {fund_code}, {e}")

        # 数据库不可用或没有数据，返回空结构
        return {"fund_info": None, "nav_history": [], "score_history": [], "source": "none"}

    def update_fund_data(self, fund_code: str) -> bool:
        """手动更新基金数据"""
        try:
            # 强制从API获取最新数据
            api_data = self._fetch_from_api_and_save(fund_code)
            return "error" not in api_data
        except Exception as e:
            logger.error(f"更新基金数据失败: {fund_code}, {e}")
            return False


# 全局实例
_enhanced_fetcher = None


def get_enhanced_fetcher() -> EnhancedFetcher:
    """获取增强版fetcher实例"""
    global _enhanced_fetcher
    if _enhanced_fetcher is None:
        _enhanced_fetcher = EnhancedFetcher()
    return _enhanced_fetcher


# 兼容性函数
def fetch_fund_data_enhanced(fund_code: str, use_cache: bool = True, force_refresh: bool = False) -> Dict:
    """增强版fetch_fund_data函数"""
    fetcher = get_enhanced_fetcher()
    return fetcher.fetch_fund_data(fund_code, use_cache, force_refresh)


def fetch_fund_detail_enhanced(fund_code: str, force_refresh: bool = False) -> Dict:
    """增强版fetch_fund_detail函数"""
    fetcher = get_enhanced_fetcher()
    return fetcher.fetch_fund_detail(fund_code, force_refresh)


def get_fund_history_enhanced(fund_code: str, days: int = 30) -> Dict:
    """获取基金历史数据"""
    fetcher = get_enhanced_fetcher()
    return fetcher.get_fund_history(fund_code, days)
