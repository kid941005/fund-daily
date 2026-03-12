# Fund Daily 🦞

> 每日基金分析工具 - 模块化重构版本

[![GitHub Stars](https://img.shields.io/github/stars/kid941005/fund-daily?style=flat)](https://github.com/kid941005/fund-daily)
[![Version](https://img.shields.io/badge/version-2.2.0-blue)](https://github.com/kid941005/fund-daily)
[![Python](https://img.shields.io/badge/python-3.11+-green)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)

## ✨ 特性

- 📊 **基金数据分析** - 实时获取基金净值、涨跌幅、市场情绪
- 🧠 **智能投资建议** - 基于市场情绪和风险评估的个性化建议
- 🔍 **增强情绪分析** - 60+ 关键词 + 板块权重 + 综合评分
- 📝 **OCR 识别** - 智能解析基金截图（需安装 EasyOCR）
- 🐳 **Docker 支持** - 精简镜像 ~200MB
- ✅ **完整测试** - 52+ 单元测试用例
- 🔄 **CI/CD** - GitHub Actions 自动测试

## 🏗️ 项目架构

```
fund-daily/
├── src/                      # 核心业务模块
│   ├── fetcher/            # 数据获取层
│   │   └── __init__.py    # API 调用 + 缓存
│   ├── analyzer/           # 分析引擎
│   │   ├── __init__.py    # 风险计算
│   │   ├── risk.py        # 真实风险分析 (numpy)
│   │   └── sentiment.py   # 增强情绪分析
│   ├── advice/            # 投资建议
│   │   └── __init__.py    # 建议生成逻辑
│   ├── models/            # 数据模型
│   │   └── __init__.py    # dataclasses 定义
│   └── ocr.py            # OCR 解析模块
│
├── web/                     # Web 层
│   ├── app.py             # Flask 主应用
│   ├── api/               # HTTP 接口
│   │   ├── routes.py     # API 端点
│   │   └── auth.py       # 认证
│   ├── services/          # 业务逻辑
│   │   └── fund_service.py
│   ├── templates/         # 前端模板
│   └── static/           # 静态资源
│
├── tests/                   # 单元测试
│   ├── test_fetcher.py
│   ├── test_analyzer.py
│   ├── test_advice.py
│   ├── test_ocr.py
│   └── test_services.py
│
├── scripts/                 # CLI 工具
│   └── fund-daily-cli.py
│
├── db/                      # 数据持久化
│   └── database.py
│
├── .github/workflows/      # CI/CD
│   └── ci.yml
│
└── Dockerfile              # Docker 构建
```

## 🚀 快速开始

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
export FUND_DAILY_DB_PATH=$(pwd)/data/fund-daily.db
python web/app.py

# 访问 http://localhost:5000
```

### Docker 运行

```bash
# 构建镜像
docker build -t fund-daily .

# 运行容器
docker run -d -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  fund-daily

# 访问 http://localhost:5000
```

### Docker Compose

```bash
docker-compose up -d
```

## 📡 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/funds` | GET | 获取基金列表 |
| `/api/fund/<code>` | GET | 基金详情 |
| `/api/report` | GET | 每日报告 |
| `/api/advice` | GET | 投资建议 |
| `/api/holdings` | GET/POST | 持仓管理 |
| `/api/news` | GET | 市场热点 |
| `/api/sectors` | GET | 热门板块 |
| `/api/portfolio-analysis` | GET | 组合分析 |

## 🧪 测试

```bash
# 安装测试依赖
pip install -r requirements-dev.txt

# 运行所有测试
pytest tests/ -v

# 运行覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 📦 依赖

### 核心依赖

```
flask>=3.0.0
flask-cors>=4.0.0
requests>=2.31.0
numpy>=1.24.0
```

### 可选依赖

```bash
# OCR 功能 (约 2GB)
pip install easyocr

# 或使用云 OCR API
```

## 🛠️ 技术栈

- **后端**: Flask + SQLite
- **数据分析**: NumPy
- **测试**: pytest + pytest-cov
- **CI/CD**: GitHub Actions
- **容器化**: Docker

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<p align="center">Made with 🦞 by 挞挞</p>
