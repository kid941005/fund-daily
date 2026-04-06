"""
Funds Router
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from db import database_pg as db
from src.advice import analyze_fund, generate_100_score, get_fund_detail_info
from src.error import ErrorCode, create_error_response
from src.fetcher import fetch_fund_data_enhanced as fetch_fund_data
from src.jwt_auth import verify_access_token
from web.api_fastapi.middleware.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["基金"])


def _get_user_id(request: Request) -> str | None:
    """Get user_id from JWT token or session"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")

    # Fallback to session
    return request.cookies.get("session")


def _validate_fund_code(code: str) -> str:
    """Validate fund code format"""
    code = code.strip()
    if not re.match(r"^\d{6}[A-Z]*$", code):
        raise ValueError("基金代码格式错误，应为6位数字加可选字母后缀")
    return code


@router.get("/funds/health-alerts")
async def get_funds_health_alerts(
    request: Request,
    min_level: str = Query("info", description="最低告警级别: critical/warning/info/none"),
    market_day_only: bool = Query(False, description="仅返回交易日告警"),
):
    """
    获取所有基金的健康度告警

    - critical: 数据严重过时或缺失
    - warning: 数据偏旧（评分 < 60）
    - info: 数据一般（评分 60-80）
    - none: 数据健康

    当 min_level=warning 时，返回 critical + warning 告警
    当 min_level=critical 时，仅返回 critical 告警
    """
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    user_id = _get_user_id(request)
    holdings = db.get_holdings(user_id) if user_id else []

    codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
    if not codes:
        codes = ["000001", "110022", "161725"]

    try:
        from src.scoring import calculate_data_health, generate_health_report, is_market_day
        from db.fund_ops import get_fund_nav, get_fund_score

        health_indicators = []
        for code in codes:
            try:
                nav_data = get_fund_nav(code)
                score_data = get_fund_score(code)
                nav_updated_at = nav_data.get("created_at") if nav_data else None
                score_updated_at = score_data.get("created_at") if score_data else None
                nav_date = nav_data.get("nav_date") if nav_data else None

                health = calculate_data_health(
                    fund_code=code,
                    nav_updated_at=nav_updated_at,
                    score_updated_at=score_updated_at,
                    nav_date=str(nav_date) if nav_date else None,
                )
                health_indicators.append(health)
            except Exception as e:
                logger.warning(f"Failed to get health for {code}: {e}")

        # 生成报告
        report = generate_health_report(health_indicators)

        # 过滤告警级别
        level_priority = {"critical": 0, "warning": 1, "info": 2, "none": 3}
        min_priority = level_priority.get(min_level, 3)

        filtered_alerts = {"critical": [], "warning": [], "info": []}
        for level, alerts in report["alerts"].items():
            if level_priority.get(level, 3) <= min_priority:
                # 非交易日过滤（可选）
                if market_day_only and not report["market_day"]:
                    continue
                filtered_alerts[level] = alerts

        return {
            "success": True,
            "total_funds": len(health_indicators),
            "market_day": report["market_day"],
            "summary": {
                "critical_count": len(filtered_alerts["critical"]),
                "warning_count": len(filtered_alerts["warning"]),
                "info_count": len(filtered_alerts["info"]),
                "healthy_count": report["healthy_count"],
            },
            "alerts": filtered_alerts,
            "has_alerts": any(filtered_alerts.values()),
        }

    except Exception as e:
        logger.error(f"Health alerts error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"获取健康告警失败: {str(e)}"},
        )




@router.get("/market/status")
async def get_market_status():
    """
    获取市场状态和智能调度信息

    返回当前市场阶段和建议的抓取频率
    """
    try:
        from src.scheduler.market_aware import get_market_status

        return {"success": True, "data": get_market_status()}
    except Exception as e:
        logger.error(f"Market status error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"获取市场状态失败: {str(e)}"},
        )



@router.post("/funds/refresh")
async def refresh_funds(
    request: Request,
    codes: str = Query(None, description="基金代码，多个用逗号分隔；为空则刷新所有持仓"),
    refresh_scores: bool = Query(True, description="是否重新计算评分"),
):
    """
    手动刷新基金数据

    - 强制从 API 获取最新数据
    - 可指定基金代码或刷新所有持仓
    - 重新计算评分并保存到数据库
    """
    from src.fetcher import fetch_fund_data_enhanced as fetch_fund_data
    from src.advice import analyze_fund
    import asyncio

    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    user_id = _get_user_id(request)
    holdings = db.get_holdings(user_id) if user_id else []

    # 确定要刷新的基金代码
    if codes:
        fund_codes = [c.strip() for c in codes.split(",") if c.strip()]
    else:
        fund_codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]

    if not fund_codes:
        return {"success": False, "error": "没有要刷新的基金", "refreshed": 0}

    async def refresh_single(code: str) -> dict:
        """异步刷新单个基金"""
        try:
            # 强制刷新，不使用缓存
            data = await asyncio.to_thread(fetch_fund_data, code, use_cache=False, force_refresh=True)
            if data and not data.get("error"):
                # 触发评分计算和保存
                result = analyze_fund(data, use_cache=False)
                return {
                    "code": code,
                    "success": True,
                    "data_updated": True,
                    "score_updated": "score_100" in result,
                }
            return {"code": code, "success": False, "error": data.get("error", "获取数据失败")}
        except Exception as e:
            return {"code": code, "success": False, "error": str(e)}

    # 并发刷新所有基金
    results = await asyncio.gather(*[refresh_single(code) for code in fund_codes])

    success_count = sum(1 for r in results if r.get("success"))
    failed = [r for r in results if not r.get("success")]

    return {
        "success": True,
        "total": len(fund_codes),
        "refreshed": success_count,
        "failed": len(failed),
        "results": results,
        "refresh_scores": refresh_scores,
    }



@router.get("/funds")
async def get_funds(request: Request, force: str = Query("false")):
    """Get all funds for user"""
    # Check rate limit
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    user_id = _get_user_id(request)
    holdings = db.get_holdings(user_id) if user_id else []

    # Check force refresh - force=true means disable cache (refresh)
    force_refresh = force.lower() == "true"
    use_cache = not force_refresh

    codes = [h["code"] for h in holdings if h.get("amount", 0) > 0]
    if not codes:
        codes = ["000001", "110022", "161725"]

    def process_fund(fund_code):
        from src.scoring import calculate_data_health
        from db.fund_ops import get_fund_nav, get_fund_score

        data = fetch_fund_data(fund_code, use_cache=use_cache)
        if not data.get("error"):
            result = analyze_fund(data, use_cache=use_cache)

            # 添加数据健康度
            try:
                nav_data = get_fund_nav(fund_code)
                score_data = get_fund_score(fund_code)
                nav_updated_at = nav_data.get("created_at") if nav_data else None
                score_updated_at = score_data.get("created_at") if score_data else None
                nav_date = nav_data.get("nav_date") if nav_data else None

                health = calculate_data_health(
                    fund_code=fund_code,
                    nav_updated_at=nav_updated_at,
                    score_updated_at=score_updated_at,
                    nav_date=str(nav_date) if nav_date else None,
                )
                result["data_health"] = health.to_dict()
            except Exception as e:
                logger.warning(f"Failed to calculate data health for {fund_code}: {e}")

            return result
        return None

    funds_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_fund, code): code for code in codes}
        for future in as_completed(futures):
            result = future.result()
            if result:
                funds_data.append(result)

    return {"success": True, "funds": funds_data, "force_refresh": force_refresh}


@router.get("/fund-detail/{fund_code}")
async def get_fund_detail(request: Request, fund_code: str, force: str = Query("false")):
    """Get fund detail"""
    # Check rate limit
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    # Validate fund code
    try:
        fund_code = _validate_fund_code(fund_code)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

    use_cache = force.lower() != "true"
    detail = get_fund_detail_info(fund_code, use_cache=use_cache)
    return {"success": True, "detail": detail}


@router.get("/score/{fund_code}")
async def get_fund_score(request: Request, fund_code: str, force: str = Query("false")):
    """Get fund score report (100-point system)"""
    # Check rate limit
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    # Validate fund code
    try:
        fund_code = _validate_fund_code(fund_code)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

    use_cache = force.lower() != "true"

    try:
        fund_data = fetch_fund_data(fund_code, use_cache=use_cache)
        if fund_data.get("error"):
            error_response, status_code = create_error_response(
                ErrorCode.FUND_DATA_FETCH_FAILED,
                fund_data.get("error", "获取基金数据失败"),
                details={"fund_code": fund_code},
                http_status=500,
            )
            return JSONResponse(status_code=status_code, content=error_response)

        daily_change = float(fund_data.get("estimated_change", 0) or fund_data.get("gszzl", 0) or 0)
        scoring = generate_100_score(fund_code, daily_change, use_cache=use_cache)

        if "error" in scoring:
            error_response, status_code = create_error_response(
                ErrorCode.FUND_SCORE_CALCULATION_FAILED,
                scoring.get("error", "计算基金评分失败"),
                details={"fund_code": fund_code},
                http_status=500,
            )
            return JSONResponse(status_code=status_code, content=error_response)

        # 获取数据健康度
        from src.scoring import calculate_data_health
        from db.fund_ops import get_fund_nav, get_fund_score as get_score_from_db

        try:
            nav_data = get_fund_nav(fund_code)
            score_data = get_score_from_db(fund_code)
            nav_updated_at = nav_data.get("created_at") if nav_data else None
            score_updated_at = score_data.get("created_at") if score_data else None
            nav_date = nav_data.get("nav_date") if nav_data else None

            health = calculate_data_health(
                fund_code=fund_code,
                nav_updated_at=nav_updated_at,
                score_updated_at=score_updated_at,
                nav_date=str(nav_date) if nav_date else None,
            )
            data_health = health.to_dict()
        except Exception as e:
            logger.warning(f"Failed to calculate data health for {fund_code}: {e}")
            data_health = None

        return {
            "success": True,
            "fund_code": fund_code,
            "fund_name": fund_data.get("name", ""),
            "daily_change": daily_change,
            "scoring": scoring,
            "data_health": data_health,
        }
    except Exception as e:
        error_response, status_code = create_error_response(
            ErrorCode.FUND_SCORE_CALCULATION_FAILED,
            f"基金评分计算异常: {str(e)}",
            details={"fund_code": fund_code},
            http_status=500,
        )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/fund-detail/{fund_code}/score-trace")
async def get_fund_score_trace(
    request: Request,
    fund_code: str,
    date: str = Query(None, description="查询日期，格式 YYYY-MM-DD，默认为最新"),
    history: int = Query(0, ge=0, le=30, description="查询最近 N 天的历史评分"),
):
    """
    获取基金评分追溯信息（含完整审计链）

    - 各维度评分可追溯到原始输入 → 评分规则 → 计算结果
    - 记录数据源、数据抓取时间、算法版本
    - 支持查询历史评分
    """
    limit_result = check_rate_limit(request, "funds")
    if not limit_result["allowed"]:
        raise HTTPException(status_code=429, detail={"success": False, "error": "请求过于频繁"})

    try:
        fund_code = _validate_fund_code(fund_code)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

    try:
        from db.fund_ops import get_fund_score
        from src.scoring import SCORE_VERSION

        result = {
            "success": True,
            "fund_code": fund_code,
            "calculation_version": SCORE_VERSION,
        }

        if history > 0:
            # 查询最近 N 天历史评分
            records = []
            for i in range(history):
                query_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                record = get_fund_score(fund_code, score_date=query_date)
                if record:
                    records.append(_format_score_trace(record))

            result["history"] = records
            result["history_days"] = history
            return result
        else:
            # 查询指定日期或最新评分
            score_date = date if date else None
            record = get_fund_score(fund_code, score_date=score_date)

            if not record:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "error": "未找到评分记录", "fund_code": fund_code},
                )

            result["trace"] = _format_score_trace(record)
            return result

    except Exception as e:
        logger.error(f"Score trace error: {fund_code}, {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"获取评分追溯失败: {str(e)}", "fund_code": fund_code},
        )


def _format_score_trace(record: dict) -> dict:
    """格式化评分追溯记录"""
    d = record
    fund_code = d.get("fund_code", "")

    # 计算 freshness
    data_fetched_at = d.get("data_fetched_at")
    freshness = None
    if data_fetched_at:
        try:
            fetched_time = data_fetched_at if isinstance(data_fetched_at, datetime) else datetime.fromisoformat(str(data_fetched_at))
            delta = datetime.now() - fetched_time
            if delta.days > 0:
                freshness = f"{delta.days}天前"
            elif delta.seconds >= 3600:
                freshness = f"{delta.seconds // 3600}小时前"
            else:
                freshness = f"{delta.seconds // 60}分钟前"
        except Exception:
            freshness = None

    # 构建维度详情
    dimensions = {}
    for dim, score_col, reason_col in [
        ("valuation", "valuation_score", "valuation_reason"),
        ("performance", "performance_score", "performance_reason"),
        ("risk_control", "risk_score", "risk_reason"),
        ("momentum", "momentum_score", "momentum_reason"),
        ("sentiment", "sentiment_score", "sentiment_reason"),
        ("sector", "sector_score", "sector_reason"),
        ("manager", "manager_score", "manager_reason"),
        ("liquidity", "liquidity_score", "liquidity_reason"),
    ]:
        score = d.get(score_col)
        reason = d.get(reason_col, "")
        if score is not None:
            dimensions[dim] = {
                "score": int(score) if score else 0,
                "reason": reason or "",
            }

    # 解析原始输入快照
    dimension_inputs = d.get("dimension_inputs")
    if dimension_inputs:
        try:
            import json
            if isinstance(dimension_inputs, str):
                dimension_inputs = json.loads(dimension_inputs)
            for dim_name in dimensions:
                if dim_name in dimension_inputs:
                    dimensions[dim_name]["input"] = dimension_inputs[dim_name]
        except Exception:
            pass

    return {
        "fund_code": fund_code,
        "score_date": str(d.get("score_date", "")),
        "total_score": int(d.get("total_score", 0)) if d.get("total_score") else 0,
        "dimensions": dimensions,
        "data_audit": {
            "source": d.get("data_source", "unknown"),
            "fetched_at": str(data_fetched_at) if data_fetched_at else None,
            "calculation_version": d.get("calculation_version", SCORE_VERSION),
            "freshness": freshness,
        },
        "created_at": str(d.get("created_at", "")) if d.get("created_at") else None,
    }
