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

def fetch_market_hot_news(limit=8):
    """Fetch market hot news from East Money with real links"""
    try:
        # East Money 7x24快讯 API
        url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://stock.eastmoney.com/'
            }
        )
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            content = response.read().decode('utf-8')
            # Parse JSONP: var ajaxResult={...}
            if 'var ajaxResult=' in content:
                json_str = content.split('var ajaxResult=')[1].rstrip(';')
                data = json.loads(json_str)
                
                news_list = []
                for item in data.get('LivesList', [])[:limit]:
                    # Use the real URL from the API
                    url = item.get('url_w', '') or item.get('url_m', '') or item.get('url_unique', '')
                    news_list.append({
                        "title": item.get('title', ''),
                        "time": item.get('showtime', ''),
                        "source": item.get('source', '东方财富'),
                        "summary": item.get('digest', '')[:100] if item.get('digest') else '',
                        "url": url
                    })
                return news_list
    except Exception as e:
        print(f"News fetch error: {e}", file=sys.stderr)
    
    # Fallback - return empty instead of demo data
    return []

def fetch_hot_sectors(limit=10):
    """Fetch hot sectors from East Money"""
    try:
        url = "https://data.eastmoney.com/bkzj/hy.html"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://data.eastmoney.com/'
            }
        )
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Extract sector data from HTML
            import re
            sectors = []
            
            # Try to find sector data in script tags
            pattern = r'var[^=]*=\{?"[^"]*":\s*\[(.*?)\]\}'
            matches = re.findall(pattern, html, re.DOTALL)
            
            # Fallback: use a simpler approach with common sector data
            # Since the page structure is complex, return mock data for demo
            # In production, you'd parse the actual API response
            url2 = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": limit,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:90+t:2",
                "fields": "f1,f2,f3,f4,f12,f13,f14"
            }
            query_string = urllib.parse.urlencode(params)
            url2 = f"{url2}?{query_string}"
            
            req2 = urllib.request.Request(url2, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            with urllib.request.urlopen(req2, context=ctx, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                diff = data.get('data', {}).get('diff', [])
                
                for item in diff:
                    sectors.append({
                        "name": item.get('f14', ''),
                        "change": item.get('f3', 0),
                        "code": item.get('f12', '')
                    })
                return sectors[:limit]
    except Exception as e:
        print(f"Error fetching sectors: {e}", file=sys.stderr)
        return []

def generate_advice(funds):
    """Generate investment advice based on fund performance"""
    if not funds:
        return {"advice": "暂无基金数据", "risk_level": "未知"}
    
    up_count = sum(1 for f in funds if f.get('trend') == 'up')
    down_count = sum(1 for f in funds if f.get('trend') == 'down')
    total = len(funds)
    
    avg_change = sum(f.get('daily_change', 0) for f in funds) / total if total > 0 else 0
    
    # Determine advice
    if up_count > down_count and avg_change > 1:
        advice = "市场表现良好，持有基金多数上涨，建议继续持有"
        risk_level = "稳健"
        action = "持有"
    elif down_count > up_count and avg_change < -1:
        advice = "市场波动较大，部分基金下跌明显，建议关注风险"
        risk_level = "谨慎"
        action = "观望"
    elif avg_change > 0.5:
        advice = "市场温和上涨，可适当关注但避免追高"
        risk_level = "适中"
        action = "持有"
    elif avg_change < -0.5:
        advice = "市场有所回调，可能是低吸机会"
        risk_level = "适中"
        action = "关注"
    else:
        advice = "市场整体平稳，建议保持现有配置"
        risk_level = "稳健"
        action = "持有"
    
    return {
        "advice": advice,
        "risk_level": risk_level,
        "action": action,
        "up_count": up_count,
        "down_count": down_count,
        "avg_change": round(avg_change, 2)
    }

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
        
    elif command == "news" and len(sys.argv) > 2:
        limit = int(sys.argv[2])
        news = fetch_market_hot_news(limit)
        print(json.dumps(news, ensure_ascii=False, indent=2))
        
    elif command == "news":
        news = fetch_market_hot_news(8)
        print(json.dumps(news, ensure_ascii=False, indent=2))
        
    elif command == "sectors" and len(sys.argv) > 2:
        limit = int(sys.argv[2])
        sectors = fetch_hot_sectors(limit)
        print(json.dumps(sectors, ensure_ascii=False, indent=2))
        
    elif command == "sectors":
        sectors = fetch_hot_sectors(10)
        print(json.dumps(sectors, ensure_ascii=False, indent=2))
        
    elif command == "advice":
        # For CLI, use default funds
        funds_data = generate_daily_report(['000001', '110022', '161725'])
        advice = generate_advice(funds_data.get('funds', []))
        print(json.dumps(advice, ensure_ascii=False, indent=2))
        
    else:
        print("Error: Invalid command or missing arguments", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
