#!/usr/bin/env python3
"""
Fund Chart Generator - 图表生成
生成基金走势图表
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fund_daily.storage import get_storage


def generate_trend_chart(fund_code, days=30, output_path=None):
    """
    生成基金净值走势图表
    
    Args:
        fund_code: 基金代码
        days: 显示天数
        output_path: 输出路径
        
    Returns:
        str: 图表文件路径或错误信息
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        return {"error": "请安装 matplotlib: pip install matplotlib"}
    
    storage = get_storage()
    history = storage.get_fund_history(fund_code, days)
    
    if not history:
        return {"error": f"暂无 {fund_code} 的历史数据"}
    
    # 准备数据
    dates = []
    navs = []
    changes = []
    
    for record in history:
        date_str = record.get('date', '')
        data = record.get('data', {})
        
        try:
            dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            nav = float(data.get('gsz', 0))
            change = float(data.get('gszzl', 0))
            navs.append(nav)
            changes.append(change)
        except:
            continue
    
    if not dates:
        return {"error": "数据格式错误"}
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), height_ratios=[2, 1])
    fig.suptitle(f'{fund_code} 基金走势 ({days}天)', fontsize=14, fontweight='bold')
    
    # 上图：净值走势
    ax1.plot(dates, navs, marker='o', linewidth=2, markersize=4, color='#2196F3')
    ax1.fill_between(dates, navs, alpha=0.3, color='#2196F3')
    ax1.set_ylabel('估算净值', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # 添加最高/最低标记
    max_idx = navs.index(max(navs))
    min_idx = navs.index(min(navs))
    ax1.scatter([dates[max_idx]], [navs[max_idx]], color='red', s=100, zorder=5, label=f'最高: {navs[max_idx]:.4f}')
    ax1.scatter([dates[min_idx]], [navs[min_idx]], color='green', s=100, zorder=5, label=f'最低: {navs[min_idx]:.4f}')
    ax1.legend(loc='upper left')
    
    # 下图：涨跌幅
    colors = ['#4CAF50' if c >= 0 else '#F44336' for c in changes]
    ax2.bar(dates, changes, color=colors, alpha=0.7, width=0.8)
    ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    ax2.set_ylabel('涨跌幅(%)', fontsize=10)
    ax2.set_xlabel('日期', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # 设置x轴日期倾斜
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # 保存
    if output_path is None:
        output_path = f"data/charts/{fund_code}_trend_{days}d.png"
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return {"success": True, "path": output_path}


def generate_comparison_chart(fund_codes, days=30, output_path=None):
    """生成多基金对比图表"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        return {"error": "请安装 matplotlib: pip install matplotlib"}
    
    storage = get_storage()
    
    # 获取所有基金数据
    fund_data = {}
    for code in fund_codes:
        history = storage.get_fund_history(code, days)
        if history:
            # 归一化到起始值 = 100
            first_nav = float(history[0].get('data', {}).get('gsz', 1))
            if first_nav > 0:
                normalized = [(float(h.get('data', {}).get('gsz', 0)) / first_nav) * 100 for h in history]
                dates = [datetime.strptime(h.get('date', ''), "%Y-%m-%d") for h in history if h.get('date')]
                fund_data[code] = {'dates': dates, 'values': normalized}
    
    if not fund_data:
        return {"error": "暂无数据"}
    
    # 创建图表
    plt.figure(figsize=(12, 6))
    
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0']
    for i, (code, data) in enumerate(fund_data.items()):
        plt.plot(data['dates'], data['values'], 
                marker='o', linewidth=2, markersize=3,
                color=colors[i % len(colors)], 
                label=code)
    
    plt.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.title(f'基金对比走势 (基准=100)', fontsize=14, fontweight='bold')
    plt.xlabel('日期', fontsize=10)
    plt.ylabel('相对净值', fontsize=10)
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # 保存
    if output_path is None:
        output_path = f"data/charts/comparison.png"
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return {"success": True, "path": output_path}


def generate_profit_pie_chart(holdings_data, output_path=None):
    """生成持仓占比饼图"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return {"error": "请安装 matplotlib"}
    
    if not holdings_data or not holdings_data.get('holdings'):
        return {"error": "暂无持仓数据"}
    
    # 准备数据
    labels = []
    sizes = []
    
    for h in holdings_data.get('holdings', []):
        name = h.get('fund_name', h.get('fund_code', ''))[:8]
        cost = h.get('cost', 0)
        if cost > 0:
            labels.append(f"{h.get('fund_code')} {name}")
            sizes.append(cost)
    
    if not sizes:
        return {"error": "无有效数据"}
    
    # 创建饼图
    plt.figure(figsize=(8, 8))
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4']
    
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', 
            colors=colors[:len(sizes)], startangle=90)
    plt.title('基金持仓占比', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # 保存
    if output_path is None:
        output_path = f"data/charts/holdings_pie.png"
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return {"success": True, "path": output_path}


def main():
    if len(sys.argv) < 2:
        print("""Usage: chart <command> [options]

Commands:
  chart <code> [days]            生成单基金走势图
  chart compare <codes> [days]   生成多基金对比图
  chart pie                       生成持仓饼图

Examples:
  chart 000001 30
  chart compare 000001,110022 30
  chart pie
""", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "compare" and len(sys.argv) >= 3:
        codes = sys.argv[2].split(',')
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        result = generate_comparison_chart(codes, days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "pie":
        from fund_daily.profit import calculate_total_profit
        holdings = calculate_total_profit()
        result = generate_profit_pie_chart(holdings)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif len(sys.argv) >= 2:
        fund_code = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        result = generate_trend_chart(fund_code, days)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
