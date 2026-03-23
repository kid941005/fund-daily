"""
Analysis API endpoints
"""

from flask import Blueprint, jsonify, request, session
from src.jwt_auth import verify_access_token, get_token_from_header
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.services.fund_service import get_fund_service
from src.analyzer import calculate_expected_return
from db import database_pg as db

analysis_bp = Blueprint("analysis", __name__)


def _get_user_id():
    """从 JWT token 或 session 获取用户ID"""
    token = get_token_from_header()
    if token:
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    return session.get("user_id")


@analysis_bp.route("/portfolio-analysis")
@analysis_bp.route("/analysis/portfolio")  # 兼容前端调用
def get_portfolio_analysis():
    """Get portfolio analysis using new service layer"""
    user_id = _get_user_id()

    # 必须登录，未认证用户不得访问任何持仓数据
    if not user_id:
        from src.error import ErrorCode, create_error_response
        return jsonify(create_error_response(
            code=ErrorCode.UNAUTHORIZED,
            message="请先登录",
            http_status=401
        )), 401

    if user_id:
        holdings = db.get_holdings(user_id)
        print(f"[DEBUG] 用户 {user_id} 的持仓数量: {len(holdings)}")
        holdings_dict = {h["code"]: h for h in holdings}
    else:
        # 如果没有用户，尝试获取所有持仓
        try:
            # 使用数据库连接池
            pool = db.get_pool()
            conn = pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT code, name, amount FROM holdings WHERE amount > 0")
            holdings = []
            for row in cursor.fetchall():
                holdings.append({
                    "code": row[0],
                    "name": row[1] or f"基金{row[0]}",
                    "amount": float(row[2])
                })
            print(f"[DEBUG] 获取所有持仓数量: {len(holdings)}")
            holdings_dict = {h["code"]: h for h in holdings}
            cursor.close()
            pool.putconn(conn)
        except Exception as e:
            print(f"[DEBUG] 获取所有持仓失败: {e}")
            holdings = []
            holdings_dict = {}

    try:
        # 使用新的FundService获取持仓建议
        fund_service = get_fund_service(cache_enabled=True)
        advice_result = fund_service.calculate_holdings_advice(holdings)
        
        funds = advice_result.get("funds", [])
        total_amount = advice_result.get("total_amount", 0)
        
        # 构建基本的投资组合分析
        if funds and total_amount > 0:
            # 计算风险指标
            risk_scores = []
            returns_1y = []
            
            for fund in funds:
                # 尝试从score_100获取风险评分
                score_data = fund.get("score_100", {})
                risk_score = score_data.get("details", {}).get("risk_control", {}).get("score", 4)
                risk_scores.append(risk_score)
                
                # 获取1年收益率
                fund_data = fund.get("fund_data", {})
                return_1y = float(fund_data.get("return_1y", 0) or 0)
                returns_1y.append(return_1y)
            
            # 计算加权平均风险
            weights = [fund.get("current_pct", 0) for fund in funds]
            if sum(weights) > 0:
                weighted_risk = sum(r * w for r, w in zip(risk_scores, weights)) / sum(weights)
                weighted_return = sum(r * w for r, w in zip(returns_1y, weights)) / sum(weights)
            else:
                weighted_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 4
                weighted_return = sum(returns_1y) / len(returns_1y) if returns_1y else 0
            
            # 确定风险级别
            if weighted_risk > 6:
                risk_level = "高风险"
            elif weighted_risk > 4:
                risk_level = "中高风险"
            elif weighted_risk > 2:
                risk_level = "中等风险"
            else:
                risk_level = "中低风险"
            
            # 分散度评估
            fund_count = len(funds)
            if fund_count >= 5:
                diversification = "良好"
            elif fund_count >= 3:
                diversification = "一般"
            else:
                diversification = "需分散"
            
            analysis = {
                "risk_level": risk_level,
                "risk_score": round(weighted_risk, 1),
                "avg_return_1y": round(weighted_return, 2),
                "fund_count": fund_count,
                "diversification": diversification,
                "total_amount": total_amount,
                "funds": funds,  # 添加基金数据供图表使用
                "message": "分析完成"
            }
        else:
            # 即使没有基金数据，也返回持仓数据供图表使用
            # 从持仓数据构建基本的基金信息
            chart_funds = []
            for holding in holdings:
                chart_funds.append({
                    "fund_code": holding.get("code"),
                    "fund_name": holding.get("name") or f"基金{holding.get('code')}",
                    "amount": holding.get("amount", 0),
                    "score_100": {"total_score": 50}  # 默认评分
                })
            
            analysis = {
                "risk_level": "未知",
                "risk_score": 0,
                "avg_return_1y": 0,
                "fund_count": len(holdings),
                "diversification": "无详细数据",
                "total_amount": sum(h.get("amount", 0) for h in holdings),
                "funds": chart_funds,  # 使用持仓数据
                "message": "使用持仓数据，基金详情待更新"
            }
        
        return jsonify({"success": True, "analysis": analysis})
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "analysis": {
                "risk_level": "未知",
                "risk_score": 0,
                "avg_return_1y": 0,
                "fund_count": 0,
                "diversification": "分析失败",
                "total_amount": 0,
                "message": f"分析失败: {str(e)}"
            }
        })


@analysis_bp.route("/expected-return")
def get_expected_return():
    """Calculate expected return"""
    from src.fetcher import fetch_fund_data
    from src.analyzer import calculate_expected_return
    
    user_id = _get_user_id()

    if user_id:
        holdings = db.get_holdings(user_id)
        holdings = [h for h in holdings if h.get("amount", 0) > 0]
    else:
        holdings = []

    if not holdings:
        return jsonify({"success": False, "error": "暂无持仓", "expected_return": 0})

    codes = [h.get("code") for h in holdings]
    
    # 并行获取基金数据
    funds_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_fund_data, code): code for code in codes}
        for future in as_completed(futures):
            data = future.result()
            if not data.get("error"):
                funds_data.append(data)

    result = calculate_expected_return(holdings, funds_data)
    return jsonify({"success": True, "result": result})
