# Fund Daily Dockerfile - 包含前后端
# Multi-stage build: 前端构建 + 后端运行
# Version: 2.7.4

# ============== Stage 1: 前端构建 ==============
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# 复制前端代码
COPY web/vue3/package*.json ./
COPY web/vue3/*.json ./
COPY web/vue3/src/ ./src/
COPY web/vue3/index.html ./
COPY web/vue3/public/ ./public/
COPY web/vue3/vite.config.ts ./

# 安装依赖并构建
RUN npm ci && npm run build

# ============== Stage 2: 后端构建 ==============
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 可选：CPU-only PyTorch
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu || true

# ============== Stage 3: 运行时 ==============
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制 Python 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY src/ ./src/
COPY db/ ./db/
COPY web/api_fastapi/ ./web/api_fastapi/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY VERSION .
COPY cron.sh ./

# 从前端构建阶段复制 dist 目录
COPY --from=frontend-builder /app/dist ./dist

# 创建目录
RUN mkdir -p /app/data /app/web

# 创建软链接（兼容旧路径）
RUN ln -sf /app/dist /app/web/dist

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    FUND_DAILY_DB_TYPE=postgres \
    FUND_DAILY_DB_HOST=postgres \
    FUND_DAILY_DB_PORT=5432 \
    FUND_DAILY_DB_NAME=fund_daily \
    FUND_DAILY_DB_USER=kid \
    FUND_DAILY_REDIS_HOST=redis \
    FUND_DAILY_REDIS_PORT=6379 \
    FUND_DAILY_REDIS_DB=0 \
    FUND_DAILY_REDIS_TTL=1800 \
    FUND_DAILY_CACHE_DURATION=1800 \
    FUND_DAILY_CORS_ORIGINS=*

EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 启动命令
CMD ["uvicorn", "web.api_fastapi.main:app", "--host", "0.0.0.0", "--port", "5000"]
