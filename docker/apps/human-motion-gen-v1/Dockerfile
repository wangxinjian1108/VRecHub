# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    zsh \
    vim \
    wget \
    curl \
    unzip \
    bzip2 \
    ca-certificates \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    ffmpeg \
    rsync \
    tmux \
    htop \
    less \
    tree \
    locales \
    sudo \
    fonts-dejavu-core \
    libgl1 \
    libglu1-mesa \
    libegl1 \
    libgles2 \
    libosmesa6 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxfixes3 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxkbcommon0 \
    libfontconfig1 \
    libfreetype6 \
    libdbus-1-3 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && update-locale LANG=en_US.UTF-8

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" init bash \
    && "${CONDA_DIR}/bin/conda" create -n hy-motion python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" create -n ardy python=3.11 -y \
    && "${CONDA_DIR}/bin/conda" create -n kimodo python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

ENV PATH=${CONDA_DIR}/bin:${PATH}

# --------------------------------------------------------------------------
# HY-Motion 1.0  (torch 2.5.1 / transformers 4.53.3 / diffusers 0.26.3)
# --------------------------------------------------------------------------
# diffusers 0.26 still imports huggingface_hub.cached_download, which the repo's
# pinned hub 0.30 removed. 0.27.2 is the nearest API-compatible release
# (DDIMScheduler is the only diffusers symbol HY-Motion uses).
COPY thirdparty/HY-Motion-1.0 /app/HY-Motion-1.0
RUN conda run -n hy-motion pip install --no-cache-dir --upgrade pip setuptools wheel \
    && conda run -n hy-motion pip install --no-cache-dir \
        -r /app/HY-Motion-1.0/requirements.txt \
    && conda run -n hy-motion pip install --no-cache-dir "diffusers==0.27.2" \
    && conda run -n hy-motion pip check \
    && conda clean -afy

# --------------------------------------------------------------------------
# ARDY  (torch>=2.4 / transformers 5.8.1, builds a CMake extension)
# --------------------------------------------------------------------------
COPY thirdparty/ardy /app/ardy
RUN conda run -n ardy pip install --no-cache-dir --upgrade pip setuptools wheel \
    && conda run -n ardy pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cu124 \
    && conda run -n ardy pip install --no-cache-dir -e /app/ardy \
    && conda run -n ardy pip check \
    && conda clean -afy

# --------------------------------------------------------------------------
# Kimodo  (torch 2.5.x / transformers 5.1.0)
# --------------------------------------------------------------------------
COPY thirdparty/kimodo /app/kimodo
RUN conda run -n kimodo pip install --no-cache-dir --upgrade pip setuptools wheel \
    && conda run -n kimodo pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cu124 \
    && conda run -n kimodo pip install --no-cache-dir -e /app/kimodo \
    && conda run -n kimodo pip check \
    && conda clean -afy

# --------------------------------------------------------------------------
# DART  (python 3.8 / torch 2.1 cu118 / pytorch3d 0.7.5, exact environment.yml)
# --------------------------------------------------------------------------
COPY thirdparty/DART /app/DART
RUN cp /app/DART/environment.yml /tmp/dart-env.yml \
    && sed -i '/chumpy==0.70/d' /tmp/dart-env.yml \
    && "${CONDA_DIR}/bin/conda" env create -n dart -f /tmp/dart-env.yml \
    && conda run -n dart pip install --no-cache-dir --no-build-isolation "chumpy==0.70" \
    && conda clean -afy

COPY --chmod=755 docker/apps/human-motion-gen-v1/hy-motion-infer.sh /usr/local/bin/hy-motion-infer
COPY --chmod=755 docker/apps/human-motion-gen-v1/ardy-generate.sh /usr/local/bin/ardy-generate
COPY --chmod=755 docker/apps/human-motion-gen-v1/kimodo-gen.sh /usr/local/bin/kimodo-gen
COPY --chmod=755 docker/apps/human-motion-gen-v1/smoke-test.sh /usr/local/bin/human-motion-gen-smoke-test

RUN human-motion-gen-smoke-test

CMD ["/bin/bash"]
