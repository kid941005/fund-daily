# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.7.17] - 2026-03-27

### Changed
- 代码质量全面提升：Lint 清理 E402/F401/F541/F821 共 50+ 错误
- Pydantic 迁移：`class Config` → `ConfigDict(use_enum_values=True)`
- datetime: `utcnow()` → `timezone.utc` 修复弃用警告
- 全项目 `isort + black` 格式化

### Fixed
- advice/generate.py: 提取辅助函数，复杂度 40→15
- services/fund_service.py: 提取辅助函数，复杂度 27→15
- tasks/models.py: 新建，分离 TaskType/TaskStatus/TaskInfo/TaskContext
- scheduler/jobs.py: 顶层导入 TaskType，消除循环依赖
- Dockerfile: 端口 5000→5007，补充缺失环境变量

## [2.7.16] - 2026-03-27

### Changed
- 架构清理：删除 6 个死代码文件（-621 行）
- 删除未使用的异步数据库层、未使用的 Flask 备份文件
- fetcher 文件重命名消除同名混淆

### Fixed
- db.init_db() 懒加载（数据库不可用时降级启动）
- fetch_fund_data 缓存命中后不再发无谓 API 请求

## [2.7.15] - 2026-03-27

### Changed
- 修复 Release 创建权限

## [2.7.14] - 2026-03-27

### Fixed
- 修复 dist 路径，Vite 输出到 ./dist

## [2.7.13] - 2026-03-27

### Fixed
- 修复 .dockerignore 规则

## [2.7.12] - 2026-03-27

### Changed
- 从 .dockerignore 移除 web/vue3/dist

## [2.7.11] - 2026-03-27

### Changed
- 简化 Dockerfile，使用预构建前端

## [2.7.10] - 2026-03-27

### Fixed
- Docker Compose .env 缺失变量 (POSTGRES_PASSWORD, REDIS_PASSWORD, REDIS_DB, FUND_DAILY_DB_PASSWORD)
- Docker Compose 默认端口 5000 → 5007（统一项目惯例）
- .env.example / .env.dev 与最新代码同步
- README 版本号 (2.7.3 → 2.7.10)、测试数 (289 → 268)、PostgreSQL 版本 (13+ → 15+) 一致性修复
- README 端口描述不一致问题

### Changed
- FUND_DAILY_SECRET_KEY 使用 secrets.token_hex 生成真实随机值

## [2.7.0] - 2026-03-26

### Fixed
- P0 严重问题修复 (6个): DB Schema 不一致、缺少 logger 导入、导入路径错误、方法重复定义、CORS 安全、Redis 降级缺陷
- P1 高优先级修复 (12个): JWT 黑名单、分布式锁、缓存语义、分数截断、内存存储线程安全、锁粒度、PBKDF2 迭代、异步任务异常、前端轮询登录检查
- P2/P3 问题修复 (23个): 双重校验、弱密码检查、CORS 配置优化等
- Docker 配置完善: 环境变量统一、docker-compose.yml 修复、CI Linting

### Changed
- Docker 镜像多阶段构建优化
- CI 自动格式化 (black/isort)

## [2.6.3] - 2026-03-25

### Added
- **P0-3: JWT Token 黑名单** - 退出登录后 Token 立即失效
- **P0-4: 密码强度校验** - 8位以上，必须包含数字、大小写字母
- **P1-1: 缓存架构增强** - `get_or_set()`, `get_stats()` 方法
- **P1-2: 评分边界处理** - 数据缺失时返回兜底分数
- **P1-3: Pydantic 严格校验** - Field 长度和范围限制
- **P1-6: 代码规范工具链** - ruff, black, mypy 配置
- **P2-3: 接口性能优化** - 分页支持, GZip 压缩
- **P2-4: 定时任务分批处理** - `batch_process()` 工具函数
- **P2-5: 依赖与镜像优化** - 多阶段构建, requirements 分离
- **P3-1: pytest async fixture** - pytest-asyncio 支持
- **P3-4: Prometheus metrics** - 基础 metrics 模块

### Changed
- 后端从 Flask 切换到 FastAPI
- `/api/holdings` 现在支持分页: `?page=1&page_size=20`
- `LoginRequest`, `RegisterRequest` 等添加字段长度限制

### Fixed
- `analyze_fund` 传递 `use_cache` 参数
- `generate_100_score` 缓存参数传递链
- `calculate_total_score` 内部缓存逻辑
- OCR 路由 `/import-screenshot` → `/import_screenshot`
- 静态文件服务 `MutableHeaders.pop` 问题

### Removed
- Flask 双引擎架构（旧 API endpoints）
- `src/openapi/`, `src/api_gateway/` (Flask OpenAPI/Gateway)
- `web/security.py`, `web/monitoring.py` (Flask 中间件)
- `test_validation.py` (过时的测试)

## [2.6.0] - 2026-03-18

### Added
- JWT 认证系统
- 多级缓存（Redis + 内存）
- 36 个数据库性能索引
- 统一错误处理

### Changed
- 服务层模块化拆分
