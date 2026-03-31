"""
System Router
"""

import json
import logging
import os
from datetime import datetime

import psutil
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db import database_pg as db
from src.config import get_config
from src.error import ErrorCode, create_error_response
from src.fetcher import fetch_hot_sectors, fetch_market_news
from src.jwt_auth import verify_access_token
from src.services.fund_service import FundService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["系统"])

# Config file path
DATA_DIR = os.path.expanduser("~/.openclaw/workspace/skills/fund-daily/data")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.json")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


def _get_user_id(request: Request) -> str | None:
    """Get user_id from JWT token or session"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return request.cookies.get("session")


def load_config() -> dict:
    """Load config from file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
    return {}


def save_config(config: dict):
    """Save config to file"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


class ConfigUpdateRequest(BaseModel):
    default_funds: list | None = None
    dingtalk: dict | None = None


@router.get("/config")
async def get_config_endpoint():
    """Get config"""
    config = load_config()
    safe_config = config.copy()
    if "dingtalk" in safe_config:
        safe_config["dingtalk"] = {
            **safe_config["dingtalk"],
            "webhook": "***" if safe_config["dingtalk"].get("webhook") else "",
        }
    return {"success": True, "config": safe_config}


@router.post("/config")
async def update_config_endpoint(data: ConfigUpdateRequest):
    """Update config"""
    config = load_config()

    if data.default_funds is not None:
        config["default_funds"] = data.default_funds

    if data.dingtalk is not None:
        notifier_data = data.dingtalk
        if isinstance(notifier_data, dict):
            if notifier_data.get("webhook", "").startswith("***"):
                notifier_data["webhook"] = config.get("dingtalk", {}).get("webhook", "")
            config["dingtalk"] = notifier_data

    save_config(config)
    return {"success": True}


@router.get("/health")
async def health_check():
    """Health check"""
    try:
        # Check database
        db_status = "connected"
        try:
            db.get_user_by_username("test")
        except Exception:
            db_status = "disconnected"

        # Check Redis
        redis_status = "connected"
        try:
            from src.cache.redis_cache import get_redis_client

            get_redis_client().ping()
        except Exception:
            redis_status = "disconnected"

        return {
            "success": True,
            "service": "fund-daily",
            "status": "healthy",
            "database": db_status,
            "redis": redis_status,
            "version": get_config().app.version,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "status": "unhealthy", "error": str(e)})


@router.get("/metrics")
async def metrics():
    """Basic metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        user_id = _get_user_id_from_headers()  # Need to handle this separately
        holdings_count = 0
        if user_id:
            try:
                holdings_count = len(db.get_holdings(user_id))
            except Exception:
                pass

        return {
            "success": True,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "holdings_count": holdings_count,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        error_response, status_code = create_error_response(
            ErrorCode.DB_OPERATION_FAILED,
            message=f"获取系统指标失败: {str(e)}",
            details={"endpoint": "metrics"},
            http_status=500,
        )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/news")
async def news_endpoint(limit: int = 8):
    """Market news"""
    try:
        news_data = fetch_market_news(limit=limit)
        return {"success": True, "news": news_data}
    except Exception as e:
        logger.error(f"News error: {e}")
        error_response, status_code = create_error_response(
            ErrorCode.INTERNAL_ERROR, message=f"内部服务器错误: {str(e)}", http_status=500
        )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/sectors")
async def sectors_endpoint(limit: int = 10):
    """Hot sectors"""
    try:
        sectors_data = fetch_hot_sectors(limit=limit)
        return {"success": True, "sectors": sectors_data}
    except Exception as e:
        logger.error(f"Sectors error: {e}")
        error_response, status_code = create_error_response(
            ErrorCode.INTERNAL_ERROR, message=f"内部服务器错误: {str(e)}", http_status=500
        )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/advice")
async def get_advice_endpoint(request: Request):
    """Get investment advice"""
    try:
        user_id = _get_user_id(request)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "error": "请先登录"})

        # Get holdings
        holdings = db.get_holdings(user_id)

        if not holdings:
            return {"success": True, "advice": {"funds": [], "message": "暂无持仓"}}

        # Generate advice
        fund_service = FundService()
        result = fund_service.calculate_holdings_advice(holdings)

        advice_data = result.get("advice", {})

        # Build funds data
        funds_data = []
        for holding in holdings:
            fund_data = {
                "code": holding.get("code"),
                "name": holding.get("name", ""),
                "amount": holding.get("amount", 0),
                "date": holding.get("buy_date"),
                "nav": holding.get("buy_nav"),
            }

            # Add score
            code = holding.get("code")
            if code:
                try:
                    score = db.get_fund_score(code)
                    if score:
                        fund_data["score_100"] = score
                except Exception:
                    pass

            funds_data.append(fund_data)

        advice_data["funds"] = funds_data

        return {"success": True, "advice": advice_data}
    except Exception as e:
        logger.error(f"Advice error: {e}")
        error_response, status_code = create_error_response(
            ErrorCode.INTERNAL_ERROR, message=f"内部服务器错误: {str(e)}", http_status=500
        )
        return JSONResponse(status_code=status_code, content=error_response)


# Helper function to get user from Authorization header only (for /metrics endpoint)
def _get_user_id_from_headers(request: Request = None) -> str | None:
    """Get user_id from Authorization header only"""
    if request is None:
        return None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return None
