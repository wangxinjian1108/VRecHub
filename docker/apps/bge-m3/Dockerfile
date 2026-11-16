FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=4 \
    BGE_M3_MODEL_PATH=/models/bge-m3 \
    BGE_M3_DEVICE=cpu \
    BGE_M3_BATCH_SIZE=8 \
    BGE_M3_MAX_LENGTH=8192 \
    BGE_M3_MAX_TEXTS=128 \
    BGE_M3_PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY docker/apps/bge-m3/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        "torch==2.6.0+cpu" \
    && python -m pip install -r /tmp/requirements.txt

COPY docker/apps/bge-m3/model.lock.json docker/apps/bge-m3/download-model.py /app/
RUN python /app/download-model.py \
        --root /models/bge-m3 \
        --revision 5617a9f61b028005a4858fdac845db406aefb181

COPY docker/apps/bge-m3/bge_m3.py docker/apps/bge-m3/cli.py \
     docker/apps/bge-m3/server.py docker/apps/bge-m3/smoke-test.py /app/
COPY --chmod=755 docker/apps/bge-m3/bge-m3-embed.sh /usr/local/bin/bge-m3-embed
COPY --chmod=755 docker/apps/bge-m3/bge-m3-server.sh /usr/local/bin/bge-m3-server

RUN python /app/smoke-test.py

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health'))['status'] == 'ok'"

CMD ["bge-m3-server"]
