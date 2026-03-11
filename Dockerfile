# 第一阶段：构建
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install EasyOCR deps (lightweight)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir easyocr && \
    rm -rf /root/.cache /root/.pip /tmp/pip-*

# 第二阶段：运行
FROM python:3.11-slim

WORKDIR /app

# Install runtime deps only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /app /app/

# Copy app files
COPY web/ ./web/
COPY scripts/fund-daily.py ./scripts/
COPY db/ ./db/

RUN mkdir -p /app/data

# Set version
ARG VERSION=latest
ENV VERSION=${VERSION}

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web/app.py
ENV FUND_DAILY_DB_PATH=/app/data/fund-daily.db

EXPOSE 5000

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
