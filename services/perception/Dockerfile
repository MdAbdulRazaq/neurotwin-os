FROM python:3.11-slim AS base

ARG USE_GPU=0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 ffmpeg curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Layer 1: Heavy ML — cached unless these versions change
RUN if [ "$USE_GPU" = "1" ]; then \
      pip install --no-cache-dir torch==2.1.0 transformers==4.36.0; \
    else \
      pip install --no-cache-dir torch==2.1.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir transformers==4.36.0; \
    fi

# Layer 2: Remaining deps
COPY requirements.txt .
RUN grep -vE '^(torch|transformers)==' requirements.txt > /tmp/req_filtered.txt \
    && pip install --no-cache-dir -r /tmp/req_filtered.txt

# Layer 3: App code
COPY services/common ./services/common
COPY app ./app

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]