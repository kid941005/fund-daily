"""
Enhanced risk calculation with real historical data
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try to import numpy for real calculations
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy not installed, using simplified calculations")


# ============== Simplified Risk Calculation (Original) ==============
def calculate_risk_metrics(month_1, month_3, year_1) -> Dict:
    """
    Calculate risk metrics based on returns (simplified version)
    
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


def fetch_historical_nav(fund_code: str, days: int = 365) -> List[Dict]:
    """
    Fetch historical NAV data from East Money
    
    Args:
        fund_code: 6-digit fund code
        days: Number of days to fetch
        
    Returns:
        list: Historical NAV data with date and nav values
    """
    from ..fetcher import _make_request
    
    try:
        # Use East Money historical API
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        content = _make_request(url)
        
        if not content:
            return []
        
        # Extract NAV data from JavaScript
        # Looking for patterns like: var netAssetValue = [...]
        nav_pattern = r'var netAssetValue=\[([^\]]+)\]'
        nav_match = re.search(nav_pattern, content)
        
        date_pattern = r'var accumNav=\[([^\]]+)\]'  
        date_match = re.search(date_pattern, content)
        
        if not nav_match:
            return []
        
        # Parse the arrays
        nav_str = nav_match.group(1)
        
        # Parse JSON-like array
        try:
            # Try to find the array in the content
            data_pattern = r'"(?:nav|share|jzzb)":\s*\[([^\]]+)\]'
            matches = re.findall(data_pattern, content)
            
            nav_data = []
            for match in matches:
                # Parse each entry
                items = re.findall(r'\[([^\]]+)\]', match)
                for item in items:
                    parts = item.split(',')
                    if len(parts) >= 2:
                        try:
                            # Try to extract date and value
                            nav_data.append({
                                'date': parts[0].strip('"'),
                                'nav': float(parts[1])
                            })
                        except Exception:
                            continue
            
            if nav_data:
                return nav_data[-days:] if len(nav_data) > days else nav_data
        except Exception as e:
            logger.debug(f"Parse error: {e}")
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching historical NAV: {e}")
        return []


def calculate_real_risk_metrics(fund_code: str) -> Dict:
    """
    Calculate real risk metrics using historical data
    
    Args:
        fund_code: Fund code
        
    Returns:
        dict: Real risk metrics
    """
    # Fetch 1 year of data
    nav_history = fetch_historical_nav(fund_code, days=365)
    
    if not nav_history or len(nav_history) < 30:
        # Not enough data, use simplified calculation
        return {"error": "Insufficient data", "source": "simplified"}
    
    # Extract NAV values
    navs = [item['nav'] for item in nav_history if 'nav' in item]
    
    if len(navs) < 30:
        return {"error": "Insufficient data", "source": "simplified"}
    
    if HAS_NUMPY:
        # Use numpy for accurate calculations
        returns = np.diff(navs) / np.array(navs[:-1])
        
        # Annual return
        annual_return = np.mean(returns) * 252 * 100
        
        # Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252) * 100
        
        # Sharpe ratio (assuming 3% risk-free rate)
        risk_free_rate = 3.0
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(np.min(drawdown)) * 100
        
    else:
        # Simplified calculation without numpy
        returns = []
        for i in range(1, len(navs)):
            ret = (navs[i] - navs[i-1]) / navs[i-1]
            returns.append(ret)
        
        # Annual return
        annual_return = (sum(returns) / len(returns)) * 252 * 100
        
        # Volatility
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = (variance ** 0.5) * (252 ** 0.5) * 100
        
        # Sharpe ratio
        risk_free_rate = 3.0
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Max drawdown (simplified)
        max_drawdown = 0
        peak = navs[0]
        for nav in navs:
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak * 100
            if dd > max_drawdown:
                max_drawdown = dd
    
    # Determine risk level
    if sharpe_ratio > 1:
        risk_level = "低风险"
        risk_score = 2
    elif sharpe_ratio > 0.5:
        risk_level = "中等风险"
        risk_score = 4
    elif sharpe_ratio > 0:
        risk_level = "中高风险"
        risk_score = 6
    else:
        risk_level = "高风险"
        risk_score = 8
    
    return {
        "source": "historical",
        "data_points": len(navs),
        "annual_return": round(annual_return, 2),
        "volatility": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown": round(max_drawdown, 2),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "suggestion": get_risk_suggestion(risk_level, annual_return)
    }


def get_risk_suggestion(risk_level: str, annual_return: float) -> str:
    """Get investment suggestion based on risk level"""
    suggestions = {
        "低风险": "适合保守型投资者，可作为主力持仓，建议占比50%以上",
        "中等风险": "适合稳健型投资者，建议占比30-50%",
        "中高风险": "适合追求收益的投资者，建议占比20-30%",
        "高风险": "适合风险承受能力强的投资者，建议占比不超过20%"
    }
    
    base = suggestions.get(risk_level, "请根据自身风险承受能力配置")
    
    if annual_return > 20:
        return f"{base} 该基金收益较高，注意锁定部分收益。"
    elif annual_return < 0:
        return f"{base} 该基金目前表现不佳，建议观察或更换。"
    
    return base
