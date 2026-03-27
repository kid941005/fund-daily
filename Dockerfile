# Fund Daily Dockerfile - 前后端一体
# Version: 2.7.10

FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 可选：CPU-only PyTorch
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu || true

# 复制应用代码
COPY src/ ./src/
COPY db/ ./db/
COPY web/api_fastapi/ ./web/api_fastapi/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY VERSION .
COPY cron.sh ./

# 复制预构建的前端（由 GitHub Actions 构建）
COPY dist ./dist

# 创建目录
RUN mkdir -p /app/data /app/web

# 创建软链接（兼容旧路径）
RUN ln -sf /app/dist /app/web/dist

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
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
    FUND_DAILY_SERVER_PORT=5007 \
    FUND_DAILY_CORS_ORIGINS=*

EXPOSE 5007

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5007/health || exit 1

# 启动命令
CMD ["uvicorn", "web.api_fastapi.main:app", "--host", "0.0.0.0", "--port", "5007"]
