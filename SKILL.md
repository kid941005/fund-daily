---
name: fund-daily
description: Daily fund analysis and sharing tool. Fetch fund NAV data, analyze trends, generate daily reports with market sentiment. Supports multiple funds comparison and formatted sharing output. Perfect for daily fund monitoring and investment tracking.
---

# Fund Daily - 每日基金分析工具

自动获取基金数据，分析趋势，生成每日报告。

## Features

- 📊 **实时数据** - 获取基金净值、涨跌幅
- 📈 **趋势分析** - 自动判断涨跌趋势
- 📋 **每日报告** - 生成多基金对比报告
- 💬 **分享格式** - 一键生成适合分享的文字
- 🎯 **市场情绪** - 统计涨跌分布，判断市场情绪

## Usage

### 获取单只基金数据

```bash
python3 ~/.openclaw/workspace/skills/fund-daily/scripts/fund-daily.py fetch 000001
```

### 分析单只基金

```bash
python3 ~/.openclaw/workspace/skills/fund-daily/scripts/fund-daily.py analyze 000001
```

### 生成每日报告（多只基金）

```bash
python3 ~/.openclaw/workspace/skills/fund-daily/scripts/fund-daily.py report 000001,000002,000003
```

### 生成分享文本

```bash
python3 ~/.openclaw/workspace/skills/fund-daily/scripts/fund-daily.py share 000001,000002,000003
```

## Output Examples

### JSON Report
```json
{
  "date": "2026-03-05",
  "funds": [
    {
      "fund_code": "000001",
      "fund_name": "华夏成长",
      "nav": "1.2345",
      "daily_change": "2.35",
      "trend": "up",
      "summary": "🚀 华夏成长 今日大涨 2.35%，净值 1.2345"
    }
  ],
  "summary": {
    "total": 3,
    "up": 2,
    "down": 1,
    "market_sentiment": "乐观"
  }
}
```

### Share Format
```
📊 每日基金报告 2026-03-05
========================================

🚀 华夏成长 今日大涨 2.35%，净值 1.2345
   代码: 000001 | 净值: 1.2345

📈 嘉实沪深300 今日上涨 1.20%，净值 1.5678
   代码: 000002 | 净值: 1.5678

========================================
📈 上涨: 2 只
📉 下跌: 1 只
➖ 平盘: 0 只
💡 市场情绪: 乐观

⚠️ 仅供参考，不构成投资建议
```

## Data Source

- 东方财富基金数据 API
- 实时净值数据
- 每日涨跌幅统计

## Fund Codes

常见基金代码示例：
- `000001` - 华夏成长
- `000002` - 华夏成长(后端)
- `000003` - 中海可转债
- `110022` - 易方达消费行业
- `161725` - 招商白酒

> 在天天基金网搜索基金名称可找到对应代码

## Automation

### 设置定时任务

```bash
# 编辑 crontab
crontab -e

# 每天 15:30 生成报告并发送到 Telegram
30 15 * * * python3 ~/.openclaw/workspace/skills/fund-daily/scripts/fund-daily.py share 000001,000002,000003 >> /tmp/fund_report.txt && curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" -d "chat_id=<CHAT_ID>" -d "text=$(cat /tmp/fund_report.txt)"
```

### GitHub Actions 定时运行

创建 `.github/workflows/fund-daily.yml`：
```yaml
name: Daily Fund Report
on:
  schedule:
    - cron: '30 15 * * *'  # 每天 15:30 UTC+8
  workflow_dispatch:

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Generate Report
        run: python3 fund-daily.py share 000001,000002,000003
```

## Notes

- 数据来源：东方财富公开 API
- 数据更新：交易日 15:00 后更新当日净值
- 风险提示：仅供参考，不构成投资建议
- 基金投资有风险，入市需谨慎

## Links

- 天天基金网：https://fund.eastmoney.com/
- 参考项目：https://github.com/ZhuLinsen/daily_stock_analysis
