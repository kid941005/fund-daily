# Fund Daily 🦞

> 每日基金分析工具 - 智能持仓管理与风险分析

[![GitHub Stars](https://img.shields.io/github/stars/kid941005/fund-daily?style=flat)](https://github.com/kid941005/fund-daily)
[![Version](https://img.shields.io/badge/version-2.6.0-blue)](https://github.com/kid941005/fund-daily/releases/tag/v2.6.0)
[![Python](https://img.shields.io/badge/python-3.11+-green)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-216+-green)](https://github.com/kid941005/fund-daily)

## ✨ 特性

- 📊 **基金数据分析** - 实时获取基金净值、涨跌幅、市场情绪
- 💼 **持仓管理** - 支持手动添加、OCR 截图导入、一键清仓
- 🧠 **智能投资建议** - 基于市场情绪和风险评估的个性化建议
- 🔍 **增强情绪分析** - 60+ 关键词 + 板块权重 + 综合评分
- 📝 **OCR 识别** - 智能解析基金截图（支持 2列/3列布局）
- 🐳 **Docker 支持** - 精简镜像 ~300MB (CPU-only PyTorch)
- ✅ **完整测试** - 216+ 单元测试用例
- 🔄 **CI/CD** - GitHub Actions 自动测试 + Docker 构建
- 🔐 **JWT 认证** - 安全的 API 认证系统
- 🛡️ **统一错误处理** - 减少 140+ 处重复错误处理代码
- 📈 **量化分析** - 动量信号、动态权重、投资组合优化
- 🗄️ **模块化架构** - 清晰的模块分离，易于维护和扩展

## 🏗️ 项目架构

```
fund-daily/
├── src/                        # 核心业务模块
│   ├── fetcher/               # 数据获取层
│   │   ├── fund_basic/       # 基础基金数据获取
│   │   ├── market_data/      # 市场数据获取
│   │   ├── enhanced_fetcher/ # 增强数据获取
│   │   └── __init__.py       # 统一导出层
│   ├── analyzer/              # 分析引擎
│   │   ├── risk.py           # 风险计算 (numpy)
│   │   └── sentiment.py      # 市场情绪分析
│   ├── advice/                # 投资建议
│   │   └── generate.py       # 建议生成逻辑
│   ├── scoring/              # 评分系统
│   │   ├── calculator.py     # 评分计算器
│   │   ├── config.py         # 权重配置
│   │   ├── weights.py        # 动态权重
│   │   └── models.py         # 数据模型
│   ├── services/             # 业务服务层
│   │   ├── fund_service.py   # 基金服务
│   │   ├── market_service.py # 市场服务
│   │   ├── score_service.py  # 评分服务
│   │   └── quant_service.py  # 量化服务
│   ├── utils/                # 工具模块
│   │   ├── error_handling.py # 统一错误处理
│   │   ├── cache_keys.py     # 缓存键生成
│   │   └── rate_limiter.py   # 限流器
│   ├── interfaces.py         # 接口定义
│   ├── analyzer_impl.py      # 分析器实现
│   └── ocr.py                # OCR 解析模块
│
├── web/                        # Web 层
│   ├── app.py                 # Flask 主应用
│   ├── api/                   # HTTP 接口
│   │   ├── endpoints/        # API 端点
│   │   │   ├── auth.py      # 认证端点
│   │   │   ├── funds.py     # 基金端点
│   │   │   ├── holdings.py  # 持仓端点
│   │   │   └── system.py    # 系统端点
│   │   └── validation.py    # 输入验证
│   ├── openapi/              # OpenAPI 文档生成
│   └── static/               # 静态资源
│
├── db/                         # 数据层
│   ├── pool.py              # PostgreSQL 连接池管理
│   ├── users.py             # 用户数据操作
│   ├── holdings.py          # 持仓数据操作
│   ├── fund_ops.py          # 基金数据操作
│   ├── database_pg.py       # PostgreSQL 操作（向后兼容）
│   └── dingtalk.py          # 钉钉推送
│
├── tests/                      # 单元测试 (216+)
│   ├── test_fetcher.py      # 数据获取测试
│   ├── test_analyzer.py     # 分析器测试
│   ├── test_advice.py       # 建议生成测试
│   ├── test_services.py     # 服务层测试
│   ├── test_scoring.py      # 评分系统测试
│   ├── test_quant_service.py # 量化服务测试
│   ├── test_jwt_auth.py     # JWT 认证测试
│   └── test_db_layer.py     # 数据库层测试
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

# 运行（使用PostgreSQL）
export FUND_DAILY_DB_HOST=localhost
export FUND_DAILY_DB_PASSWORD=your_password
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
| `/api/funds/{code}` | GET | 获取单个基金详情 |
| `/api/funds/{code}/score` | GET | 获取基金评分 |
| `/api/holdings` | GET/POST/DELETE | 持仓管理 |
| `/api/holdings/clear-all` | POST | 一键清仓 |
| `/api/portfolio-analysis` | GET | 组合分析 |
| `/api/import-screenshot` | POST | OCR 截图导入 |
| `/api/news` | GET | 市场热点新闻 |
| `/api/sectors` | GET | 热门板块 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/logout` | POST | 用户退出 |
| `/api/auth/refresh` | POST | 刷新 Token |
| `/api/analysis/market-sentiment` | GET | 市场情绪分析 |
| `/api/analysis/commodity-sentiment` | GET | 商品情绪分析 |
| `/api/quant/timing-signals` | GET | 择时信号分析 |
| `/api/quant/dynamic-weights` | GET | 动态权重计算 |
| `/api/system/health` | GET | 系统健康检查 |
| `/api/system/version` | GET | 系统版本信息 |

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

- **后端**: Flask + PostgreSQL + Redis
- **数据分析**: NumPy + Pandas
- **认证**: JWT (JSON Web Tokens)
- **缓存**: Redis + 内存缓存
- **OCR**: EasyOCR (可选)
- **测试**: pytest + pytest-cov (216+ 测试用例)
- **CI/CD**: GitHub Actions
- **容器化**: Docker + Docker Compose
- **API 文档**: OpenAPI 3.0
- **错误处理**: 统一错误处理工具
- **架构模式**: 依赖注入 + 接口隔离

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<p align="center">Made with 🦞 by 挞挞</p>

## 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| FUND_DAILY_DB_HOST | localhost | PostgreSQL 主机 |
| FUND_DAILY_DB_PORT | 5432 | PostgreSQL 端口 |
| FUND_DAILY_DB_NAME | fund_daily | PostgreSQL 数据库名 |
| FUND_DAILY_DB_USER | kid | PostgreSQL 用户名 |
| FUND_DAILY_DB_PASSWORD | - | PostgreSQL 密码 |
| REDIS_TTL | 1800 | Redis 缓存时间(秒) |
| FUND_DAILY_SECRET_KEY | - | Flask Session 密钥 |

## 快速启动

```bash
# PostgreSQL 模式（默认）
export FUND_DAILY_DB_NAME=fund_daily
export FUND_DAILY_DB_USER=kid
export FUND_DAILY_DB_PASSWORD=your_password
cd web && python3 app.py
```
