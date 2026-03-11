FROM python:3.11-slim

WORKDIR /app

# Install system dependencies in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY web/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install EasyOCR (CPU only, no CUDA)
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir easyocr && \
    rm -rf /root/.cache/torch/hub/checkpoints/*

# Copy application files
COPY web/ ./web/
COPY scripts/fund-daily.py ./scripts/
COPY db/ ./db/

RUN mkdir -p /app/data

# Set version from build-arg
ARG VERSION=latest
ENV VERSION=${VERSION}
RUN sed -i "s/VERSION = \".*\"/VERSION = \"${VERSION}\"/" web/app.py

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web/app.py
ENV FUND_DAILY_DB_PATH=/app/data/fund-daily.db

EXPOSE 5000

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
