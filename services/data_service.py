"""
数据服务模块
处理基金数据的获取、缓存、分析
"""
import os
import sys
import json
import logging
import urllib.request
import urllib.parse
import ssl
import hashlib
import time

logger = logging.getLogger(__name__)

# 缓存配置
CACHE = {}
CACHE_DURATION = int(os.environ.get('FUND_DAILY_CACHE_DURATION', 300))

# SSL上下文
ctx = ssl.create_default_context()
ctx.check_hostname = os.environ.get('FUND_DAILY_SSL_VERIFY', '1') == '1'

def get_cache(key):
    """获取缓存"""
    if key in CACHE:
        cached_time, cached_value = CACHE[key]
        if time.time() - cached_time < CACHE_DURATION:
            return cached_value
    return None

def set_cache(key, value):
    """设置缓存"""
    CACHE[key] = (time.time(), value)

def fetch_fund_data_eastmoney(fund_code):
    """从东方财富获取基金数据"""
    cache_key = f"fund:{fund_code}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    try:
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            content = resp.read().decode('utf-8')
            
            # 解析数据
            data = {'code': fund_code}
            
            # 提取关键数据
            if "fundName" in content:
                import re
                name_match = re.search(r'fundName\s*=\s*"([^"]+)"', content)
                if name_match:
                    data['name'] = name_match.group(1)
            
            set_cache(cache_key, data)
            return data
            
    except Exception as e:
        logger.error(f"获取基金数据失败 {fund_code}: {e}")
        return {'code': fund_code, 'name': '未知'}

def analyze_fund(fund_data):
    """分析基金"""
    return {
        'code': fund_data.get('code'),
        'name': fund_data.get('name', '未知'),
        'analyzed': True
    }

def generate_summary(fund_data, change):
    """生成基金摘要"""
    trend = "📈 上涨" if change > 0 else "📉 下跌"
    return f"{trend} {fund_data.get('name', '')} {change:+.2f}%"
