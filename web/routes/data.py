"""
数据蓝图
处理基金、新闻、板块等数据
"""
from flask import Blueprint, jsonify

data_bp = Blueprint('data', __name__, url_prefix='/api')

@data_bp.route('/funds')
def get_funds():
    """获取默认基金列表"""
    import os
    codes = os.environ.get('FUND_CODES', '000001,110022,161725').split(',')
    funds_data = []
    
    from services.data_service import fetch_fund_data_eastmoney
    for code in codes:
        code = code.strip()
        if code:
            data = fetch_fund_data_eastmoney(code)
            if data:
                funds_data.append(data)
    
    return jsonify({
        "success": True,
        "funds": funds_data
    })

@data_bp.route('/fund/<code>')
def get_fund(code):
    """获取单只基金数据"""
    from services.data_service import fetch_fund_data_eastmoney
    data = fetch_fund_data_eastmoney(code)
    return jsonify({
        "success": True,
        "fund": data
    })

@data_bp.route('/news')
def get_news():
    """获取市场热点新闻"""
    from scripts.fund_daily import fetch_market_hot_news
    limit = int(request.args.get('limit', 8))
    news = fetch_market_hot_news(limit)
    return jsonify({
        "success": True,
        "news": news
    })

@data_bp.route('/sectors')
def get_sectors():
    """获取热门板块"""
    from scripts.fund_daily import fetch_hot_sectors
    limit = int(request.args.get('limit', 10))
    sectors = fetch_hot_sectors(limit)
    return jsonify({
        "success": True,
        "sectors": sectors
    })

@data_bp.route('/advice')
def get_advice():
    """获取操作建议"""
    from scripts.fund_daily import generate_advice
    from db import database as db
    
    user_id = session.get('user_id')
    if user_id:
        holdings = db.get_holdings(user_id)
    else:
        holdings = []
    
    if not holdings:
        return jsonify({
            "success": False,
            "error": "请先添加持仓"
        })
    
    # 获取基金数据
    funds_data = {}
    from services.data_service import fetch_fund_data_eastmoney
    for h in holdings:
        code = h.get('code')
        data = fetch_fund_data_eastmoney(code)
        if data:
            funds_data[code] = data
    
    advice = generate_advice(funds_data)
    
    return jsonify({
        "success": True,
        "advice": advice
    })

@data_bp.route('/fund-detail/<code>')
def get_fund_detail(code):
    """获取基金详情"""
    from scripts.fund_daily import get_fund_detail_info
    detail = get_fund_detail_info(code)
    return jsonify({
        "success": True,
        "detail": detail
    })

@data_bp.route('/expected-return', methods=['POST'])
def get_expected_return():
    """计算预期收益"""
    from scripts.fund_daily import calculate_expected_return
    data = request.json
    holdings = data.get('holdings', [])
    
    result = calculate_expected_return(holdings, {})
    
    return jsonify({
        "success": True,
        "result": result
    })

@data_bp.route('/portfolio-analysis')
def get_portfolio_analysis():
    """获取组合分析"""
    from scripts.fund_daily import calculate_risk_metrics, get_market_sentiment
    from db import database as db
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"})
    
    holdings = db.get_holdings(user_id)
    if not holdings:
        return jsonify({"success": False, "error": "暂无持仓数据"})
    
    # 获取市场数据
    funds_data = {}
    from services.data_service import fetch_fund_data_eastmoney
    for h in holdings:
        code = h.get('code')
        data = fetch_fund_data_eastmoney(code)
        if data:
            funds_data[code] = data
    
    # 计算风险指标
    month_1 = []
    month_3 = []
    month_6 = []
    
    risk = calculate_risk_metrics(month_1, month_3, month_6)
    sentiment = get_market_sentiment()
    
    return jsonify({
        "success": True,
        "holdings": holdings,
        "risk": risk,
        "sentiment": sentiment
    })
