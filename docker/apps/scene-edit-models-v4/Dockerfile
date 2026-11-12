# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/scene-edit-models-v3:latest
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CUDA_HOME=/usr/local/cuda \
    MAX_JOBS=4

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    libopenexr-dev \
    && rm -rf /var/lib/apt/lists/*

# TRELLIS.2 keeps its own stack (torch 2.6 cu124 + compiled extensions).
RUN "${CONDA_DIR}/bin/conda" create -n trellis2 python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

COPY thirdparty/TRELLIS.2 /app/TRELLIS.2

# setup.sh installs every inference extension documented by TRELLIS.2:
# flash-attn, nvdiffrast, nvdiffrec, CuMesh, FlexGEMM and o-voxel.
RUN conda run -n trellis2 pip install --no-cache-dir \
        torch==2.6.0 torchvision==0.21.0 \
        --index-url https://download.pytorch.org/whl/cu124 \
    && conda run -n trellis2 pip install --no-cache-dir --no-build-isolation \
        "flash-attn==2.7.3" \
    && bash -lc 'source "${CONDA_DIR}/etc/profile.d/conda.sh" \
        && conda activate trellis2 \
        && cd /app/TRELLIS.2 \
        && sed -i "/pip install pillow-simd/d" setup.sh \
        && . ./setup.sh --basic --flash-attn --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm' \
    && conda clean -afy

COPY --chmod=755 docker/apps/scene-edit-models-v4/trellis2-python.sh /usr/local/bin/trellis2-python
COPY --chmod=755 docker/apps/scene-edit-models-v4/smoke-test.sh /usr/local/bin/scene-edit-v4-smoke-test

RUN scene-edit-v4-smoke-test

CMD ["/bin/bash"]
