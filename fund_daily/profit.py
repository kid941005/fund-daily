#!/usr/bin/env python3
"""
Fund Profit Calculator - 收益计算
计算基金持仓的收益情况
"""

import json
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fund_daily.holdings import get_holdings_manager
from fund_daily.storage import get_storage


def fetch_current_nav(fund_code):
    """获取当前净值"""
    import urllib.request
    import ssl
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js?rt=1463558676006"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://fund.eastmoney.com/'
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            content = response.read().decode('utf-8')
            if content.startswith('jsonpgz('):
                json_str = content[8:-2]
                return json.loads(json_str)
            return None
    except:
        return None


def calculate_profit(holding, current_nav):
    """
    计算单个持仓的收益
    
    Args:
        holding: 持仓信息
        current_nav: 当前估值净值
        
    Returns:
        dict: 收益详情
    """
    shares = holding['shares']
    cost_price = holding['cost_price']
    
    # 计算
    cost = shares * cost_price  # 成本
    current_value = shares * float(current_nav)  # 当前价值
    profit = current_value - cost  # 收益金额
    profit_percent = (profit / cost) * 100 if cost > 0 else 0  # 收益率
    
    return {
        "fund_code": holding['fund_code'],
        "fund_name": holding['fund_name'],
        "shares": shares,
        "cost_price": cost_price,
        "current_nav": current_nav,
        "cost": round(cost, 2),
        "current_value": round(current_value, 2),
        "profit": round(profit, 2),
        "profit_percent": round(profit_percent, 2),
        "trend": "up" if profit > 0 else "down" if profit < 0 else "flat"
    }


def calculate_total_profit(holdings_manager=None, storage=None):
    """
    计算所有持仓的总收益
    
    Args:
        holdings_manager: 持仓管理器
        storage: 数据存储管理器
        
    Returns:
        dict: 总收益详情
    """
    if holdings_manager is None:
        holdings_manager = get_holdings_manager()
    if storage is None:
        storage = get_storage()
    
    # 获取所有持仓
    holdings_data = holdings_manager.list_holdings()
    holdings = holdings_data.get('holdings', [])
    
    if not holdings:
        return {
            "total_holdings": 0,
            "total_cost": 0,
            "total_value": 0,
            "total_profit": 0,
            "profit_percent": 0,
            "holdings": []
        }
    
    results = []
    total_cost = 0
    total_value = 0
    
    for holding in holdings:
        fund_code = holding['fund_code']
        
        # 获取当前净值
        fund_data = fetch_current_nav(fund_code)
        
        if fund_data:
            current_nav = fund_data.get('gsz', holding['cost_price'])
            profit_info = calculate_profit(holding, current_nav)
            results.append(profit_info)
            total_cost += profit_info['cost']
            total_value += profit_info['current_value']
        else:
            # 无法获取数据，使用成本
            profit_info = calculate_profit(holding, holding['cost_price'])
            profit_info['current_nav'] = "N/A"
            profit_info['current_value'] = "N/A"
            profit_info['profit'] = "N/A"
            profit_info['profit_percent'] = "N/A"
            profit_info['trend'] = "unknown"
            results.append(profit_info)
    
    total_profit = total_value - total_cost
    profit_percent = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_holdings": len(holdings),
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_profit": round(total_profit, 2),
        "profit_percent": round(profit_percent, 2),
        "trend": "up" if total_profit > 0 else "down" if total_profit < 0 else "flat",
        "holdings": results
    }


def generate_profit_report():
    """生成收益报告（适合分享到社交媒体）"""
    result = calculate_total_profit()
    
    if result['total_holdings'] == 0:
        return "📊 暂无持仓记录\n请先添加持仓：holdings add <code> <name> <shares> <cost>"
    
    lines = ["📊 基金收益日报"]
    lines.append(f"📅 {result['date']}")
    lines.append("")
    
    # 总收益
    trend_emoji = "📈" if result['trend'] == 'up' else "📉" if result['trend'] == 'down' else "➡️"
    lines.append(f"{trend_emoji} 总收益: ¥{result['total_profit']:,.2f} ({result['profit_percent']:+.2f}%)")
    lines.append(f"💰 总成本: ¥{result['total_cost']:,.2f}")
    lines.append(f"💵 当前价值: ¥{result['total_value']:,.2f}")
    lines.append("")
    
    # 各个基金
    lines.append("📋 持仓明细:")
    for h in result['holdings']:
        code = h['fund_code']
        name = h['fund_name'][:8]
        trend = "🔺" if h.get('trend') == 'up' else "🔻" if h.get('trend') == 'down' else "➡️"
        
        if h.get('profit_percent') == "N/A":
            lines.append(f"  {code} {name} - 数据获取失败")
        else:
            profit = h['profit']
            percent = h['profit_percent']
            lines.append(f"  {trend} {code} {name}: ¥{profit:,.2f} ({percent:+.2f}%)")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        # 默认生成报告
        print(generate_profit_report())
        return
    
    command = sys.argv[1]
    
    if command == "report":
        print(generate_profit_report())
        
    elif command == "json":
        result = calculate_total_profit()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "add" and len(sys.argv) >= 6:
        manager = get_holdings_manager()
        result = manager.add_holding(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "list":
        manager = get_holdings_manager()
        result = manager.list_holdings()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "total":
        result = calculate_total_profit()
        print(f"总收益: ¥{result['total_profit']:,.2f} ({result['profit_percent']:+.2f}%)")
        
    else:
        print("""Usage: profit [command]

Commands:
  profit                  生成收益报告（默认）
  profit report           生成可分享的报告
  profit json            JSON 格式输出
  profit add <code> <name> <shares> <cost>  添加持仓
  profit list            列出持仓
  profit total           显示总收益
""", file=sys.stderr)


if __name__ == '__main__':
    main()
