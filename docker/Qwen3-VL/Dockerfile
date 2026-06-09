FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=Qwen3-VL

WORKDIR /Qwen3-VL

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
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 and zh_CN.UTF-8 so bash / perl / python don't fall back to POSIX.
# Place ENV LANG/LC_ALL AFTER locale-gen, otherwise later RUN steps inherit
# LC_ALL=en_US.UTF-8 before the locale is generated and emit warnings.
RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && update-locale LANG=en_US.UTF-8

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.11 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh \
    && ssh-keygen -A

ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}

COPY thirdparty/Qwen3-VL .

# Install torch (cu128) first, then vllm + web-demo deps + qwen-vl-utils.
# vllm brings transformers as a dependency; pin >= 4.57.0 for Qwen3-VL compat.
RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch torchvision --index-url https://download.pytorch.org/whl/cu128 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        "vllm>=0.11.0" \
        "transformers>=4.57.0" \
        accelerate \
        gradio==5.49.1 \
        gradio_client==1.13.3 \
        transformers-stream-generator==0.0.5 \
        torchcodec==0.7 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -e ./qwen-vl-utils

CMD ["python", "-c", "import vllm, transformers, qwen_vl_utils; print('Qwen3-VL ready, vllm', vllm.__version__, 'transformers', transformers.__version__)"]
