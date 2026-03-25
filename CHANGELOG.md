# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
