# Fund Daily 部署指南

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 硬件: 2GB+ RAM, 10GB+ 磁盘

## 快速部署

### 1. 准备环境

```bash
# 创建目录
mkdir -p ~/fund-daily && cd ~/fund-daily

# 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/kid941005/fund-daily/main/docker-compose.yml

# 下载数据库初始化脚本
curl -O https://raw.githubusercontent.com/kid941005/fund-daily/main/db/init.sql

# 创建环境变量文件
cat > .env << 'EOF'
POSTGRES_PASSWORD=your_strong_postgres_password
FUND_DAILY_JWT_SECRET=your_jwt_secret_key_at_least_32_characters
FUND_DAILY_SECRET_KEY=your_secret_key_at_least_32_characters
FUND_DAILY_DB_PASSWORD=your_postgres_password
EOF
```

### 2. 启动服务

```bash
# 启动所有服务（自动拉取镜像）
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 3. 访问服务

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5007 |
| 后端 API | http://localhost:5007 |
| API 文档 | http://localhost:5007/api/docs |

## 生产环境部署

### 1. 服务器准备

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
apt-get update
apt-get install -y docker-compose
```

### 2. 配置域名 (可选)

如需域名访问，配置 `.env`:

```bash
FUND_DAILY_CORS_ORIGINS=https://your-domain.com
```

### 3. 数据持久化

数据库数据存储在 Docker volume 中:
- `postgres_data` - PostgreSQL 数据
- `redis_data` - Redis 缓存

### 4. 备份

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U kid fund_daily > backup.sql

# 备份 Redis 数据
docker-compose exec redis redis-cli AUTH your_password SAVE
docker cp fund-daily-redis:/data/dump.rdb ./redis-backup.rdb
```

## 维护命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新版本
git pull origin main
docker-compose up -d --build

# 清理旧镜像
docker-compose down --rmi old
docker image prune -f
```

## 故障排查

### 服务无法启动

```bash
# 查看日志
docker-compose logs postgres
docker-compose logs redis
docker-compose logs backend

# 检查端口占用
netstat -tlnp | grep -E '5432|6379|5000|80'
```

### 数据库连接失败

```bash
# 检查 postgres 状态
docker-compose exec postgres pg_isready

# 重新初始化数据库
docker-compose down -v
docker-compose up -d
```

### 前端无法访问 API

```bash
# 检查 backend 是否正常运行
docker-compose exec backend curl http://localhost:5000/api/health

# 检查 nginx 日志
docker-compose logs frontend
```

## 目录结构

部署后目录应包含：

```
~/fund-daily/
├── docker-compose.yml    # 编排配置（下载）
├── .env                  # 环境变量（手动创建）
├── init.sql              # 数据库初始化（下载）
└── dist/                 # 前端构建产物（容器内提供）
```

**注意**: 只需 3 个文件即可部署，无需克隆整个代码仓库。
