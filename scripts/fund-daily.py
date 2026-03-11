#!/usr/bin/env python3
"""
Fund Daily - Daily fund analysis and sharing tool
Fetches fund data, analyzes trends, and generates daily reports
"""

import sys
import json
import re
import urllib.request
import urllib.error
import ssl
import os
import logging
import time
from datetime import datetime, timedelta

# ============== Logging Setup ==============
def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('fund-daily')

logger = setup_logging()

# ============== SSL Setup ==============
# SSL context - verify certificates by default, disable only if explicitly set
if os.environ.get('FUND_DAILY_SSL_VERIFY', '1') == '0':
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
else:
    ctx = ssl.create_default_context()

# ============== Cache Settings ==============
# Cache duration in seconds (default 5 minutes)
CACHE_DURATION = int(os.environ.get('FUND_DAILY_CACHE_DURATION', 300))

# Simple cache storage
_cache = {}

def get_cache(key):
    """Get value from cache if not expired"""
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            logger.debug(f"Cache hit: {key}")
            return value
        else:
            del _cache[key]
            logger.debug(f"Cache expired: {key}")
    return None

def set_cache(key, value):
    """Set value in cache"""
    _cache[key] = (value, time.time())
    logger.debug(f"Cache set: {key}")

def clear_cache():
    """Clear all cache"""
    global _cache
    _cache = {}
    logger.info("Cache cleared")

def fetch_fund_data_eastmoney(fund_code):
    """Fetch fund data from East Money web API with caching"""
    # Check cache first
    cache_key = f"fund:{fund_code}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        logger.info(f"Fetching fund data: {fund_code}")
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
                result = json.loads(json_str)
                set_cache(cache_key, result)
                return result
            logger.warning(f"Invalid response format for fund {fund_code}")
            return {"error": "Invalid response format"}
            
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP error fetching fund {fund_code}: {e.code} {e.reason}")
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        logger.error(f"Error fetching fund {fund_code}: {str(e)}")
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
    """Fetch market hot news from East Money with caching"""
    # Check cache first
    cache_key = f"news:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        logger.info(f"Fetching market news, limit={limit}")
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
                set_cache(cache_key, news_list)
                return news_list
    except Exception as e:
        logger.error(f"News fetch error: {str(e)}")
    
    # Fallback - return empty instead of demo data
    return []

def fetch_hot_sectors(limit=10):
    """Fetch hot sectors from East Money with caching"""
    # Check cache first
    cache_key = f"sectors:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        logger.info(f"Fetching hot sectors, limit={limit}")
        
        # Use East Money API for sector data
        url = "https://push2.eastmoney.com/api/qt/clist/get"
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
        url = f"{url}?{query_string}"
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            diff = data.get('data', {}).get('diff', [])
            
            sectors = []
            for item in diff:
                sectors.append({
                    "name": item.get('f14', ''),
                    "change": item.get('f3', 0),
                    "code": item.get('f12', '')
                })
            
            set_cache(cache_key, sectors)
            return sectors[:limit]
            
    except Exception as e:
        logger.error(f"Error fetching sectors: {str(e)}")
        return []

def fetch_commodity_prices():
    """Fetch commodity prices via ETFs (gold, silver, energy, copper)
    
    Returns:
        dict: Commodity price data with changes
    """
    cache_key = "commodity_prices"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    
    commodities = {}
    
    # 大宗商品ETF映射：代码 -> (名称, 权重)
    commodity_etfs = {
        'gold': ('518880', '华安黄金ETF', 0.4),      # 黄金 40%
        'silver': ('161226', '白银基金', 0.15),      # 白银 15%
        'energy': ('159867', '能源化工ETF', 0.25),   # 能源 25%
        'copper': ('159997', '有色金属ETF', 0.2),   # 有色 20%
    }
    
    for key, (code, name, weight) in commodity_etfs.items():
        try:
            url = f"https://fundgz.1234567.com.cn/js/{code}.js"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                content = resp.read().decode('utf-8')
                if content.startswith('jsonpgz('):
                    data = json.loads(content[8:-2])
                    change = float(data.get('gszzl', 0) or 0)
                    commodities[key] = {
                        'name': name,
                        'code': code,
                        'price': data.get('gsz'),
                        'change': change,
                        'weight': weight
                    }
        except Exception as e:
            logger.debug(f"Commodity ETF {code} fetch failed: {e}")
    
    set_cache(cache_key, commodities)
    return commodities


def get_commodity_sentiment():
    """Analyze commodity price trends
    
    Returns:
        dict: {
            'sentiment': '通胀'/'通缩'/'平稳',
            'score': -50 to 50,
            'details': {...}
        }
    """
    commodities = fetch_commodity_prices()
    
    if not commodities:
        return {'sentiment': '平稳', 'score': 0, 'details': {}}
    
    # 计算加权得分：大宗商品涨价→通胀预期→利空股市
    score = 0
    total_weight = 0
    details = {}
    
    for name, data in commodities.items():
        change = data.get('change', 0) or 0
        weight = data.get('weight', 0.25)  # 默认权重
        details[name] = {
            'name': data.get('name', name),
            'code': data.get('code'),
            'price': data.get('price'),
            'change': change,
            'weight': weight
        }
        # 涨价为正，通胀预期增强
        score += change * weight
        total_weight += weight
    
    # 归一化
    if total_weight > 0:
        score = score / total_weight
    
    # 限制得分范围
    score = max(-50, min(50, score))
    
    # 判断情绪
    if score > 10:
        sentiment = '通胀'  # 大宗商品普涨，通胀预期强
    elif score < -10:
        sentiment = '通缩'  # 大宗商品普跌，需求疲软
    else:
        sentiment = '平稳'
    
    return {
        'sentiment': sentiment,
        'score': round(score, 2),
        'details': details,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def get_market_sentiment():
    """Get market sentiment from multiple sources
    
    Returns:
        dict: {
            'sentiment': '乐观'/'谨慎'/'恐慌'/'平稳',
            'score': -100 to 100,
            'indicators': {...}
        }
    """
    # Check cache first
    cache_key = "market_sentiment"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        # Get sector data
        sectors = fetch_hot_sectors(5)
        
        # Get news sentiment (简单分析)
        news = fetch_market_hot_news(5)
        
        # 分析涨跌幅
        up_count = sum(1 for s in sectors if s.get('change', 0) > 0)
        down_count = sum(1 for s in sectors if s.get('change', 0) < 0)
        
        # 计算市场得分
        score = 0
        
        # 板块涨跌
        if sectors:
            avg_change = sum(s.get('change', 0) for s in sectors) / len(sectors)
            score += avg_change * 10
        
        # 上涨/下跌板块比例
        if up_count > down_count * 2:
            score += 20
        elif down_count > up_count * 2:
            score -= 20
        
        # 关键词情绪分析
        fear_words = ['跌', '跌停', '恐慌', '暴跌', '大跌', '跳水', '利空']
        hope_words = ['涨', '涨停', '利好', '暴涨', '大涨', '反弹', '突破']
        
        fear_count = sum(1 for n in news for w in fear_words if w in n.get('title', ''))
        hope_count = sum(1 for n in news for w in hope_words if w in n.get('title', ''))
        
        score += hope_count * 10
        score -= fear_count * 10
        
        # 大宗商品因素 (通胀/通缩影响)
        # 大宗商品涨价 → 通胀预期 → 货币政策收紧预期 → 利空股市
        commodity = get_commodity_sentiment()
        commodity_score = commodity.get('score', 0)
        
        # 大宗商品权重：根据市场波动调整
        # 当板块波动大时，大宗商品影响力增强
        sector_volatility = abs(avg_change) if sectors else 0
        commodity_weight = min(0.3, 0.1 + sector_volatility * 0.02)  # 10%-30%权重
        
        score -= commodity_score * commodity_weight * 10  # 通胀利空股市
        
        # 限制在 -100 到 100
        score = max(-100, min(100, score))
        
        # 确定情绪
        if score > 30:
            sentiment = "乐观"
        elif score > 10:
            sentiment = "偏多"
        elif score > -10:
            sentiment = "平稳"
        elif score > -30:
            sentiment = "偏空"
        else:
            sentiment = "恐慌"
        
        result = {
            'sentiment': sentiment,
            'score': score,
            'sector_up': up_count,
            'sector_down': down_count,
            'sector_total': len(sectors),
            'news_hope': hope_count,
            'news_fear': fear_count,
            'commodity_sentiment': commodity.get('sentiment', '平稳'),
            'commodity_score': commodity_score,
            'commodity_details': commodity.get('details', {}),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        set_cache(cache_key, result)
        return result
        
    except Exception as e:
        logger.error(f"Error getting market sentiment: {str(e)}")
        return {'sentiment': '平稳', 'score': 0, 'error': str(e)}

def calculate_expected_return(holdings, funds_data):
    """Calculate expected return based on holdings and sector performance
    
    Args:
        holdings: List of holdings with code, amount, name
        funds_data: List of fund data with code, daily_change
    
    Returns:
        dict: Expected return analysis
    """
    if not holdings or not funds_data:
        return {"error": "暂无持仓数据", "expected_return": 0}
    
    # Get sector data
    sectors = fetch_hot_sectors(10)
    
    # Sector keywords mapping to fund types
    sector_keywords = {
        '新能源': ['新能源', '光伏', '锂电', '电池', '电力', '储能', '氢能'],
        '消费': ['消费', '食品', '饮料', '白酒', '家电', '纺织', '零售'],
        '医药': ['医药', '医疗', '生物', '中药', '疫苗', '医疗器械'],
        '科技': ['科技', '半导体', '芯片', '电子', '计算机', '软件', '互联网'],
        '金融': ['金融', '银行', '保险', '证券', '地产'],
        '军工': ['军工', '航天', '航空', '国防'],
        '材料': ['材料', '化工', '钢铁', '有色', '建材'],
        '基建': ['基建', '工程', '建筑', '工程机械'],
    }
    
    # Calculate expected return
    total_investment = 0
    expected_return = 0
    holdings_analysis = []
    
    for h in holdings:
        code = h.get('code')
        amount = h.get('amount', 0)
        name = h.get('name', '')
        
        if amount <= 0:
            continue
        
        total_investment += amount
        
        # Find fund's daily change
        fund_change = 0
        for f in funds_data:
            if f.get('fund_code') == code:
                fund_change = f.get('daily_change', 0)
                break
        
        # Map fund to related sectors based on name
        related_sectors = []
        fund_sector_change = 0
        
        for sector_name, keywords in sector_keywords.items():
            for keyword in keywords:
                if keyword in name:
                    related_sectors.append(sector_name)
                    # Find sector change
                    for s in sectors:
                        if sector_name in s.get('name', ''):
                            fund_sector_change = s.get('change', 0)
                            break
                    break
        
        # If no sector match found, use fund's own change
        if not related_sectors:
            related_sectors = ['综合']
            fund_sector_change = fund_change
        
        # Calculate expected return for this holding
        # Weight: 70% fund's own change + 30% related sector change
        expected = amount * (fund_change * 0.7 + fund_sector_change * 0.3) / 100
        expected_return += expected
        
        holdings_analysis.append({
            'code': code,
            'name': name,
            'amount': amount,
            'fund_change': fund_change,
            'related_sectors': related_sectors,
            'sector_change': fund_sector_change,
            'expected_return': round(expected, 2)
        })
    
    # Calculate return percentage
    return_pct = (expected_return / total_investment * 100) if total_investment > 0 else 0
    
    # Get top performing sectors
    top_sectors = sorted(sectors, key=lambda x: x.get('change', 0), reverse=True)[:3]
    
    return {
        'total_investment': round(total_investment, 2),
        'expected_return': round(expected_return, 2),
        'return_percentage': round(return_pct, 2),
        'holdings_analysis': holdings_analysis,
        'top_sectors': [
            {'name': s.get('name', ''), 'change': s.get('change', 0)} 
            for s in top_sectors
        ],
        'market_sentiment': get_market_sentiment().get('sentiment', '平稳')
    }

def generate_advice(funds):
    """Generate investment advice based on fund performance and market indicators"""
    if not funds:
        return {"advice": "暂无基金数据", "risk_level": "未知", "action": "观望"}
    
    # 基础统计
    up_count = sum(1 for f in funds if f.get('trend') == 'up')
    down_count = sum(1 for f in funds if f.get('trend') == 'down')
    total = len(funds)
    
    avg_change = sum(f.get('daily_change', 0) for f in funds) / total if total > 0 else 0
    
    # 获取市场情绪
    market = get_market_sentiment()
    market_sentiment = market.get('sentiment', '平稳')
    market_score = market.get('score', 0)
    
    # 计算组合加权指标 - 尝试获取详细数据
    total_sharpe = 0
    total_drawdown = 0
    total_risk_score = 0
    funds_with_risk = 0
    
    for f in funds:
        # 尝试从详细数据获取风险指标
        code = f.get('fund_code')
        if code:
            try:
                detail = get_fund_detail_info(code)
                risk = detail.get('risk_metrics', {})
                if risk:
                    total_sharpe += risk.get('sharpe_ratio', 0)
                    total_drawdown += risk.get('estimated_max_drawdown', 0)
                    total_risk_score += risk.get('risk_score', 4)
                    funds_with_risk += 1
            except:
                pass
    
    # 如果没有详细数据，使用默认值
    if funds_with_risk > 0:
        avg_sharpe = total_sharpe / funds_with_risk
        avg_drawdown = total_drawdown / funds_with_risk
        avg_risk = total_risk_score / funds_with_risk
    else:
        avg_sharpe = 0
        avg_drawdown = 0
        avg_risk = 4
    
    # 估算回撤天数（简化：根据近1月波动）
    # 波动大可能回撤天数多
    drawdown_days = int(avg_drawdown * 2) if avg_drawdown > 0 else 0
    drawdown_days = min(drawdown_days, 30)  # 最多30天
    
    # ========== 新增：计算总仓位和平均收益率 ==========
    total_amount = sum(f.get('amount', 0) for f in funds)
    total_value = sum(f.get('total_value', f.get('amount', 0)) for f in funds)
    
    # 估算平均收益率（简化计算：假设成本=持仓金额*0.8）
    total_cost = sum(f.get('amount', 0) * 0.8 for f in funds)
    avg_profit_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    
    # 计算持仓占比（简化：假设总资产100万）
    total_assets = 1000000  # 可配置
    position_ratio = (total_value / total_assets * 100) if total_assets > 0 else 0
    
    # 综合评分
    score = 0
    
    # 市场情绪权重
    if market_sentiment in ['乐观', '偏多']:
        score += 30
    elif market_sentiment == '平稳':
        score += 10
    elif market_sentiment in ['偏空', '恐慌']:
        score -= 30
    
    # 基金当日表现
    score += avg_change * 10
    
    # 夏普比率（越大越好）
    if avg_sharpe > 1:
        score += 20
    elif avg_sharpe > 0.5:
        score += 10
    elif avg_sharpe < 0:
        score -= 15
    
    # 最大回撤（越大越危险）
    if avg_drawdown > 20:
        score -= 20
    elif avg_drawdown > 10:
        score -= 10
    elif avg_drawdown < 5:
        score += 10
    
    # 确定操作建议
    if score > 40:
        advice = "市场情绪乐观，基金表现良好，适合适度加仓"
        action = "买入"
    elif score > 20:
        advice = "市场偏多，建议继续持有，可少量加仓"
        action = "持有"
    elif score > -10:
        advice = "市场整体平稳，建议保持当前配置"
        action = "持有"
    elif score > -30:
        advice = "市场偏谨慎，注意风险，可适当减仓"
        action = "减仓"
    else:
        advice = "市场情绪偏空，建议减仓观望，等待机会"
        action = "卖出"
    
    # ========== 新增：边界条件判断 ==========
    # 1. 仓位判断
    if position_ratio >= 90 and action == "买入":
        action = "持有"
        advice = f"⚠️ 当前仓位约{position_ratio:.0f}%已较高，建议持有为主"
    elif position_ratio >= 70 and action == "买入":
        advice += "（仓位较高，请谨慎加仓）"
    
    # 2. 收益率判断
    if avg_profit_pct < -30:
        action = "减仓/止损"
        advice = f"⚠️ 平均亏损{abs(avg_profit_pct):.1f}%，建议止损或减仓"
    elif avg_profit_pct < -15:
        if action == "买入":
            action = "持有"
            advice = f"亏损{abs(avg_profit_pct):.1f}%，建议轻仓摊低成本"
    elif avg_profit_pct > 30:
        if action == "持有":
            advice += "（收益较高，可考虑部分止盈）"
    
    # 3. 风险等级
    if avg_risk >= 7:
        risk_level = "高风险"
    elif avg_risk >= 5:
        risk_level = "中高风险"
    elif avg_risk >= 3:
        risk_level = "中等风险"
    else:
        risk_level = "中低风险"
    
    # 4. 高风险提示
    if avg_risk >= 7 and action in ["买入", "持有"]:
        advice += "（⚠️ 组合风险较高）"
    
    # 获取大宗商品信息
    commodity = get_commodity_sentiment()
    
    # 构建大宗商品描述
    commodity_info = []
    for name, data in commodity.get('details', {}).items():
        change = data.get('change', 0) or 0
        price = data.get('price', 'N/A')
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        commodity_info.append(f"{emoji}{data.get('name', name)}: {change:+.2f}%")
    
    commodity_desc = " | ".join(commodity_info) if commodity_info else "暂无"
    
    return {
        "advice": advice,
        "risk_level": risk_level,
        "action": action,
        "up_count": up_count,
        "down_count": down_count,
        "avg_change": round(avg_change, 2),
        "market_sentiment": market_sentiment,
        "market_score": market_score,
        "commodity_sentiment": commodity.get('sentiment', '平稳'),
        "commodity_score": commodity.get('score', 0),
        "commodity_details": commodity.get('details', {}),
        "commodity_desc": commodity_desc,
        "sharpe_ratio": round(avg_sharpe, 2),
        "max_drawdown": round(avg_drawdown, 2),
        "drawdown_days": drawdown_days,
        "risk_score": round(avg_risk, 1),
        # 新增字段
        "position_ratio": round(position_ratio, 1),
        "avg_profit_pct": round(avg_profit_pct, 1),
        "total_value": round(total_value, 2)
    }

def get_fund_detail_info(code):
    """Get detailed fund information including history and risk metrics"""
    try:
        # Fetch basic data
        fund_data = fetch_fund_data_eastmoney(code)
        
        # Fetch detailed data from East Money
        url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            content = response.read().decode('utf-8')
            
            # Extract metrics
            
            #收益率
            syl_1n = re.search(r'syl_1n="([^"]+)"', content)
            syl_6y = re.search(r'syl_6y="([^"]+)"', content)
            syl_3y = re.search(r'syl_3y="([^"]+)"', content)
            syl_1y = re.search(r'syl_1y="([^"]+)"', content)
            syl_1z = re.search(r'syl_1z="([^"]+)"', content)  # 近1周
            syl_2z = re.search(r'syl_2z="([^"]+)"', content)  # 近2周
            syl_5z = re.search(r'syl_5z="([^"]+)"', content)  # 近5周
            syl_10z = re.search(r'syl_10z="([^"]+)"', content)  # 近10周
            
            # 净值数据
            dwjz = re.search(r'dwjz="([^"]+)"', content)  # 单位净值
            ljjz = re.search(r'ljjz="([^"]+)"', content)  # 累计净值
            fund_sourceRate = re.search(r'fund_sourceRate="([^"]+)"', content)  # 原费率
            fund_Rate = re.search(r'fund_Rate="([^"]+)"', content)  # 现费率
            
        # 构建返回数据
        result = {
            "fund_code": code,
            "fund_name": fund_data.get("name", ""),
            "nav": fund_data.get("dwjz"),  # 单位净值
            "acc_nav": ljjz.group(1) if ljjz else None,  # 累计净值
            "estimate_nav": fund_data.get("gsz"),  # 估算净值
            "daily_change": fund_data.get("gszzl"),  # 今日涨跌
            "date": fund_data.get("jzrq"),  # 净值日期
            
            # 收益率
            "return_1w": syl_1z.group(1) if syl_1z else None,  # 近1周
            "return_2w": syl_2z.group(1) if syl_2z else None,  # 近2周
            "return_1m": syl_1y.group(1) if syl_1y else None,  # 近1月
            "return_3m": syl_3y.group(1) if syl_3y else None,  # 近3月
            "return_6m": syl_6y.group(1) if syl_6y else None,  # 近6月
            "return_1y": syl_1n.group(1) if syl_1n else None,  # 近1年
            "return_10z": syl_10z.group(1) if syl_10z else None,  # 近10周
            
            # 费率
            "fee_rate": fund_Rate.group(1) if fund_Rate else None,
            "source_rate": fund_sourceRate.group(1) if fund_sourceRate else None,
            
            # 计算风险指标
            "risk_metrics": calculate_risk_metrics(
                float(syl_1y.group(1)) if syl_1y and syl_1y.group(1) else 0,
                float(syl_3y.group(1)) if syl_3y and syl_3y.group(1) else 0,
                float(syl_1n.group(1)) if syl_1n and syl_1n.group(1) else 0
            )
        }
        
        return result
        
    except Exception as e:
        return {"error": str(e), "fund_code": code}

def calculate_risk_metrics(month_1, month_3, year_1):
    """Calculate risk metrics based on returns
    
    Args:
        month_1: 近1月收益率 (%)
        month_3: 近3月收益率 (%)
        year_1: 近1年收益率 (%)
    
    Returns:
        dict: 风险指标
    """
    # 解析输入（处理字符串如 "3.21%" 或 None）
    def parse_return(val):
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        # 去除 % 符号
        return float(str(val).replace('%', '').strip()) if val else 0.0
    
    m1 = parse_return(month_1)
    m3 = parse_return(month_3)
    y1 = parse_return(year_1)
    
    # 1. 风险等级评估 - 综合考虑收益和波动
    # 使用年化收益和波动幅度综合判断
    volatility = abs(m3 - m1)  # 近1月vs近3月的差异作为波动指标
    risk_score = 0
    
    # 基于年化收益
    if y1 > 30:
        risk_score += 4
    elif y1 > 15:
        risk_score += 3
    elif y1 > 5:
        risk_score += 2
    else:
        risk_score += 1
    
    # 基于波动性（波动越大风险越高）
    if volatility > 15:
        risk_score += 4
    elif volatility > 10:
        risk_score += 3
    elif volatility > 5:
        risk_score += 2
    else:
        risk_score += 1
    
    # 确定风险等级
    if risk_score >= 7:
        risk_level = "高风险"
    elif risk_score >= 5:
        risk_level = "中高风险"
    elif risk_score >= 3:
        risk_level = "中等风险"
    else:
        risk_level = "中低风险"
    
    # 2. 年化波动率（简化估算）
    # 使用不同周期收益率的标准差估算
    returns = [m1, m3, y1 / 12]  # 将年化转为月化
    std_dev = (max(returns) - min(returns)) / 2 if len(returns) > 1 else 0
    
    # 3. 夏普比率（简化版，假设无风险利率 3%）
    risk_free_rate = 3.0
    if std_dev > 0:
        sharpe_ratio = (y1 - risk_free_rate) / (std_dev * 12)  # 年化
    else:
        sharpe_ratio = 0
    
    # 4. 最大回撤估算（基于波动性的简化估算）
    # 波动越大，可能回撤越大
    estimated_max_drawdown = min(volatility * 1.5, 50)  # 估算上限50%
    
    # 5. 收益风险比
    return_ratio = y1 / volatility if volatility > 0 else 0
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "volatility": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "estimated_max_drawdown": round(estimated_max_drawdown, 2),
        "return_ratio": round(return_ratio, 2),
        "suggestion": get_risk_suggestion(risk_level, y1)
    }

def get_risk_suggestion(risk_level, year_return):
    """Get investment suggestion based on risk level"""
    suggestions = {
        "高风险": "适合风险承受能力强的投资者，建议占比不超过30%",
        "中高风险": "适合追求高收益的投资者，建议占比不超过50%",
        "中等风险": "适合稳健型投资者，建议占比不超过70%",
        "中低风险": "适合保守型投资者，可作为主力持仓"
    }
    return suggestions.get(risk_level, "请根据自身风险承受能力配置")

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
        
    elif command == "detail" and len(sys.argv) > 2:
        code = sys.argv[2]
        detail = get_fund_detail_info(code)
        print(json.dumps(detail, ensure_ascii=False, indent=2))
        
    else:
        print("Error: Invalid command or missing arguments", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
