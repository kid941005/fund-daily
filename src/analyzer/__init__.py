"""
Analysis module for Fund Daily
Handles risk metrics and market sentiment analysis
"""

import logging
from typing import Dict, List
from datetime import datetime

from ..fetcher import (
    fetch_hot_sectors,
    fetch_market_news,
    fetch_commodity_prices,
)

# Import enhanced modules
from .sentiment import get_enhanced_market_sentiment

logger = logging.getLogger(__name__)


# ============== Risk Analysis ==============
def calculate_risk_metrics(month_1: float, month_3: float, year_1: float) -> Dict:
    """
    Calculate risk metrics based on returns
    
    Args:
        month_1: 近1月收益率 (%)
        month_3: 近3月收益率 (%)
        year_1: 近1年收益率 (%)
    
    Returns:
        dict: 风险指标
    """
    def parse_return(val):
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        return float(str(val).replace('%', '').strip()) if val else 0.0
    
    m1 = parse_return(month_1)
    m3 = parse_return(month_3)
    y1 = parse_return(year_1)
    
    # 1. 风险等级评估
    volatility = abs(m3 - m1)
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
    
    # 基于波动性
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
    
    # 2. 年化波动率
    returns = [m1, m3, y1 / 12]
    std_dev = (max(returns) - min(returns)) / 2 if len(returns) > 1 else 0
    
    # 3. 夏普比率（简化版，假设无风险利率 3%）
    risk_free_rate = 3.0
    if std_dev > 0:
        sharpe_ratio = (y1 - risk_free_rate) / (std_dev * 12)
    else:
        sharpe_ratio = 0
    
    # 4. 最大回撤估算
    estimated_max_drawdown = min(volatility * 1.5, 50)
    
    # 5. 收益风险比
    return_ratio = y1 / volatility if volatility > 0 else 0
    
    suggestions = {
        "高风险": "适合风险承受能力强的投资者，建议占比不超过30%",
        "中高风险": "适合追求高收益的投资者，建议占比不超过50%",
        "中等风险": "适合稳健型投资者，建议占比不超过70%",
        "中低风险": "适合保守型投资者，可作为主力持仓"
    }
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "volatility": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "estimated_max_drawdown": round(estimated_max_drawdown, 2),
        "return_ratio": round(return_ratio, 2),
        "suggestion": suggestions.get(risk_level, "请根据自身风险承受能力配置")
    }


# ============== Market Sentiment ==============
def get_commodity_sentiment() -> Dict:
    """
    Analyze commodity price trends
    
    Returns:
        dict: Commodity sentiment analysis
    """
    commodities = fetch_commodity_prices()
    
    if not commodities:
        return {'sentiment': '平稳', 'score': 0, 'details': {}}
    
    score = 0
    total_weight = 0
    details = {}
    
    for name, data in commodities.items():
        change = data.get('change', 0) or 0
        weight = data.get('weight', 0.25)
        
        details[name] = {
            'name': data.get('name', name),
            'code': data.get('code'),
            'price': data.get('price'),
            'change': change,
            'weight': weight
        }
        
        score += change * weight
        total_weight += weight
    
    if total_weight > 0:
        score = score / total_weight
    
    score = max(-50, min(50, score))
    
    if score > 10:
        sentiment = '通胀'
    elif score < -10:
        sentiment = '通缩'
    else:
        sentiment = '平稳'
    
    return {
        'sentiment': sentiment,
        'score': round(score, 2),
        'details': details,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def get_market_sentiment() -> Dict:
    """
    Get market sentiment - now uses enhanced algorithm
    
    Returns:
        dict: Market sentiment (uses enhanced algorithm)
    """
    # Use enhanced sentiment analysis
    return get_enhanced_market_sentiment()


def get_enhanced_sentiment() -> Dict:
    """
    Get enhanced market sentiment with improved algorithm
    
    Returns:
        dict: Enhanced market sentiment analysis
    """
    return get_enhanced_market_sentiment()
    """
    Get market sentiment from multiple sources
    
    Returns:
        dict: Market sentiment analysis
    """
    cache_key = "market_sentiment"
    from ..fetcher import get_cache, set_cache
    
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        # Get sector data
        sectors = fetch_hot_sectors(5)
        
        # Get news
        news = fetch_market_news(5)
        
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
        
        # 大宗商品因素
        commodity = get_commodity_sentiment()
        commodity_score = commodity.get('score', 0)
        
        sector_volatility = abs(avg_change) if sectors else 0
        commodity_weight = min(0.3, 0.1 + sector_volatility * 0.02)
        
        score -= commodity_score * commodity_weight * 10
        
        # 限制范围
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


# ============== Portfolio Analysis ==============
def calculate_expected_return(holdings: List[Dict], funds_data: List[Dict]) -> Dict:
    """
    Calculate expected return based on holdings and sector performance
    
    Args:
        holdings: List of holdings with code, amount, name
        funds_data: List of fund data with code, daily_change
    
    Returns:
        dict: Expected return analysis
    """
    if not holdings or not funds_data:
        return {"error": "暂无持仓数据", "expected_return": 0}
    
    sectors = fetch_hot_sectors(10)
    
    # Sector keywords mapping
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
        
        # Map fund to related sectors
        related_sectors = []
        fund_sector_change = 0
        
        for sector_name, keywords in sector_keywords.items():
            for keyword in keywords:
                if keyword in name:
                    related_sectors.append(sector_name)
                    for s in sectors:
                        if sector_name in s.get('name', ''):
                            fund_sector_change = s.get('change', 0)
                            break
                    break
        
        if not related_sectors:
            related_sectors = ['综合']
            fund_sector_change = fund_change
        
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
    
    return_pct = (expected_return / total_investment * 100) if total_investment > 0 else 0
    
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
