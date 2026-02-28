FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps - CPU-only torch first to avoid 2GB CUDA version
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.0+cpu torchvision==0.17.0+cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install sentence-transformers explicitly after torch to avoid CUDA dependency
RUN pip install --no-cache-dir sentence-transformers==2.7.0

# Copy app code
COPY app/ ./app/

ENV ARTIFACTS_DIR=/artifacts \
    PROCESSED_DIR=/data \
    MODEL_DIR=/models \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

