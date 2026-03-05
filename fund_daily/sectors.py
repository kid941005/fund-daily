#!/usr/bin/env python3
"""
Market Sectors Analysis - 热门板块分析
获取和分析当日热门板块
"""

import json
import urllib.request
import ssl
from datetime import datetime
from collections import Counter


# SSL context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_hot_sectors(limit=20):
    """
    获取热门板块排行
    
    Args:
        limit: 返回数量
        
    Returns:
        list: 热门板块列表
    """
    # 行业板块 API
    url = f"https://push2.eastmoney.com/api/qt/clist/get?cb=&pn=1&pz={limit}&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f1,f2,f3,f4,f12,f13,f14"
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/'
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)
            
            sectors = []
            for item in data.get('data', {}).get('diff', []):
                sectors.append({
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'price': item.get('f2'),
                    'change_percent': item.get('f3'),
                    'change_amount': item.get('f4')
                })
            
            return sectors
    except Exception as e:
        return {"error": str(e)}


def fetch_concept_sectors(limit=20):
    """获取概念板块排行"""
    # 概念板块 API
    url = f"https://push2.eastmoney.com/api/qt/clist/get?cb=&pn=1&pz={limit}&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:3&fields=f1,f2,f3,f4,f12,f13,f14"
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/'
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)
            
            sectors = []
            for item in data.get('data', {}).get('diff', []):
                sectors.append({
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'price': item.get('f2'),
                    'change_percent': item.get('f3'),
                    'change_amount': item.get('f4')
                })
            
            return sectors
    except Exception as e:
        return {"error": str(e)}


def analyze_sectors():
    """
    综合分析热门板块
    
    Returns:
        dict: 板块分析结果
    """
    # 获取行业板块和概念板块
    industry_sectors = fetch_hot_sectors(30)
    concept_sectors = fetch_concept_sectors(30)
    
    if isinstance(industry_sectors, dict) and 'error' in industry_sectors:
        return industry_sectors
    
    # 分析
    result = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "update_time": datetime.now().strftime("%H:%M:%S"),
        "industry": {
            "hot": [],
            "cold": []
        },
        "concept": {
            "hot": [],
            "cold": []
        },
        "summary": {}
    }
    
    # 行业板块分析
    if isinstance(industry_sectors, list):
        # 涨幅前5
        hot = sorted(industry_sectors, key=lambda x: x.get('change_percent', 0), reverse=True)[:5]
        result['industry']['hot'] = [{
            'name': s['name'],
            'change': s['change_percent']
        } for s in hot if s.get('change_percent', 0) > 0]
        
        # 跌幅前5
        cold = sorted(industry_sectors, key=lambda x: x.get('change_percent', 0))[:5]
        result['industry']['cold'] = [{
            'name': s['name'],
            'change': s['change_percent']
        } for s in cold if s.get('change_percent', 0) < 0]
    
    # 概念板块分析
    if isinstance(concept_sectors, list):
        hot = sorted(concept_sectors, key=lambda x: x.get('change_percent', 0), reverse=True)[:5]
        result['concept']['hot'] = [{
            'name': s['name'],
            'change': s['change_percent']
        } for s in hot if s.get('change_percent', 0) > 0]
        
        cold = sorted(concept_sectors, key=lambda x: x.get('change_percent', 0))[:5]
        result['concept']['cold'] = [{
            'name': s['name'],
            'change': s['change_percent']
        } for s in cold if s.get('change_percent', 0) < 0]
    
    # 总结
    all_changes = [s.get('change_percent', 0) for s in industry_sectors if isinstance(s, dict)]
    if all_changes:
        avg_change = sum(all_changes) / len(all_changes)
        up_count = sum(1 for c in all_changes if c > 0)
        down_count = sum(1 for c in all_changes if c < 0)
        
        result['summary'] = {
            'total_sectors': len(all_changes),
            'up_count': up_count,
            'down_count': down_count,
            'avg_change': round(avg_change, 2),
            'market_sentiment': "偏多" if avg_change > 0.5 else "偏空" if avg_change < -0.5 else "震荡"
        }
    
    return result


def format_sector_report():
    """格式化板块报告"""
    result = analyze_sectors()
    
    if 'error' in result:
        return f"获取板块数据失败: {result['error']}"
    
    lines = ["📊 今日热门板块分析"]
    lines.append(f"📅 {result['date']}")
    lines.append("")
    
    # 市场总结
    summary = result.get('summary', {})
    lines.append("【市场概览】")
    lines.append(f"  板块总数: {summary.get('total_sectors', 0)}")
    lines.append(f"  上涨: {summary.get('up_count', 0)} | 下跌: {summary.get('down_count', 0)}")
    lines.append(f"  平均涨幅: {summary.get('avg_change', 0):+.2f}%")
    lines.append(f"  市场情绪: {summary.get('market_sentiment', '震荡')}")
    lines.append("")
    
    # 行业板块
    lines.append("【行业板块】")
    lines.append("  🔥 涨幅前5:")
    for i, s in enumerate(result['industry'].get('hot', [])[:5], 1):
        lines.append(f"    {i}. {s['name']} {s['change']:+.2f}%")
    
    lines.append("  ❄️ 跌幅前5:")
    for i, s in enumerate(result['industry'].get('cold', [])[:5], 1):
        lines.append(f"    {i}. {s['name']} {s['change']:+.2f}%")
    
    lines.append("")
    
    # 概念板块
    lines.append("【概念板块】")
    lines.append("  🔥 涨幅前5:")
    for i, s in enumerate(result['concept'].get('hot', [])[:5], 1):
        lines.append(f"    {i}. {s['name']} {s['change']:+.2f}%")
    
    lines.append("  ❄️ 跌幅前5:")
    for i, s in enumerate(result['concept'].get('cold', [])[:5], 1):
        lines.append(f"    {i}. {s['name']} {s['change']:+.2f}%")
    
    lines.append("")
    lines.append("⚠️ 数据来源：东方财富")
    
    return "\n".join(lines)


def get_sector_recommendation():
    """获取板块投资建议"""
    result = analyze_sectors()
    
    if 'error' in result:
        return {"error": result['error']}
    
    # 分析热门板块
    hot_industries = result.get('industry', {}).get('hot', [])
    hot_concepts = result.get('concept', {}).get('hot', [])
    
    recommendations = []
    
    # 热门行业建议
    if hot_industries:
        for sector in hot_industries[:3]:
            if sector['change'] > 5:
                recommendations.append({
                    'type': 'hot_industry',
                    'name': sector['name'],
                    'change': sector['change'],
                    'advice': f"板块强势上涨{sector['change']:.1f}%，注意短期回调风险",
                    'risk': 'high'
                })
            elif sector['change'] > 2:
                recommendations.append({
                    'type': 'hot_industry',
                    'name': sector['name'],
                    'change': sector['change'],
                    'advice': f"板块表现强势，可适当关注",
                    'risk': 'medium'
                })
    
    # 概念板块建议
    if hot_concepts:
        for sector in hot_concepts[:3]:
            if sector['change'] > 5:
                recommendations.append({
                    'type': 'hot_concept',
                    'name': sector['name'],
                    'change': sector['change'],
                    'advice': f"概念板块大热，注意追高风险",
                    'risk': 'high'
                })
    
    # 市场情绪建议
    sentiment = result.get('summary', {}).get('market_sentiment', '震荡')
    if sentiment == "偏多":
        recommendations.append({
            'type': 'market',
            'name': '整体市场',
            'advice': '市场情绪偏多，可适当加仓',
            'risk': 'low'
        })
    elif sentiment == "偏空":
        recommendations.append({
            'type': 'market',
            'name': '整体市场',
            'advice': '市场情绪偏空，建议减仓观望',
            'risk': 'high'
        })
    
    return {
        "date": result['date'],
        "recommendations": recommendations
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'json':
        result = analyze_sectors()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_sector_report())
