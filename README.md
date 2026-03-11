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

## 🚀 快速开始

### 方式 1: Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily

# 启动服务
docker-compose up -d

# 访问 http://localhost:5000
```

**版本说明**：
- `kid941005/fund-daily:latest` - 最新版
- `kid941005/fund-daily:v1.9.1` - 指定版本

GitHub Actions 自动构建推送至 Docker Hub

### 方式 2: Docker 单容器

```bash
# 拉取镜像
docker pull kid941005/fund-daily:latest

# 运行
docker run -d -p 5000:5000 kid941005/fund-daily:latest
```

### 方式 3: 本地运行

```bash
# 克隆仓库
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily

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

### 快速启动

```bash
# 克隆并启动
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily
docker-compose up -d
```

### 配置说明

`docker-compose.yml` 已包含默认配置：

| 配置 | 值 |
|------|-----|
| 端口 | 5000 |
| 时区 | Asia/Shanghai |
| 数据库 | /app/data/fund-daily.db |
| 自动重启 | ✅ |

### 管理命令

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 查看日志
docker-compose logs -f

# 重启
docker-compose restart

# 更新
docker-compose down
docker-compose pull
docker-compose up -d
```

### 数据持久化

数据存储在 `data/` 目录：
- `data/fund-daily.db` - SQLite 数据库
- `data/` 目录会在首次运行时自动创建

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

| 变量 | 说明 | 默认值 |
|------|------|--------|
| FUND_DAILY_SECRET_KEY | 会话密钥 | 自动生成 |
| FLASK_ENV | 运行环境 | production |
| FUND_DAILY_SSL_VERIFY | SSL验证 | 1 |
| FUND_DAILY_DB_PATH | 数据库路径 | /app/data/fund-daily.db |
| FUND_CODES | 默认基金代码 | 000001,110022,161725 |

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
├── docker-compose.yml    # Docker 编排
├── Dockerfile           # 容器定义
└── README.md            # 说明文档
```

## 🛠️ 技术栈

- **后端**: Flask + SQLite
- **前端**: HTML + CSS + JavaScript (PWA)
- **数据源**: 东方财富公开 API
- **OCR**: EasyOCR (本地离线识别)

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

## 🙏 致谢

- 数据来源：[东方财富](https://fund.eastmoney.com/)
- OCR 引擎：[EasyOCR](https://github.com/JaidedAI/EasyOCR)
