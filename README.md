# Fund Daily 🦞

> 每日基金分析工具 - 智能持仓管理与风险分析

[![GitHub Stars](https://img.shields.io/github/stars/kid941005/fund-daily?style=flat)](https://github.com/kid941005/fund-daily)
[![Version](https://img.shields.io/badge/version-2.6.0-blue)](https://github.com/kid941005/fund-daily/releases/tag/v2.6.0)
[![Python](https://img.shields.io/badge/python-3.11+-green)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-63+-green)](https://github.com/kid941005/fund-daily)

## ✨ 特性

- 📊 **基金数据分析** - 实时获取基金净值、涨跌幅、市场情绪
- 💼 **持仓管理** - 支持手动添加、OCR 截图导入、一键清仓
- 🧠 **智能投资建议** - 基于市场情绪和风险评估的个性化建议
- 🔍 **增强情绪分析** - 60+ 关键词 + 板块权重 + 综合评分
- 📝 **OCR 识别** - 智能解析基金截图（支持 2列/3列布局）
- 🐳 **Docker 支持** - 精简镜像 ~300MB (CPU-only PyTorch)
- ✅ **完整测试** - 63+ 单元测试用例
- 🔄 **CI/CD** - GitHub Actions 自动测试 + Docker 构建

## 🏗️ 项目架构

```
fund-daily/
├── src/                        # 核心业务模块
│   ├── fetcher/               # 数据获取层
│   │   └── __init__.py       # API 调用 + 缓存 + 限流
│   ├── analyzer/              # 分析引擎
│   │   ├── risk.py           # 风险计算 (numpy)
│   │   └── sentiment.py      # 市场情绪分析
│   ├── advice/                # 投资建议
│   │   └── __init__.py       # 建议生成逻辑
│   ├── models/                # 数据模型
│   │   └── __init__.py       # dataclasses
│   └── ocr.py                 # OCR 解析模块
│
├── web/                        # Web 层
│   ├── app.py                 # Flask 主应用
│   ├── api/                   # HTTP 接口
│   │   ├── routes.py         # API 端点
│   │   └── auth.py           # 认证
│   ├── services/              # 业务逻辑
│   │   └── fund_service.py
│   ├── templates/             # 前端模板
│   │   └── index.html        # 单页应用
│   └── static/               # 静态资源
│
├── db/                         # 数据层
│   ├── database.py           # SQLite 操作
│   └── dingtalk.py           # 钉钉推送
│
├── tests/                      # 单元测试 (63+)
│   ├── test_fetcher.py
│   ├── test_analyzer.py
│   ├── test_advice.py
│   ├── test_ocr.py
│   └── test_services.py
│
├── scripts/                    # CLI 工具
│   └── fund-daily-cli.py
│
├── config/                     # 配置文件
├── docker-compose.yml          # Docker Compose
├── Dockerfile                 # Docker 镜像
└── pyproject.toml            # 项目配置
```

## 🎉 最新版本 v2.6.0 已发布！

**v2.6.0 主要改进**:
- 🔒 **安全加固**: 统一输入验证系统，防止安全漏洞
- 🗄️ **数据库优化**: PostgreSQL完全迁移 + 36个性能索引
- 🏗️ **架构升级**: 服务层重构 + 模块化设计
- ✨ **功能增强**: 清仓按钮 + 实时数据展示
- ⚡ **性能优化**: 多级缓存 + 连接池优化

[查看完整发布说明](CHANGELOG-2.6.0.md) | [下载 v2.6.0](https://github.com/kid941005/fund-daily/releases/tag/v2.6.0)

## 🚀 快速开始

### 本地运行

```bash
# 克隆项目
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily

# 安装依赖
pip install -r web/requirements.txt

# 可选：安装 OCR 依赖
pip install easyocr

# 运行
export FUND_DAILY_DB_PATH=/path/to/fund-daily.db
python -m flask run --host=0.0.0.0 --port=5000
```

### Docker 运行

```bash
# 使用 Docker Compose
docker-compose up -d

# 或手动构建
docker build -t fund-daily .
docker run -d -p 5000:5000 fund-daily
```

### 访问

- Web 界面: http://localhost:5000
- API 端点: http://localhost:5000/api/funds

## 📡 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/funds` | GET | 获取基金列表 |
| `/api/holdings` | GET/POST/DELETE | 持仓管理 |
| `/api/holdings/clear-all` | POST | 一键清仓 |
| `/api/portfolio-analysis` | GET | 组合分析 |
| `/api/import-screenshot` | POST | OCR 截图导入 |
| `/api/news` | GET | 市场热点新闻 |
| `/api/sectors` | GET | 热门板块 |
| `/api/login` | POST | 用户登录 |
| `/api/logout` | POST | 用户退出 |

## 🧪 测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行所有测试
pytest tests/ -v

# 运行覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 🛠️ 技术栈

- **后端**: Flask + SQLite
- **数据分析**: NumPy
- **OCR**: EasyOCR (可选)
- **测试**: pytest + pytest-cov
- **CI/CD**: GitHub Actions
- **容器化**: Docker

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<p align="center">Made with 🦞 by 挞挞</p>

## 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| FUND_DAILY_DB_TYPE | sqlite | 数据库类型 (sqlite/postgres) |
| FUND_DAILY_DB_PATH | /app/data/fund-daily.db | SQLite 数据库路径 |
| FUND_DAILY_DB_HOST | localhost | PostgreSQL 主机 |
| FUND_DAILY_DB_PORT | 5432 | PostgreSQL 端口 |
| FUND_DAILY_DB_NAME | fund_daily | PostgreSQL 数据库名 |
| FUND_DAILY_DB_USER | kid | PostgreSQL 用户名 |
| FUND_DAILY_DB_PASSWORD | - | PostgreSQL 密码 |
| REDIS_TTL | 1800 | Redis 缓存时间(秒) |
| FUND_DAILY_SECRET_KEY | - | Flask Session 密钥 |

## 快速启动

```bash
# SQLite 模式
cd web && python3 app.py

# PostgreSQL + Redis 模式
export FUND_DAILY_DB_TYPE=postgres
export FUND_DAILY_DB_NAME=fund_daily
export FUND_DAILY_DB_USER=kid
export FUND_DAILY_DB_PASSWORD=your_password
cd web && python3 app.py
```
