# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/scene-edit-models-v4@sha256:b1bb26b01888399f88fc58e1dcf0d729f85c8acf0242cdf2e7732cff6d29864c
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive CONDA_DIR=/opt/conda \
    PIP_NO_CACHE_DIR=1 MPLBACKEND=Agg WANDB_MODE=disabled \
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0+PTX" FORCE_CUDA=1 MAX_JOBS=2
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglu1-mesa libegl1 libosmesa6 libsm6 libxext6 libxrender1 \
    libxi6 libxfixes3 libxrandr2 libxinerama1 libxcursor1 \
    libxkbcommon0 libfontconfig1 libfreetype6 \
    && rm -rf /var/lib/apt/lists/* \
    && conda create -n light python=3.10 -y \
    && conda clean -afy

COPY thirdparty/LIGHT /app/LIGHT
COPY docker/apps/scene-edit-models-v5/constraints-light.txt /tmp/constraints-light.txt

# LIGHT uses its own torch 2.5 / Python 3.10 environment and a matching
# PyTorch3D build; the conda environment provides a matching CUDA 12.4 compiler.
RUN conda run -n light pip install 'pip<25' 'setuptools==69.5.1' wheel ninja \
    && conda run -n light pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124 \
    && conda install -n light -c nvidia cuda-nvcc=12.4 cuda-cudart-dev=12.4 cuda-cccl=12.4 -y \
    && conda run -n light pip install fvcore iopath \
    && CUDA_HOME=/opt/conda/envs/light conda run -n light pip install --no-build-isolation 'git+https://github.com/facebookresearch/pytorch3d.git@v0.7.9' \
    && conda run -n light pip install -c /tmp/constraints-light.txt -r /app/LIGHT/requirements.txt \
    && conda run -n light pip check \
    && conda clean -afy

COPY --chmod=755 docker/apps/scene-edit-models-v5/smoke-test.sh /usr/local/bin/scene-edit-v5-smoke-test
RUN scene-edit-v5-smoke-test
WORKDIR /app
CMD ["/bin/bash"]
