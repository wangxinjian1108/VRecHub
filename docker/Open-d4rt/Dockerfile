FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=Open-d4rt

WORKDIR /Open-d4rt

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
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh \
    && ssh-keygen -A

ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}

COPY thirdparty/Open-d4rt .

# requirements.txt pins torch==2.6.0+cu124 with --extra-index-url to PyTorch's CUDA 12.4 wheel index.
RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir -r requirements.txt

# --- Model download (HuggingFace public repo Lijiaxin0111/OpenD4RT) ---
RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir "huggingface_hub[cli]" \
    && mkdir -p /opt/var/models/Open-d4rt \
    && conda run -n "${CONDA_ENV}" hf download Lijiaxin0111/OpenD4RT \
         --repo-type model --local-dir /opt/var/models/Open-d4rt \
         --include "checkpoints/OpenD4RT_32CLIP_9Dataset_NoAUG/opend4rt.ckpt" \
         --include "checkpoints/OpenD4RT_32CLIP_9Dataset_NoAUG/model.yaml" \
         --include "checkpoints/OpenD4RT_48CLIP_9Mix_NoCropAUG/opend4rt.ckpt" \
         --include "checkpoints/OpenD4RT_48CLIP_9Mix_NoCropAUG/model.yaml"

CMD ["python", "-c", "import torch; print('Open-d4rt ready, torch', torch.__version__)"]
