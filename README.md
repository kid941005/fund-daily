# Fund Daily - 每日基金分析工具

🚀 自动获取基金数据，分析趋势，生成每日报告，支持持仓管理和风险分析

[English](README_EN.md) | 中文

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 📊 实时数据 | 获取基金净值、估算涨跌幅 |
| 📈 趋势分析 | 自动判断涨跌趋势 |
| 🧠 市场情绪 | 综合板块+新闻计算市场情绪得分 |
| 📉 风险分析 | 夏普比率、最大回撤、风险评分 |
| 💰 持仓管理 | 用户账号系统，添加/修改持仓 |
| 📥 数据导入 | CSV文件 / 截图OCR识别 / 支付宝截图 |
| 📤 数据导出 | CSV/JSON格式，支持中文表头 |
| 📋 每日报告 | 生成多基金对比报告 |
| 🔔 钉钉通知 | Webhook推送每日报告和涨跌提醒 |
| 💬 分享格式 | 一键生成适合分享的文字 |
| 🌐 Web UI | 可视化界面，操作建议 |
| 📱 PWA支持 | 可添加到手机桌面 |
| 🐳 Docker | 一键部署 |

## 🖼️ 界面预览

![Fund Daily](https://via.placeholder.com/800x400?text=Fund+Daily+Web+UI)

## 🚀 快速开始

### 方式 1: 直接运行

```bash
# 克隆仓库
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily

# 安装依赖
pip3 install -r requirements.txt

# 运行
python3 scripts/fund-daily.py share 000001,110022
```

### 方式 2: Docker 部署

```bash
# 拉取镜像 (Docker Hub)
docker pull kid941005/fund-daily:latest

# 运行
docker run -d -p 5000:5000 kid941005/fund-daily:latest
```

或者使用阿里云镜像：

# 运行
docker run --rm fund-daily share 000001,110022
```

### 方式 3: Web UI

```bash
# 安装依赖
pip3 install -r requirements.txt

# 启动 Web 服务
python3 web/app.py

# 访问 http://localhost:5000
```

## 📖 使用说明

### 命令行工具

```bash
# 获取单只基金数据
python3 scripts/fund-daily.py fetch 000001

# 分析单只基金
python3 scripts/fund-daily.py analyze 000001

# 生成每日报告
python3 scripts/fund-daily.py report 000001,000002,000003

# 生成分享文本
python3 scripts/fund-daily.py share 000001,000002,000003

# 获取市场热点新闻
python3 scripts/fund-daily.py news

# 获取热门板块
python3 scripts/fund-daily.py sectors

# 获取操作建议
python3 scripts/fund-daily.py advice
```

### Web 界面功能

访问 http://localhost:5000：

| Tab | 功能 |
|-----|------|
| 🔥 热门板块 | 市场热点资讯、板块涨跌排行 |
| 💼 持仓 | 添加/管理持仓，修改金额 |
| 💡 建议 | 操作建议（买入/持有/卖出） |
| 📊 分析 | 组合分析、风险指标、资产配置 |

### 用户系统

- 注册账号：点击右上角"登录/注册"
- 添加持仓：在"持仓"页面点击"+ 添加持仓"
- 导入数据：支持 CSV 文件上传 或 截图 OCR 识别
- 导出数据：登录后点击右上角用户名 → "导出数据"

### 钉钉通知

1. 在钉钉群添加机器人（Webhook 类型）
2. 复制 Webhook 地址
3. 在网页右上角 → 钉钉通知 配置
4. 可以发送测试消息和每日报告

## 🐳 Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 服务列表
- fund-daily-web: http://localhost:5000 (Web UI)
```

## 📋 常用基金代码

| 代码 | 名称 |
|:---|:---|
| 000001 | 华夏成长混合 |
| 110022 | 易方达消费行业 |
| 161725 | 招商中证白酒指数(LOF)A |
| 002190 | 农银新能源主题混合 |
| 005911 | 广发双擎升级混合 |

## 🔧 配置

### 环境变量

在 `.env` 文件中配置：

```bash
# 安全设置
FUND_DAILY_SECRET_KEY=your_secret_key  # 会话密钥
FLASK_ENV=development                   # 生产环境设为 production
FUND_DAILY_SSL_VERIFY=1               # 0 关闭SSL验证

# 缓存设置
FUND_DAILY_CACHE_DURATION=300         # 缓存秒数，默认5分钟
```

### 配置文件

编辑 `config/config.json`：

```json
{
  "default_funds": ["000001", "110022", "161725"],
  "report_time": "15:00"
}
```

## 📄 项目结构

```
fund-daily/
├── scripts/              # 核心脚本
│   └── fund-daily.py    # 主程序
├── web/                  # Web UI
│   ├── app.py           # Flask 应用
│   ├── templates/       # HTML 模板
│   └── static/          # 静态资源
├── db/                   # 数据库
│   ├── database.py      # SQLite 操作
│   └── dingtalk.py      # 钉钉通知
├── config/              # 配置文件
├── SKILL.md             # OpenClaw 技能配置
├── Dockerfile           # CLI 版本
├── Dockerfile.web       # Web 版本
└── docker-compose.yml   # Docker 编排
```

## 🛠️ 技术栈

- **后端**: Flask + SQLite
- **前端**: HTML + CSS + JavaScript (PWA)
- **数据源**: 东方财富公开 API
- **OCR**: Tesseract (截图识别)

## 📊 买卖逻辑

### 评分因素

| 因素 | 权重 | 说明 |
|------|------|------|
| 市场情绪 | ±30 | 乐观+30, 恐慌-30 |
| 基金涨跌 | ±∞ | 平均涨跌幅 × 10 |
| 夏普比率 | ±20 | >1 +20, <0 -15 |
| 最大回撤 | ±20 | >20% -20 |

### 操作建议

| 分数 | 操作 |
|------|------|
| > 40 | 🟢 买入 |
| 20 ~ 40 | 🔵 持有 |
| -10 ~ 20 | 🔵 持有 |
| -30 ~ -10 | 🟠 减仓 |
| < -30 | 🔴 卖出 |

## ⚠️ 免责声明

- 数据来源：东方财富公开 API
- 仅供参考，不构成投资建议
- 基金投资有风险，入市需谨慎

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 🙏 致谢

- 数据来源：[东方财富](https://fund.eastmoney.com/)
- OCR 引擎：[Tesseract](https://github.com/tesseract-ocr/tesseract)
