# Fund Daily Dockerfile - Optimized
# Multi-stage build for smaller image

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

# Install CPU-only PyTorch first (to avoid installing CUDA version)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Download EasyOCR models (automatic in v1.7+)
RUN pip install --no-cache-dir easyocr && \
    python -c "from easyocr import Reader; Reader(['ch_sim', 'en'], gpu=False)" && \
    rm -rf ~/.cache ~/.local

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

# Copy EasyOCR models from builder
COPY --from=builder /root/.EasyOCR /root/.EasyOCR

# Copy application files
COPY src/ ./src/
COPY web/ ./web/
COPY scripts/ ./scripts/
COPY db/ ./db/
COPY config/ ./config/
COPY VERSION ./
COPY cron.sh ./

# Create data directory
RUN mkdir -p /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=web/app.py \
    FUND_DAILY_DB_TYPE=postgres \
    FUND_DAILY_DB_HOST=postgres \
    FUND_DAILY_DB_PORT=5432 \
    FUND_DAILY_DB_NAME=fund_daily \
    FUND_DAILY_DB_USER=kid \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_TTL=1800 \
    FUND_DAILY_CACHE_DURATION=1800

EXPOSE 5000

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
