# syntax=docker/dockerfile:1
# Rebuild the upstream-pinned TorchRL 0.7 extension against HAIC's torch 2.7 ABI.
FROM ubuntu:22.04 AS build
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 MAX_JOBS=1 TORCHRL_BUILD_VERSION=0.7.0 \
    CONDA_DIR=/opt/conda
RUN apt-get update && apt-get install -y --no-install-recommends \
      git build-essential unzip wget bzip2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "$CONDA_DIR" && rm /tmp/miniconda.sh \
    && "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
    && "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r \
    && "$CONDA_DIR/bin/conda" create -n build python=3.11 -y \
    && "$CONDA_DIR/bin/conda" clean -afy
ENV PATH=/opt/conda/envs/build/bin:/opt/conda/bin:$PATH
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
