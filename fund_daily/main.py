#!/usr/bin/env python3
"""
Fund Daily - Enhanced version with data persistence
"""

import sys
import json
import os
import urllib.request
import ssl
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fund_daily.storage import FundStorage, get_storage

# SSL context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_fund_data_eastmoney(fund_code):
    """Fetch fund data from East Money"""
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
            return {"error": "Invalid response format"}
    except Exception as e:
        return {"error": str(e)}


def analyze_fund(fund_data):
    """Analyze fund data"""
    if "error" in fund_data or not fund_data.get("fundcode"):
        return {"error": fund_data.get("error", "No data available")}
    
    try:
        gszzl = float(fund_data.get("gszzl", 0))
    except:
        gszzl = 0
    
    return {
        "fund_code": fund_data.get("fundcode"),
        "fund_name": fund_data.get("name"),
        "nav": fund_data.get("dwjz"),
        "estimate_nav": fund_data.get("gsz"),
        "daily_change": gszzl,
        "date": fund_data.get("jzrq"),
        "estimate_date": fund_data.get("gztime"),
        "trend": "up" if gszzl > 0 else "down" if gszzl < 0 else "flat",
        "change_percent": f"{gszzl}%"
    }


def fetch_and_save(fund_code, storage=None):
    """获取并保存基金数据"""
    if storage is None:
        storage = get_storage()
    
    # 获取数据
    data = fetch_fund_data_eastmoney(fund_code)
    
    if 'error' in data:
        return {"success": False, "error": data['error']}
    
    # 保存到本地
    storage.save_fund_data(fund_code, data)
    
    # 分析
    analysis = analyze_fund(data)
    analysis['saved'] = True
    
    return analysis


def show_fund_history(fund_code, days=30):
    """显示基金历史"""
    storage = get_storage()
    history = storage.get_fund_history(fund_code, days)
    
    if not history:
        return {"error": "No history data"}
    
    # 格式化输出
    result = {
        "fund_code": fund_code,
        "fund_name": history[-1].get('data', {}).get('name', 'Unknown'),
        "records": len(history),
        "date_range": {
            "start": history[0].get('date'),
            "end": history[-1].get('date')
        },
        "history": []
    }
    
    for record in history:
        data = record.get('data', {})
        result['history'].append({
            "date": record.get('date'),
            "nav": data.get('dwjz'),
            "change": data.get('gszzl')
        })
    
    return result


def show_statistics(fund_code, days=30):
    """显示基金统计"""
    storage = get_storage()
    stats = storage.get_statistics(fund_code, days)
    
    if not stats:
        return {"error": "No statistics available"}
    
    return stats


def list_all_funds():
    """列出所有基金"""
    storage = get_storage()
    funds = storage.get_all_funds()
    
    return {
        "total": len(funds),
        "funds": funds
    }


def generate_report_with_history(fund_codes):
    """生成包含历史数据的报告"""
    storage = get_storage()
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "funds": [],
        "summary": {}
    }
    
    up_count = down_count = flat_count = 0
    
    for code in fund_codes:
        # 获取并保存最新数据
        result = fetch_and_save(code, storage)
        
        if 'error' not in result:
            report["funds"].append(result)
            
            if result.get('trend') == 'up':
                up_count += 1
            elif result.get('trend') == 'down':
                down_count += 1
            else:
                flat_count += 1
    
    report["summary"] = {
        "total": len(report["funds"]),
        "up": up_count,
        "down": down_count,
        "flat": flat_count,
        "market_sentiment": "乐观" if up_count > down_count else "谨慎" if down_count > up_count else "平稳"
    }
    
    return report


def main():
    if len(sys.argv) < 2:
        print("""Usage: fund-daily-enhanced <command> [options]

Commands:
  fetch <code>              获取并保存基金数据
  history <code> [days]     显示历史数据 (默认30天)
  stats <code> [days]       显示统计数据
  list                      列出所有已记录的基金
  report <code1,code2,...>  生成完整报告
  export <code> [path]      导出到CSV

Examples:
  fund-daily-enhanced fetch 000001
  fund-daily-enhanced history 000001 60
  fund-daily-enhanced stats 000001
  fund-daily-enhanced list
  fund-daily-enhanced report 000001,110022
  fund-daily-enhanced export 000001 ./myfund.csv
""", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "fetch" and len(sys.argv) > 2:
        result = fetch_and_save(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "history" and len(sys.argv) > 2:
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        result = show_fund_history(sys.argv[2], days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "stats" and len(sys.argv) > 2:
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        result = show_statistics(sys.argv[2], days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "list":
        result = list_all_funds()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "report" and len(sys.argv) > 2:
        codes = sys.argv[2].split(",")
        result = generate_report_with_history(codes)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "export" and len(sys.argv) > 2:
        storage = get_storage()
        output_path = sys.argv[3] if len(sys.argv) > 3 else None
        success = storage.export_to_csv(sys.argv[2], output_path)
        print(json.dumps({
            "success": success,
            "message": f"Exported to {output_path or sys.argv[2] + '_export.csv'}"
        }, ensure_ascii=False))
        
    else:
        print("Error: Invalid command or missing arguments", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
