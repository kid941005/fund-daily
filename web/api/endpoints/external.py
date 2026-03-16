"""
外部数据源 API 端点
提供雪球、支付宝、且慢等第三方数据
"""

from flask import Blueprint, jsonify, request
from concurrent.futures import ThreadPoolExecutor

external_bp = Blueprint("external", __name__)


@external_bp.route("/external/hot-rank")
def get_hot_rank():
    """获取雪球热度排行"""
    limit = request.args.get("limit", 20, type=int)
    
    try:
        from src.fetcher.xueqiu import get_fund_hot_rank
        rank_data = get_fund_hot_rank(limit)
        return jsonify({"success": True, "data": rank_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@external_bp.route("/external/fund-hot/<fund_code>")
def get_fund_hot(fund_code):
    """获取单只基金热度"""
    try:
        from src.fetcher.xueqiu import fetch_fund_hot
        hot_data = fetch_fund_hot(fund_code)
        return jsonify({"success": True, "data": hot_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@external_bp.route("/external/fund-discussion/<fund_code>")
def get_fund_discussion(fund_code):
    """获取基金讨论"""
    limit = request.args.get("limit", 5, type=int)
    
    try:
        from src.fetcher.xueqiu import fetch_fund_discussion
        discussions = fetch_fund_discussion(fund_code, limit)
        return jsonify({"success": True, "data": discussions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@external_bp.route("/external/fund-compare", methods=["POST"])
def compare_funds():
    """基金对比"""
    fund_codes = request.json.get("codes", [])
    
    if not fund_codes:
        return jsonify({"success": False, "error": "请提供基金代码"})
    
    try:
        from src.fetcher.alipay import get_fund_compare
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(get_fund_compare, [fund_codes]))
        
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@external_bp.route("/external/portfolios")
def get_portfolios():
    """获取且慢组合列表"""
    try:
        from src.fetcher.qianman import fetch_portfolio_list
        portfolios = fetch_portfolio_list()
        return jsonify({"success": True, "data": portfolios})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@external_bp.route("/external/advisors")
def get_advisors():
    """获取投顾策略"""
    try:
        from src.fetcher.qianman import fetch_fund_advisor
        advisors = fetch_fund_advisor()
        return jsonify({"success": True, "data": advisors})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@external_bp.route("/external/portfolio/<portfolio_id>")
def get_portfolio_detail(portfolio_id):
    """获取组合详情"""
    try:
        from src.fetcher.qianman import fetch_portfolio_detail
        detail = fetch_portfolio_detail(portfolio_id)
        return jsonify({"success": True, "data": detail})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
