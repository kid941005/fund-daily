#!/usr/bin/env python3
"""
Fund Daily - Daily fund analysis and sharing tool
Fetches fund data, analyzes trends, and generates daily reports
"""

import sys
import json
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timedelta

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_fund_data_eastmoney(fund_code):
    """Fetch fund data from East Money web API"""
    try:
        # East Money web API (more stable)
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
            # Parse JSONP format: jsonpgz({...})
            if content.startswith('jsonpgz('):
                json_str = content[8:-2]  # Remove jsonpgz( and );
                return json.loads(json_str)
            return {"error": "Invalid response format"}
            
    except Exception as e:
        return {"error": str(e)}

def analyze_fund(fund_data):
    """Analyze fund data and generate insights"""
    if "error" in fund_data:
        return {"error": fund_data["error"]}
    
    if not fund_data.get("fundcode"):
        return {"error": "No fund data available"}
    
    # Parse change percentage
    try:
        gszzl = float(fund_data.get("gszzl", 0))
    except:
        gszzl = 0
    
    analysis = {
        "fund_code": fund_data.get("fundcode"),
        "fund_name": fund_data.get("name"),
        "nav": fund_data.get("dwjz"),  # 单位净值
        "estimate_nav": fund_data.get("gsz"),  # 估算净值
        "daily_change": gszzl,  # 估算涨跌幅
        "date": fund_data.get("jzrq"),  # 净值日期
        "estimate_date": fund_data.get("gztime"),  # 估算时间
        
        # Analysis
        "trend": "up" if gszzl > 0 else "down" if gszzl < 0 else "flat",
        "change_percent": f"{gszzl}%",
        
        # Summary
        "summary": generate_summary(fund_data, gszzl)
    }
    
    return analysis

def generate_summary(fund_data, change):
    """Generate text summary"""
    name = fund_data.get("name", "Unknown")
    nav = fund_data.get("dwjz", "N/A")
    
    if change > 3:
        emoji = "🚀"
        desc = "大涨"
    elif change > 1:
        emoji = "📈"
        desc = "上涨"
    elif change > -1:
        emoji = "➖"
        desc = "平盘"
    elif change > -3:
        emoji = "📉"
        desc = "下跌"
    else:
        emoji = "🔻"
        desc = "大跌"
    
    return f"{emoji} {name} 今日{desc} {change}%，净值 {nav}"

def generate_daily_report(fund_codes):
    """Generate daily report for multiple funds"""
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "funds": [],
        "summary": {}
    }
    
    up_count = 0
    down_count = 0
    flat_count = 0
    
    for code in fund_codes:
        data = fetch_fund_data_eastmoney(code.strip())
        analysis = analyze_fund(data)
        
        if "error" not in analysis:
            report["funds"].append(analysis)
            
            if analysis["trend"] == "up":
                up_count += 1
            elif analysis["trend"] == "down":
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

def format_report_for_share(report):
    """Format report for sharing"""
    lines = [
        f"📊 每日基金报告 {report['date']}",
        "=" * 40,
        ""
    ]
    
    for fund in report["funds"]:
        lines.append(fund["summary"])
        lines.append(f"   代码: {fund['fund_code']} | 净值: {fund['nav']}")
        if fund.get('estimate_nav'):
            lines.append(f"   估算: {fund['estimate_nav']} ({fund['change_percent']})")
        lines.append("")
    
    lines.append("=" * 40)
    lines.append(f"📈 上涨: {report['summary']['up']} 只")
    lines.append(f"📉 下跌: {report['summary']['down']} 只")
    lines.append(f"➖ 平盘: {report['summary']['flat']} 只")
    lines.append(f"💡 市场情绪: {report['summary']['market_sentiment']}")
    lines.append("")
    lines.append("⚠️ 仅供参考，不构成投资建议")
    
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("""Usage: fund-daily <command> [options]

Commands:
  fetch <fund_code>           Fetch single fund data
  analyze <fund_code>         Analyze single fund
  report <code1,code2,...>    Generate daily report for multiple funds
  share <code1,code2,...>     Generate shareable report

Examples:
  fund-daily fetch 000001
  fund-daily analyze 000001
  fund-daily report 000001,000002,000003
  fund-daily share 000001,000002
""", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "fetch" and len(sys.argv) > 2:
        result = fetch_fund_data_eastmoney(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "analyze" and len(sys.argv) > 2:
        data = fetch_fund_data_eastmoney(sys.argv[2])
        result = analyze_fund(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "report" and len(sys.argv) > 2:
        codes = sys.argv[2].split(",")
        result = generate_daily_report(codes)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "share" and len(sys.argv) > 2:
        codes = sys.argv[2].split(",")
        report = generate_daily_report(codes)
        result = format_report_for_share(report)
        print(result)
        
    else:
        print("Error: Invalid command or missing arguments", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
