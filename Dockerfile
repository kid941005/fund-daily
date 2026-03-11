FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ ./web/
COPY scripts/fund-daily.py ./scripts/
COPY db/ ./db/

RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web/app.py

EXPOSE 5000

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
