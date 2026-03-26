# Fund Daily Dockerfile - Optimized
# Multi-stage build for smaller image
# Version: 2.7.3

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install CPU-only PyTorch (optional, for ML features)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu || true

# Download EasyOCR models (optional, for OCR features)
# Disabled by default to speed up build. Enable if needed.
# RUN pip install --no-cache-dir easyocr && \
#     python -c "from easyocr import Reader; Reader(['ch_sim', 'en'], gpu=False)" && \
#     rm -rf ~/.cache ~/.local

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy EasyOCR models (if built in builder stage)
# COPY --from=builder /root/.EasyOCR /root/.EasyOCR

# Copy application files
# Core application
COPY src/ ./src/
COPY db/ ./db/

# API layer (FastAPI)
COPY web/api_fastapi/ ./web/api_fastapi/

# Scripts and migrations
COPY scripts/ ./scripts/

# Configuration
COPY config/ ./config/
COPY VERSION .
COPY cron.sh ./

# Create data directory
RUN mkdir -p /app/data

# 创建前端静态文件目录软链接
# vite 输出到 ./dist，backend 期望 web/dist
RUN ln -sf /app/dist /app/web/dist

# Environment variables
# Database
ENV PYTHONUNBUFFERED=1 \
    FUND_DAILY_DB_TYPE=postgres \
    FUND_DAILY_DB_HOST=postgres \
    FUND_DAILY_DB_PORT=5432 \
    FUND_DAILY_DB_NAME=fund_daily \
    FUND_DAILY_DB_USER=kid \
    # Redis (统一使用 FUND_DAILY_ 前缀)
    FUND_DAILY_REDIS_HOST=redis \
    FUND_DAILY_REDIS_PORT=6379 \
    FUND_DAILY_REDIS_DB=0 \
    FUND_DAILY_REDIS_TTL=1800 \
    # 缓存配置
    FUND_DAILY_CACHE_DURATION=1800 \
    # JWT 配置（生产环境必须设置）
    # FUND_DAILY_JWT_SECRET=your-secret-key-here \
    # CORS 配置
    FUND_DAILY_CORS_ORIGINS=*

EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动命令
CMD ["uvicorn", "web.api_fastapi.main:app", "--host", "0.0.0.0", "--port", "5000"]
