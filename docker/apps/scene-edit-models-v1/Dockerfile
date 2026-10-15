# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda

WORKDIR /app

# The tail of the package list is the X/GL stack that bpy (Blender shipped as a
# python module) links against, plus open3d's GL dependency.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    zsh \
    vim \
    git-lfs \
    wget \
    unzip \
    bzip2 \
    ca-certificates \
    openssh-server \
    clang-format \
    htop \
    iotop \
    rsync \
    ffmpeg \
    curl \
    cmake \
    make \
    less \
    time \
    sqlite3 \
    tree \
    gdb \
    g++ \
    ninja-build \
    build-essential \
    tmux \
    locales \
    lsb-release \
    nano \
    nethogs \
    net-tools \
    valgrind \
    xz-utils \
    sudo \
    pciutils \
    libglib2.0-0 \
    libgl1 \
    libglu1-mesa \
    libegl1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxkbcommon0 \
    libsm6 \
    libice6 \
    libfontconfig1 \
    libfreetype6 \
    libdbus-1-3 \
    libasound2 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 and zh_CN.UTF-8 so bash / perl / python don't fall back to POSIX
RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && update-locale LANG=en_US.UTF-8

# Place ENV LANG/LC_ALL AFTER locale-gen, otherwise later RUN steps inherit
# LC_ALL=en_US.UTF-8 before the locale is generated and emit warnings.
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" create -n skintokens python=3.11 -y \
    && "${CONDA_DIR}/bin/conda" create -n qwen3-vl python=3.11 -y \
    && "${CONDA_DIR}/bin/conda" init bash \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh \
    && ssh-keygen -A

ENV PATH=${CONDA_DIR}/bin:/opt/blender:${PATH}

# Standalone Blender and the SkinTokens bpy wheel use the same release.
ARG BLENDER_VERSION=4.5.3
ARG BLENDER_SHA256=975c58fcb244273838534bba771e64ad87739216b0f9b39a888531a49a72d845
RUN curl -fL --retry 3 \
        "https://download.blender.org/release/Blender4.5/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
        -o /tmp/blender.tar.xz \
    && echo "${BLENDER_SHA256}  /tmp/blender.tar.xz" | sha256sum -c - \
    && mkdir -p /opt/blender \
    && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm /tmp/blender.tar.xz

COPY docker/apps/scene-edit-models-v1/constraints-skintokens.txt /opt/constraints/skintokens.txt
COPY docker/apps/scene-edit-models-v1/check-skintokens-dependencies.py /opt/constraints/check-skintokens-dependencies.py
COPY thirdparty/SkinTokens /app/skintokens
RUN conda run -n skintokens pip install --no-cache-dir \
        torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128 \
    && conda run -n skintokens pip install --no-cache-dir \
        -c /opt/constraints/skintokens.txt -r /app/skintokens/requirements.txt \
    && conda run -n skintokens python /opt/constraints/check-skintokens-dependencies.py

# vLLM 0.11.0 requires torch 2.8.0 / torchvision 0.23.0. Keep this stack
# isolated from SkinTokens; torchcodec 0.7 is paired with torch 2.8.
COPY thirdparty/Qwen3-VL /app/qwen3-vl
RUN conda run -n qwen3-vl pip install --no-cache-dir \
        torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 \
        --index-url https://download.pytorch.org/whl/cu128 \
    && conda run -n qwen3-vl pip install --no-cache-dir \
        vllm==0.11.0 transformers==4.57.6 accelerate \
        gradio==5.49.1 gradio_client==1.13.3 \
        transformers-stream-generator==0.0.5 torchcodec==0.7.0 \
    && conda run -n qwen3-vl pip install --no-cache-dir -e /app/qwen3-vl/qwen-vl-utils \
    && conda run -n qwen3-vl pip check

# Checkpoints and Hugging Face model configs are supplied as runtime mounts.
RUN mkdir -p /opt/var/models /app/skintokens/experiments /app/skintokens/models

COPY --chmod=755 docker/apps/scene-edit-models-v1/smoke-test.sh /usr/local/bin/scene-edit-smoke-test
RUN scene-edit-smoke-test

CMD ["/bin/bash"]
