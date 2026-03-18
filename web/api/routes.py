"""
API routes for Fund Daily
所有API端点的统一入口

路由已拆分到 endpoints/ 目录：
- auth.py: 认证相关（register, login, logout, password）
- funds.py: 基金相关（/funds, /fund-detail, /score）
- holdings.py: 持仓相关（/holdings, /import）
- analysis.py: 分析相关（/portfolio-analysis, /expected-return）
- quant.py: 量化相关（/quant/timing-signals, /quant/portfolio-optimize）
- system.py: 系统相关（/health, /metrics, /advice）
- external.py: 外部数据（/external/*）
"""

import logging
from flask import Blueprint

logger = logging.getLogger(__name__)

# Create API blueprint
api = Blueprint("api", __name__)

# 导入拆分后的端点
from .endpoints.auth import auth_bp
from .endpoints.funds import funds_bp
from .endpoints.quant import quant_bp
from .endpoints.holdings import holdings_bp
from .endpoints.analysis import analysis_bp
from .endpoints.external import external_bp
from .endpoints.system import system_bp

# 注册蓝图
api.register_blueprint(auth_bp, url_prefix="/")
api.register_blueprint(funds_bp, url_prefix="/")
api.register_blueprint(holdings_bp, url_prefix="/")
api.register_blueprint(analysis_bp, url_prefix="/")
api.register_blueprint(quant_bp, url_prefix="/quant")
api.register_blueprint(external_bp, url_prefix="/external")
api.register_blueprint(system_bp, url_prefix="/")

# ============== Error Handlers ==============
def handle_error(e: Exception, message: str = "请求失败"):
    """统一错误处理"""
    from src.error import ErrorCode, create_error_response
    
    if "validation" in str(e).lower() or "无效" in str(e):
        error_code = ErrorCode.INVALID_INPUT
        http_status = 400
    elif "not found" in str(e).lower() or "未找到" in str(e):
        error_code = ErrorCode.FUND_NOT_FOUND
        http_status = 404
    elif "timeout" in str(e).lower():
        error_code = ErrorCode.TIMEOUT_ERROR
        http_status = 504
    else:
        error_code = ErrorCode.INTERNAL_ERROR
        http_status = 500
    
    return create_error_response(
        code=error_code,
        message=message,
        details={"exception": str(e)},
        http_status=http_status
    )


def handle_validation_error(message: str):
    """验证错误处理"""
    from src.error import ErrorCode, create_error_response
    return create_error_response(
        code=ErrorCode.INVALID_INPUT,
        message=message,
        http_status=400
    )
