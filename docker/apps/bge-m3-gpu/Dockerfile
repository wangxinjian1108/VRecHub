FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    BGE_M3_MODEL_PATH=/models/bge-m3 \
    BGE_M3_DEVICE=cuda \
    BGE_M3_USE_FP16=true \
    BGE_M3_BATCH_SIZE=16 \
    BGE_M3_MAX_LENGTH=8192 \
    BGE_M3_MAX_TEXTS=128 \
    BGE_M3_PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates libgomp1 python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY docker/apps/bge-m3/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --upgrade pip setuptools wheel \
    && python3 -m pip install \
        --index-url https://download.pytorch.org/whl/cu124 \
        --extra-index-url https://pypi.org/simple \
        "torch==2.6.0+cu124" \
    && python3 -m pip install -r /tmp/requirements.txt \
    && python3 -c "import torch; assert torch.backends.cuda.is_built(); assert torch.version.cuda == '12.4', torch.version.cuda"

COPY docker/apps/bge-m3/model.lock.json docker/apps/bge-m3/download-model.py /app/
RUN python3 /app/download-model.py \
        --root /models/bge-m3 \
        --revision 5617a9f61b028005a4858fdac845db406aefb181

COPY docker/apps/bge-m3/bge_m3.py docker/apps/bge-m3/cli.py \
     docker/apps/bge-m3/server.py docker/apps/bge-m3/smoke-test.py \
     docker/apps/bge-m3/gpu-smoke-test.py /app/
COPY --chmod=755 docker/apps/bge-m3/bge-m3-embed.sh /usr/local/bin/bge-m3-embed
COPY --chmod=755 docker/apps/bge-m3/bge-m3-server.sh /usr/local/bin/bge-m3-server

# Hosted GitHub runners have no GPU. Validate model inference on CPU and verify
# that the installed wheel was compiled with CUDA; gpu-smoke-test.py must pass
# on the target GPU before deployment.
RUN BGE_M3_DEVICE=cpu BGE_M3_USE_FP16=false python3 /app/smoke-test.py

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python3 -c "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health'))['status'] == 'ok'"

CMD ["bge-m3-server"]
