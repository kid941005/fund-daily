FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy skill files
COPY scripts/fund-daily.py /app/fund-daily.py
COPY config/ /app/config/

# Make executable
RUN chmod +x /app/fund-daily.py

# Create data directory
RUN mkdir -p /app/data

# Set environment
ENV PYTHONUNBUFFERED=1
ENV FUND_DATA_PATH=/app/data

# Default command
ENTRYPOINT ["python3", "/app/fund-daily.py"]
CMD ["--help"]
