FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Pin numpy FIRST before anything else can pull 2.x
RUN pip install --no-cache-dir "numpy==1.26.4"

# CPU-only torch
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.0+cpu torchvision==0.17.0+cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# sentence-transformers after torch and numpy are locked
RUN pip install --no-cache-dir sentence-transformers==2.7.0

COPY app/ ./app/

ENV ARTIFACTS_DIR=/artifacts \
    PROCESSED_DIR=/data \
    MODEL_DIR=/models \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
