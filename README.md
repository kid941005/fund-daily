# Fund Daily 🦞

> 每日基金分析系统 - 智能持仓管理与量化分析

[![GitHub Stars](https://img.shields.io/github/stars/kid941005/fund-daily?style=flat)](https://github.com/kid941005/fund-daily)
[![Version](https://img.shields.io/badge/version-2.7.17-blue)](https://github.com/kid941005/fund-daily/releases/tag/v2.7.17)
[![Python](https://img.shields.io/badge/python-3.11+-green)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.100+-blue)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/vue-3.3-green)](https://vuejs.org/)
[![Tests](https://img.shields.io/badge/tests-268-green)](https://github.com/kid941005/fund-daily)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)

## ✨ 特性

- 📊 **基金数据分析** - 实时获取基金净值、收益率、市场情绪
- 💼 **持仓管理** - 支持手动添加、OCR 截图导入、一键清仓
- 🧠 **智能评分系统** - 8维度综合评分 + 量化择时信号统一
- 🔍 **量化分析** - 动量信号、动态权重、投资组合优化
- 📝 **OCR 识别** - 智能解析基金截图，快速导入持仓
- 📈 **定时任务** - 自动净值更新、评分计算、缓存预热
- 🔐 **JWT 认证** - 安全的 API 认证系统
- 🗄️ **多级缓存** - Redis + 内存缓存，自动失效
- 🐳 **Docker 支持** - 一键部署
- ✅ **完整测试** - 268 个单元测试用例
- 🔄 **CI/CD** - GitHub Actions 自动测试 + Docker 构建

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Vue 3 前端                              │
│                   (TypeScript + Vite)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI 后端                             │
│              (Python 3.11+ + Uvicorn)                     │
├─────────────────────────────────────────────────────────────┤
│  API Routes: auth | funds | holdings | analysis | quant   │
├─────────────────────────────────────────────────────────────┤
│  Services: score_service | fund_service | quant_service  │
├─────────────────────────────────────────────────────────────┤
│  Scoring: 8-dimension scoring system (100-point)          │
├─────────────────────────────────────────────────────────────┤
│  Fetcher: EastMoney API + Historical NAV parsing          │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│       PostgreSQL         │   │         Redis           │
│    (用户/持仓/评分)      │   │    (多级缓存)          │
└─────────────────────────┘   └─────────────────────────┘
```

## 📁 项目结构

```
fund-daily/
├── src/                        # 核心业务模块
│   ├── fetcher/              # 数据获取层
│   │   ├── fund_basic/       # 基金基础数据 + 历史净值
│   │   ├── fund_advanced/    # 增强数据获取
│   │   ├── market_data/      # 市场数据（板块/情绪/新闻）
│   │   └── cache/           # 缓存管理 (Redis + LRU)
│   ├── scoring/             # 评分系统
│   │   ├── calculator.py    # 评分计算器
│   │   ├── config.py        # 权重配置
│   │   ├── performance.py   # 业绩评分
│   │   ├── valuation.py      # 估值评分
│   │   ├── risk.py          # 风险评分
│   │   ├── momentum.py      # 动量评分
│   │   └── ...
│   ├── services/            # 业务服务层
│   │   ├── score_service.py # 评分服务
│   │   ├── fund_service.py  # 基金服务
│   │   └── quant_service.py # 量化服务
│   ├── scheduler/           # 定时任务调度 (APScheduler)
│   ├── advice/             # 投资建议生成
│   ├── analyzer/            # 市场分析
│   ├── auth.py              # 认证模块
│   ├── jwt_auth.py         # JWT 认证
│   └── config.py           # 配置管理 (dataclass)
│
├── web/                      # Web 层
│   ├── api_fastapi/        # FastAPI 应用 (主)
│   │   ├── main.py         # FastAPI 主应用
│   │   ├── routers/        # API 路由
│   │   ├── middleware/     # 中间件 (限流等)
│   │   └── deps.py         # 依赖注入
│   └── vue3/               # Vue 3 前端源码
│       └── src/
│           ├── views/       # 页面组件
│           ├── stores/       # Pinia 状态管理
│           ├── api/         # API 调用
│           └── types/       # TypeScript 类型
│
├── db/                       # 数据层
│   ├── pool.py             # 连接池管理
│   ├── users.py            # 用户 CRUD
│   ├── holdings.py         # 持仓 CRUD
│   └── fund_ops.py         # 基金数据操作
│
├── tests/                    # 单元测试 (268)
│
├── nginx/                    # Nginx 配置
│
├── docker-compose.yml        # Docker Compose
├── Dockerfile               # Docker 镜像
└── .env.example            # 环境变量模板
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis 6+
- Node.js 18+ (前端开发)

### 1. 克隆项目

```bash
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily
```

### 2. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 或使用虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 设置数据库密码
```

### 4. 启动服务

**本地开发模式：**
```bash
# 设置环境变量
export FUND_DAILY_DB_PASSWORD=your_password

# 启动 FastAPI 服务
python3 -m uvicorn web.api_fastapi.main:app --host 0.0.0.0 --port 5007 --reload
```

**Docker 部署模式：**
```bash
# 使用 Docker Compose（推荐）
docker-compose up -d

# 或手动启动
docker build -t fund-daily .
docker run -p 5007:5007 --env-file .env fund-daily
```

### 5. 默认登录凭据

系统初始化后会自动创建默认管理员账户：

- **用户名**: `admin`
- **密码**: `admin123`

⚠️ **安全提示**: 生产环境请立即修改默认密码或创建新账户。

### 5. 访问

- Web 界面: http://localhost:5007 (Docker 模式下)
- API 文档: http://localhost:5007/docs

## 🐳 Docker 部署

```bash
# 使用 Docker Compose
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

## 📡 API 接口

### 认证接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/logout` | POST | 用户退出 |
| `/api/auth/refresh` | POST | 刷新 Token |
| `/api/auth/check-login` | GET | 检查登录状态 |

### 基金接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/funds` | GET | 获取基金列表（支持 `?force=true` 强制刷新） |
| `/api/fund-detail/{code}` | GET | 获取基金详情 |
| `/api/score/{code}` | GET | 获取基金评分（8维度） |

### 持仓接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/holdings` | GET | 获取持仓列表 |
| `/api/holdings` | POST | 添加持仓 |
| `/api/holdings` | DELETE | 删除持仓 |
| `/api/holdings/clear` | POST | 清仓 |
| `/api/import_screenshot` | POST | OCR 截图导入 |

### 量化接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/quant/timing-signals` | GET | 择时信号 |
| `/api/quant/portfolio-optimize` | GET | 组合优化 |
| `/api/quant/dynamic-weights` | GET | 动态权重 |
| `/api/quant/rebalancing` | GET | 调仓建议 |

### 系统接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/sectors` | GET | 热门板块 |
| `/api/news` | GET | 市场新闻 |

## 📊 评分系统

评分采用 100 分制，8 个维度：

| 维度 | 满分 | 说明 |
|------|------|------|
| 估值 | 25 | 市盈率/市净率等 |
| 业绩 | 20 | 近3月/1年收益率 |
| 风险 | 15 | 波动率/最大回撤 |
| 动量 | 15 | 趋势分析 |
| 情绪 | 10 | 市场情绪 |
| 板块 | 8 | 行业景气度 |
| 经理 | 4 | 基金经理评分 |
| 流动性 | 3 | 日均成交量 |

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行覆盖率
pytest tests/ --cov=src --cov-report=html

# 运行特定测试
pytest tests/test_scoring.py -v
```

## 🛠️ 技术栈

- **后端**: FastAPI (Python 3.11+) + Uvicorn
- **前端**: Vue 3 + TypeScript + Vite + Pinia + ECharts
- **数据库**: PostgreSQL 13+
- **缓存**: Redis + 内存缓存 (LRU)
- **认证**: JWT (python-jose) + PBKDF2 密码哈希
- **定时任务**: APScheduler + Redis 分布式锁
- **测试**: pytest (268 测试用例)
- **CI/CD**: GitHub Actions
- **容器化**: Docker + Docker Compose

## 🔧 环境变量

> ⚠️ 所有配置统一使用 `FUND_DAILY_` 前缀（向后兼容旧变量名）

### 核心配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FUND_DAILY_ENV` | development | 环境 (development/production) |
| `FUND_DAILY_SERVER_PORT` | 5007 | 服务端口（Docker 默认 5007，本地开发直接启动为 5007）|
| `FUND_DAILY_DEBUG` | false | 调试模式 |

### 数据库配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FUND_DAILY_DB_HOST` | localhost | PostgreSQL 主机 |
| `FUND_DAILY_DB_PORT` | 5432 | PostgreSQL 端口 |
| `FUND_DAILY_DB_NAME` | fund_daily | 数据库名 |
| `FUND_DAILY_DB_USER` | kid | 数据库用户名 |
| `FUND_DAILY_DB_PASSWORD` | - | ⚠️ 必须设置 |

### Redis 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FUND_DAILY_REDIS_HOST` | localhost | Redis 主机 |
| `FUND_DAILY_REDIS_PORT` | 6379 | Redis 端口 |
| `FUND_DAILY_REDIS_DB` | 0 | Redis 数据库 |
| `FUND_DAILY_REDIS_PASSWORD` | - | Redis 密码 |
| `FUND_DAILY_REDIS_TTL` | 1800 | 缓存 TTL（秒） |

### 安全配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FUND_DAILY_SECRET_KEY` | - | ⚠️ 必须设置（会话加密） |
| `FUND_DAILY_JWT_SECRET` | - | ⚠️ 必须设置（JWT 签名） |
| `FUND_DAILY_JWT_EXPIRE_MINUTES` | 30 | JWT 过期时间 |
| `FUND_DAILY_CORS_ORIGINS` | * | CORS 白名单（生产环境应配置） |

## 📝 更新日志

### v2.7.17 (2026-03-30) - OCR 打包 + 评分系统优化
- ✅ OCR 依赖完整打包进 Docker 镜像（easyocr、opencv-python-headless、scipy 等）
- ✅ 评分分布图与量化板块评分系统统一（使用 timing_signals 评分）
- ✅ Docker 镜像重新构建，包含所有 OCR 依赖
- ✅ .gitignore 和 .dockerignore 完善
- ✅ 修复 python-bidi 版本兼容性问题

### v2.7.10 (2026-03-27) - Docker 配置修复
- ✅ 补全 .env 缺失变量 (POSTGRES_PASSWORD, REDIS_PASSWORD, REDIS_DB, FUND_DAILY_DB_PASSWORD)
- ✅ 生成真实 FUND_DAILY_SECRET_KEY
- ✅ 统一 docker-compose 默认端口 5007
- ✅ 同步 .env / .env.example / .env.dev 一致性
- ✅ README 版本号/测试数/端口一致性修复

### v2.7.x (2026-03-26) - 近期更新
- ✅ 环境变量统一 (FUND_DAILY_ Prefix)
- ✅ P0 严重问题修复 (6个)
- ✅ P1 高优先级问题修复 (12个)
- ✅ P2/P3 问题修复
- ✅ Docker 配置优化
- ✅ 安全加固 (密码哈希 310k 迭代, Redis fail-safe)

### v2.6.3 (2026-03-25)
- ✅ 后端切换到 FastAPI
- ✅ 评分系统完整修复（8维度显示）
- ✅ 缓存传递链完整修复
- ✅ OCR 截图导入功能

### v2.6.0 (2026-03-18)
- 🔒 安全加固：统一输入验证
- 🗄️ 数据库优化：36 个性能索引
- 🏗️ 架构升级：服务层模块化
- ⚡ 性能优化：多级缓存 + 连接池

[查看完整更新日志](CHANGELOG.md)

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<p align="center">Made with 🦞</p>
