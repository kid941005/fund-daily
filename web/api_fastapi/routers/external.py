"""
External Data Router
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/external", tags=["外部数据"])


class FundCompareRequest(BaseModel):
    codes: List[str]


@router.get("/hot-rank")
async def get_hot_rank(limit: int = 20):
    """Get Xueqiu hot fund ranking"""
    try:
        from src.fetcher.xueqiu import get_fund_hot_rank

        rank_data = get_fund_hot_rank(limit)
        return {"success": True, "data": rank_data}
    except Exception as e:
        logger.error(f"Hot rank error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/fund-hot/{fund_code}")
async def get_fund_hot(fund_code: str):
    """Get single fund hot data"""
    try:
        from src.fetcher.xueqiu import fetch_fund_hot

        hot_data = fetch_fund_hot(fund_code)
        return {"success": True, "data": hot_data}
    except Exception as e:
        logger.error(f"Fund hot error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/fund-discussion/{fund_code}")
async def get_fund_discussion(fund_code: str, limit: int = 5):
    """Get fund discussion"""
    try:
        from src.fetcher.xueqiu import fetch_fund_discussion

        discussions = fetch_fund_discussion(fund_code, limit)
        return {"success": True, "data": discussions}
    except Exception as e:
        logger.error(f"Fund discussion error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/fund-compare")
async def compare_funds(data: FundCompareRequest):
    """Compare multiple funds"""
    fund_codes = data.codes

    if not fund_codes:
        return JSONResponse(status_code=400, content={"success": False, "error": "请提供基金代码"})

    try:
        from src.fetcher.alipay import get_fund_compare

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(get_fund_compare, [fund_codes]))

        return {"success": True, "data": results}
    except Exception as e:
        logger.error(f"Fund compare error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/portfolios")
async def get_portfolios():
    """Get Qianman portfolio list"""
    try:
        from src.fetcher.qianman import fetch_portfolio_list

        portfolios = fetch_portfolio_list()
        return {"success": True, "data": portfolios}
    except Exception as e:
        logger.error(f"Portfolios error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/advisors")
async def get_advisors():
    """Get fund advisors"""
    try:
        from src.fetcher.qianman import fetch_fund_advisor

        advisors = fetch_fund_advisor()
        return {"success": True, "data": advisors}
    except Exception as e:
        logger.error(f"Advisors error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_detail(portfolio_id: str):
    """Get portfolio detail"""
    try:
        from src.fetcher.qianman import fetch_portfolio_detail

        detail = fetch_portfolio_detail(portfolio_id)
        return {"success": True, "data": detail}
    except Exception as e:
        logger.error(f"Portfolio detail error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
