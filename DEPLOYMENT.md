# Fund Daily v2.6.0 部署指南

## 项目概述

Fund Daily 是一个基金投资分析平台，提供：
- 基金数据实时获取和分析
- 持仓管理和监控
- 量化分析和投资建议
- 响应式 Web 界面
- JWT 认证系统
- 多级缓存策略

## 技术栈

- **后端**: Flask + PostgreSQL + Redis
- **前端**: Vue 3 + Vite + ECharts
- **缓存**: Redis + 内存多级缓存
- **认证**: JWT + 会话管理
- **监控**: Prometheus + Grafana
- **部署**: Docker + Docker Compose

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily

# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，设置强密码
vim .env
```

### 2. 配置文件 (.env)

```bash
# 生成安全密钥
python -c "import secrets; print('FUND_DAILY_SECRET_KEY=' + secrets.token_hex(32))"
python -c "import secrets; print('FUND_DAILY_JWT_SECRET=' + secrets.token_hex(32))"

# 重要环境变量
POSTGRES_PASSWORD=your_strong_password_here
FUND_DAILY_SECRET_KEY=your_flask_secret_key_here
FUND_DAILY_JWT_SECRET=your_jwt_secret_key_here
```

### 3. 启动服务

#### 开发环境
```bash
# 复制开发配置
cp docker-compose.override.yml.example docker-compose.override.yml

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

#### 生产环境
```bash
# 仅启动核心服务
docker-compose up -d postgres redis backend

# 或启动完整堆栈（包括监控）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. 访问应用

- **Web 界面**: http://localhost:5000
- **API 文档**: http://localhost:5000/api/docs
- **健康检查**: http://localhost:5000/health
- **监控指标**: http://localhost:5000/metrics

## 服务说明

### 核心服务

#### 1. PostgreSQL 数据库
- **端口**: 5432
- **数据卷**: postgres_data
- **健康检查**: pg_isready
- **管理工具**: pgAdmin (开发环境)

#### 2. Redis 缓存
- **端口**: 6379
- **数据卷**: redis_data
- **健康检查**: redis-cli ping
- **管理工具**: Redis Commander (开发环境)

#### 3. Flask 后端
- **端口**: 5000
- **特性**:
  - JWT 认证
  - 多级缓存
  - 速率限制
  - 统一错误处理
  - 健康检查端点
  - Prometheus 指标

#### 4. Vue 前端
- **开发端口**: 5173 (热重载)
- **生产端口**: 80 (通过 Nginx)
- **特性**:
  - 响应式设计
  - ECharts 可视化
  - 懒加载路由
  - 状态管理 (Pinia)

### 可选服务

#### 1. Nginx 反向代理
- **端口**: 80 (HTTP), 443 (HTTPS)
- **功能**:
  - SSL 终止
  - 静态文件服务
  - Gzip/Brotli 压缩
  - 安全头设置

#### 2. Prometheus 监控
- **端口**: 9090
- **功能**:
  - 指标收集
  - 告警规则
  - 数据持久化

#### 3. Grafana 仪表板
- **端口**: 3000
- **默认凭证**: admin/admin
- **功能**:
  - 可视化仪表板
  - 实时监控
  - 性能分析

## 环境配置

### 开发环境
```yaml
# docker-compose.override.yml
services:
  backend:
    environment:
      - FUND_DAILY_ENV=development
      - FUND_DAILY_SERVER_DEBUG=true
    volumes:
      - ./src:/app/src:ro
      - ./web:/app/web:ro
    command: python -m flask run --host=0.0.0.0 --port=5000 --reload
```

### 生产环境
```yaml
# docker-compose.prod.yml (需要创建)
services:
  backend:
    environment:
      - FUND_DAILY_ENV=production
      - FUND_DAILY_SERVER_DEBUG=false
      - FUND_DAILY_SECURE_COOKIES=true
    restart: always
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

## 数据库管理

### 初始化
```bash
# 手动初始化数据库
docker-compose exec postgres psql -U kid -d fund_daily -f /docker-entrypoint-initdb.d/init.sql
```

### 备份
```bash
# 自动备份（每小时）
docker-compose up -d db-exporter

# 手动备份
docker-compose exec postgres pg_dump -U kid fund_daily > backup.sql
```

### 恢复
```bash
# 从备份恢复
docker-compose exec -T postgres psql -U kid -d fund_daily < backup.sql
```

## 监控和日志

### 查看日志
```bash
# 所有服务日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f backend

# 实时日志
docker-compose logs --tail=100 -f
```

### 监控指标
```bash
# 健康检查
curl http://localhost:5000/health

# Prometheus 指标
curl http://localhost:5000/metrics

# Grafana 仪表板
# 访问 http://localhost:3000
# 添加 Prometheus 数据源: http://prometheus:9090
```

## 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查 PostgreSQL 状态
docker-compose logs postgres

# 测试数据库连接
docker-compose exec postgres pg_isready -U kid

# 检查环境变量
docker-compose exec backend env | grep DB
```

#### 2. Redis 连接失败
```bash
# 检查 Redis 状态
docker-compose logs redis

# 测试 Redis 连接
docker-compose exec redis redis-cli ping

# 检查密码配置
docker-compose exec backend env | grep REDIS
```

#### 3. 前端构建失败
```bash
# 检查 Node.js 依赖
docker-compose exec frontend-builder npm list

# 重新构建前端
docker-compose build frontend-builder
docker-compose up -d frontend-builder
```

#### 4. 端口冲突
```bash
# 查看端口使用
netstat -tulpn | grep :5000

# 修改端口配置
# 在 .env 文件中修改:
# FUND_DAILY_SERVER_PORT=5001
```

### 性能优化

#### 1. 数据库索引
```sql
-- 添加性能索引
CREATE INDEX idx_fund_history_composite ON fund_history(fund_code, date DESC);
CREATE INDEX idx_holdings_composite ON holdings(user_id, fund_code);
```

#### 2. 缓存优化
```bash
# 调整 Redis 配置
REDIS_TTL=3600  # 延长缓存时间
FUND_DAILY_CACHE_DURATION=1800  # 应用层缓存
```

#### 3. 连接池调整
```python
# 在 db/pool.py 中调整
minconn=5  # 最小连接数
maxconn=20 # 最大连接数
```

## 安全建议

### 1. 生产环境配置
- 使用强密码和密钥
- 启用 HTTPS
- 设置防火墙规则
- 定期更新镜像
- 启用数据库加密

### 2. 访问控制
```bash
# 限制数据库访问
POSTGRES_HOST_AUTH_METHOD=scram-sha-256

# Redis 密码保护
REDIS_PASSWORD=your_redis_password

# API 速率限制
FUND_DAILY_RATE_LIMIT=100/分钟
```

### 3. 备份策略
```bash
# 每日完整备份
0 2 * * * docker-compose exec postgres pg_dumpall -U kid | gzip > /backups/fund_daily_$(date +\%Y\%m\%d).sql.gz

# 保留策略
find /backups -name "*.sql.gz" -mtime +30 -delete
```

## 扩展部署

### 1. Docker Swarm
```bash
# 初始化 Swarm
docker swarm init

# 部署堆栈
docker stack deploy -c docker-compose.yml fund-daily

# 查看服务
docker service ls
```

### 2. Kubernetes
```bash
# 生成 Kubernetes 配置
kompose convert -f docker-compose.yml

# 部署到 Kubernetes
kubectl apply -f fund-daily-postgres-service.yaml
kubectl apply -f fund-daily-backend-deployment.yaml
```

### 3. 云平台
- **AWS**: ECS + RDS + ElastiCache
- **Google Cloud**: GKE + Cloud SQL + Memorystore
- **Azure**: AKS + Azure SQL + Redis Cache

## 更新和升级

### 1. 更新代码
```bash
# 拉取最新代码
git pull origin main

# 重建服务
docker-compose build --no-cache
docker-compose up -d
```

### 2. 数据库迁移
```bash
# 创建迁移脚本
docker-compose exec backend python scripts/migrate.py

# 备份后升级
docker-compose exec db-exporter /backup.sh
docker-compose up -d --force-recreate backend
```

### 3. 版本回滚
```bash
# 回滚到特定版本
git checkout v2.5.0
docker-compose build
docker-compose up -d

# 恢复数据库备份
docker-compose exec -T postgres psql -U kid -d fund_daily < backup_v2.5.0.sql
```

## 支持与维护

### 1. 监控告警
- 设置 Prometheus 告警规则
- 配置 Grafana 通知渠道
- 监控关键指标:
  - 数据库连接数
  - API 响应时间
  - 错误率
  - 内存使用率

### 2. 定期维护
```bash
# 每周维护任务
docker system prune -f  # 清理未使用的资源
docker-compose exec postgres vacuumdb -U kid -d fund_daily  # 数据库维护
docker-compose exec redis redis-cli BGSAVE  # Redis 持久化
```

### 3. 性能测试
```bash
# API 压力测试
docker run --network fund-daily_fund-daily-network alpine/ab -n 1000 -c 10 http://backend:5000/api/funds

# 数据库性能测试
docker-compose exec postgres pgbench -U kid -i -s 10 fund_daily
```

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 联系方式

- **项目主页**: https://github.com/kid941005/fund-daily
- **问题跟踪**: https://github.com/kid941005/fund-daily/issues
- **文档**: https://github.com/kid941005/fund-daily/wiki

---

*最后更新: 2026-03-19*
*版本: Fund Daily v2.6.0*