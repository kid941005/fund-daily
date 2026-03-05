#!/usr/bin/env python3
"""
Fund Daily Advisor - 每日操作建议
基于技术分析和市场趋势生成操作建议
"""

import json
import sys
import os
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fund_daily.storage import get_storage


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
            return None
    except Exception as e:
        return None


def calculate_ma(history, days=5):
    """计算移动平均线"""
    if len(history) < days:
        return None
    
    prices = [float(h.get('data', {}).get('gsz', 0)) for h in history[-days:] if h.get('data', {}).get('gsz')]
    if not prices:
        return None
    
    return sum(prices) / len(prices)


def calculate_volatility(history):
    """计算波动率"""
    if len(history) < 5:
        return 0
    
    changes = []
    for h in history:
        try:
            change = float(h.get('data', {}).get('gszzl', 0))
            changes.append(change)
        except:
            continue
    
    if not changes:
        return 0
    
    # 计算标准差
    avg = sum(changes) / len(changes)
    variance = sum((x - avg) ** 2 for x in changes) / len(changes)
    return variance ** 0.5


def analyze_trend(history):
    """分析趋势"""
    if len(history) < 5:
        return "数据不足"
    
    # 计算近期涨跌
    recent_changes = []
    for h in history[-5:]:
        try:
            change = float(h.get('data', {}).get('gszzl', 0))
            recent_changes.append(change)
        except:
            continue
    
    if not recent_changes:
        return "数据不足"
    
    avg_change = sum(recent_changes) / len(recent_changes)
    
    # 连续上涨/下跌天数
    consecutive_up = 0
    consecutive_down = 0
    for change in reversed(recent_changes):
        if change > 0:
            consecutive_up += 1
        elif change < 0:
            consecutive_down += 1
        else:
            break
    
    # 判断趋势
    if avg_change > 1.5:
        return "强势上涨"
    elif avg_change > 0.5:
        return "上涨趋势"
    elif avg_change > -0.5:
        return "震荡整理"
    elif avg_change > -1.5:
        return "下跌趋势"
    else:
        return "弱势下跌"


def calculate_support_resistance(history):
    """计算支撑位和压力位"""
    if len(history) < 10:
        return None, None
    
    prices = []
    for h in history:
        try:
            price = float(h.get('data', {}).get('gsz', 0))
            if price > 0:
                prices.append(price)
        except:
            continue
    
    if len(prices) < 5:
        return None, None
    
    current_price = prices[-1]
    
    # 压力位：近期最高价
    resistance = max(prices[-5:])
    
    # 支撑位：近期最低价
    support = min(prices[-5:])
    
    return support, resistance


def generate_advisor(fund_code, history=None):
    """
    生成操作建议
    
    分析维度：
    1. 近期趋势（5日涨跌幅）
    2. 波动性（标准差）
    3. 技术形态（连续涨跌）
    4. 支撑/压力位
    5. 市场情绪
    
    返回：
    {
        "code": "000001",
        "name": "基金名称",
        "recommendation": "买入/持有/卖出",
        "confidence": 85,
        "reason": ["原因1", "原因2", ...],
        "risk_level": "中",
        "target_price": 1.15,
        "stop_loss": 1.02
    }
    """
    
    # 获取数据
    if history is None:
        storage = get_storage()
        history = storage.get_fund_history(fund_code, days=30)
    
    if not history:
        # 尝试获取实时数据
        data = fetch_fund_data_eastmoney(fund_code)
        if data:
            return {
                "fund_code": fund_code,
                "fund_name": data.get('name', 'Unknown'),
                "recommendation": "建议观察",
                "confidence": 50,
                "reason": ["暂无历史数据，建议先观察"],
                "risk_level": "未知",
                "note": "需要更多历史数据进行分析"
            }
        return {"error": "无法获取数据"}
    
    # 获取最新数据
    latest = history[-1]
    data = latest.get('data', {})
    fund_name = data.get('name', 'Unknown')
    current_price = float(data.get('gsz', 0))
    daily_change = float(data.get('gszzl', 0))
    
    # 分析各项指标
    trend = analyze_trend(history)
    volatility = calculate_volatility(history)
    
    # 计算均线
    ma5 = calculate_ma(history, 5)
    ma10 = calculate_ma(history, 10) if len(history) >= 10 else None
    
    # 支撑/压力位
    support, resistance = calculate_support_resistance(history)
    
    # 生成建议
    reasons = []
    score = 0  # -100 到 100
    
    # 1. 趋势分析
    if trend in ["强势上涨", "上涨趋势"]:
        score += 20
        reasons.append(f"✓ 近期趋势向好：{trend}")
    elif trend in ["下跌趋势", "弱势下跌"]:
        score -= 20
        reasons.append(f"✗ 近期趋势偏弱：{trend}")
    else:
        reasons.append(f"○ 近期震荡整理")
    
    # 2. 日涨跌幅
    if daily_change > 2:
        score -= 10  # 大涨可能是回调信号
        reasons.append(f"⚠️ 今日涨幅较大({daily_change:.2f}%)，注意短期回调风险")
    elif daily_change > 0:
        score += 5
        reasons.append(f"✓ 今日上涨({daily_change:.2f}%)")
    elif daily_change < -2:
        score += 10  # 大跌可能是机会
        reasons.append(f"✓ 今日跌幅较大({daily_change:.2f}%)，可能存在反弹机会")
    elif daily_change < 0:
        score -= 5
        reasons.append(f"○ 今日下跌({daily_change:.2f}%)")
    
    # 3. 均线判断
    if ma5 and ma10:
        if ma5 > ma10:
            score += 15
            reasons.append(f"✓ 5日均线({ma5:.4f}) > 10日均线({ma10:.4f})，多头排列")
        else:
            score -= 15
            reasons.append(f"✗ 均线呈空头排列")
    
    # 4. 支撑/压力位
    if support and resistance:
        if current_price < support * 1.02:
            score += 15
            reasons.append(f"✓ 接近支撑位({support:.4f})，下跌空间有限")
        elif current_price > resistance * 0.98:
            score -= 15
            reasons.append(f"⚠️ 接近压力位({resistance:.4f})，注意回调风险")
    
    # 5. 波动性
    if volatility > 3:
        reasons.append(f"⚠️ 波动性较高({volatility:.2f}%)，适合激进型投资者")
    elif volatility < 1:
        reasons.append(f"○ 波动性较低({volatility:.2f}%)，适合稳健型投资者")
    
    # 生成最终建议
    if score >= 30:
        recommendation = "建议买入"
        confidence = min(90, 50 + score // 2)
        risk_level = "中"
    elif score >= 10:
        recommendation = "建议持有"
        confidence = min(80, 50 + score // 2)
        risk_level = "中低"
    elif score >= -10:
        recommendation = "建议观望"
        confidence = 60
        risk_level = "中"
    elif score >= -30:
        recommendation = "建议持有"
        confidence = min(70, 50 + score // 2)
        risk_level = "中高"
    else:
        recommendation = "建议卖出/换基"
        confidence = min(85, 50 + score // 2)
        risk_level = "高"
    
    # 计算目标价和止损价
    if current_price > 0:
        if recommendation in ["建议买入", "建议持有"]:
            target_price = current_price * 1.05  # 5% 涨幅目标
            stop_loss = current_price * 0.97     # 3% 止损
        else:
            target_price = current_price * 0.95
            stop_loss = current_price * 1.03
    else:
        target_price = None
        stop_loss = None
    
    return {
        "fund_code": fund_code,
        "fund_name": fund_name,
        "current_price": current_price,
        "daily_change": daily_change,
        "recommendation": recommendation,
        "confidence": confidence,
        "risk_level": risk_level,
        "trend": trend,
        "volatility": round(volatility, 2),
        "support": round(support, 4) if support else None,
        "resistance": round(resistance, 4) if resistance else None,
        "target_price": round(target_price, 4) if target_price else None,
        "stop_loss": round(stop_loss, 4) if stop_loss else None,
        "reason": reasons,
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def format_advisor_report(fund_codes):
    """格式化建议报告（适合分享）"""
    lines = ["📊 基金每日操作建议"]
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    for code in fund_codes:
        result = generate_advisor(code)
        
        if "error" in result:
            lines.append(f"❌ {code}: {result.get('error')}")
            continue
        
        # 图标
        if result['recommendation'] == "建议买入":
            icon = "🟢"
        elif result['recommendation'] == "建议卖出/换基":
            icon = "🔴"
        else:
            icon = "🟡"
        
        lines.append(f"{icon} **{result['fund_name']}** ({code})")
        lines.append(f"   建议: {result['recommendation']} | 置信度: {result['confidence']}%")
        lines.append(f"   现价: {result['current_price']:.4f} | 日涨跌: {result['daily_change']:+.2f}%")
        lines.append(f"   风险: {result['risk_level']} | 趋势: {result['trend']}")
        
        if result.get('support') and result.get('resistance'):
            lines.append(f"   支撑: {result['support']:.4f} | 压力: {result['resistance']:.4f}")
        
        if result.get('target_price'):
            lines.append(f"   目标: {result['target_price']:.4f} | 止损: {result['stop_loss']:.4f}")
        
        # 主要原因（只显示前2条）
        key_reasons = [r for r in result['reason'] if r.startswith('✓') or r.startswith('✗')][:2]
        for r in key_reasons:
            lines.append(f"   {r}")
        
        lines.append("")
    
    # 风险提示
    lines.append("⚠️ 免责声明：以上仅供参考，不构成投资建议")
    lines.append("投资有风险，入市需谨慎")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("""Usage: advisor <command> [options]

Commands:
  advisor <code1,code2,...>    生成操作建议
  advisor json <codes>         JSON 格式输出
  advisor report               使用配置中的基金生成报告

Examples:
  advisor 000001,110022
  advisor json 000001
  advisor report
""", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "json" and len(sys.argv) > 2:
        codes = sys.argv[2].split(',')
        results = [generate_advisor(c.strip()) for c in codes]
        print(json.dumps(results, ensure_ascii=False, indent=2))
        
    elif command == "report":
        # 读取配置文件
        config_path = Path("config/config.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                codes = config.get('default_funds', [])
        else:
            codes = ["000001"]
        
        print(format_advisor_report(codes))
        
    else:
        # 默认生成建议
        codes = command.split(',')
        print(format_advisor_report(codes))


if __name__ == '__main__':
    main()
