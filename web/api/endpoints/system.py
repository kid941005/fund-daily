"""
系统相关 API 端点
包括 health, metrics, advice 等
"""

import psutil
import logging
from flask import Blueprint, jsonify, request, session

from db import database_pg as db
from src.fetcher import fetch_market_news, fetch_hot_sectors
from src.advice import analyze_fund, generate_advice

logger = logging.getLogger(__name__)

system_bp = Blueprint("system", __name__)


@system_bp.route("/health")
def health_check():
    """健康检查"""
    try:
        # 检查数据库
        db_status = "connected"
        try:
            db.get_user_by_username("test")
        except Exception:
            db_status = "disconnected"
        
        # 检查 Redis
        redis_status = "connected"
        try:
            from src.cache.redis_cache import get_redis_client
            get_redis_client().ping()
        except Exception:
            redis_status = "disconnected"
        
        return jsonify({
            "success": True,
            "service": "fund-daily",
            "status": "healthy",
            "database": db_status,
            "redis": redis_status,
            "version": "2.6.0"
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500


@system_bp.route("/metrics")
def metrics():
    """基础指标"""
    try:
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存使用
        memory = psutil.virtual_memory()
        
        # 持仓数量
        user_id = session.get("user_id")
        holdings_count = 0
        if user_id:
            try:
                holdings_count = len(db.get_holdings(user_id))
            except Exception:
                pass
        
        return jsonify({
            "success": True,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "holdings_count": holdings_count,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route("/metrics/enhanced")
def enhanced_metrics():
    """增强指标"""
    try:
        from src.services.enhanced_metrics_service import EnhancedMetricsService
        
        service = EnhancedMetricsService()
        metrics = service.get_all_metrics()
        
        return jsonify({
            "success": True,
            "metrics": metrics
        })
    except Exception as e:
        logger.error(f"Enhanced metrics error: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/news")
def news():
    """市场新闻"""
    try:
        limit = request.args.get("limit", 8, type=int)
        news_data = fetch_market_news(limit=limit)
        return jsonify({
            "success": True,
            "news": news_data
        })
    except Exception as e:
        logger.error(f"News error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route("/sectors")
def sectors():
    """热门板块"""
    try:
        limit = request.args.get("limit", 10, type=int)
        sectors_data = fetch_hot_sectors(limit=limit)
        return jsonify({
            "success": True,
            "sectors": sectors_data
        })
    except Exception as e:
        logger.error(f"Sectors error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route("/advice")
def get_advice():
    """获取投资建议"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({
                "success": False,
                "error": "请先登录"
            }), 401
        
        # 获取持仓
        holdings = db.get_holdings(user_id)
        
        if not holdings:
            return jsonify({
                "success": True,
                "advice": {
                    "funds": [],
                    "message": "暂无持仓"
                }
            })
        
        # 生成建议
        from src.services.fund_service import FundService
        fund_service = FundService()
        result = fund_service.calculate_holdings_advice(holdings)
        
        advice_data = result.get("advice", {})
        
        # 转换为前端需要的格式
        funds_data = []
        for holding in holdings:
            fund_data = {
                "code": holding.get("code"),
                "name": holding.get("name", ""),
                "amount": holding.get("amount", 0),
                "date": holding.get("buy_date"),
                "nav": holding.get("buy_nav"),
            }
            
            # 添加评分
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
        
        return jsonify({
            "success": True,
            "advice": advice_data
        })
    except Exception as e:
        logger.error(f"Advice error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# 导入 datetime
from datetime import datetime
