# syntax=docker/dockerfile:1
# Rebuild the upstream-pinned TorchRL 0.7 extension against HAIC's torch 2.7 ABI.
FROM python:3.11-slim-bullseye AS build
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 MAX_JOBS=1 TORCHRL_BUILD_VERSION=0.7.0
RUN apt-get update && apt-get install -y --no-install-recommends \
      git build-essential unzip \
    && rm -rf /var/lib/apt/lists/*
RUN pip install 'pip<25' 'setuptools>=70,<81' wheel ninja packaging numpy \
    && pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/cu128
RUN git clone https://github.com/pytorch/rl.git /tmp/torchrl \
    && git -C /tmp/torchrl checkout 3ff13ffb48343a6fd123e169b01bb55789e3ceeb \
    && cd /tmp/torchrl \
    && pip wheel --no-deps --no-build-isolation -w /tmp/wheels . \
    && test "$(find /tmp/wheels -maxdepth 1 -name '*.whl' | wc -l)" -eq 1 \
    && mkdir /output \
    && unzip -j /tmp/wheels/*.whl 'torchrl/_torchrl.so' -d /output \
    && python -c 'import torch; torch.ops.load_library("/output/_torchrl.so"); print("TorchRL extension loaded against torch", torch.__version__)'

FROM scratch
COPY --from=build /output/_torchrl.so /opt/conda/envs/haic/lib/python3.11/site-packages/torchrl/_torchrl.so
