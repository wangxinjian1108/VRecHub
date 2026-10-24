# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/scene-edit-models-v2:latest
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda

WORKDIR /app

# v3 = v2 (SkinTokens + Qwen3-VL + Blender + GVHMR + Motion2MixamoRig) + Kimodo.
# Kimodo needs transformers 5.1.0 and therefore its own env.
RUN "${CONDA_DIR}/bin/conda" create -n kimodo python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

COPY thirdparty/kimodo /app/kimodo
RUN conda run -n kimodo pip install --no-cache-dir --upgrade pip setuptools wheel \
    && conda run -n kimodo pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cu124 \
    && conda run -n kimodo pip install --no-cache-dir -e /app/kimodo \
    && conda run -n kimodo pip check \
    && conda clean -afy

COPY --chmod=755 docker/apps/scene-edit-models-v3/kimodo-gen.sh /usr/local/bin/kimodo-gen
COPY --chmod=755 docker/apps/scene-edit-models-v3/smoke-test.sh /usr/local/bin/scene-edit-v3-smoke-test

RUN scene-edit-v3-smoke-test

CMD ["/bin/bash"]
