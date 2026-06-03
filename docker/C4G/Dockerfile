FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=C4G

WORKDIR /C4G

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
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
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

# Build context is the repo root; copy C4G + its nested submodules (recursive checkout
# brings glm into the third_party/ tree, which the CUDA extension #include's).
COPY thirdparty/C4G .

# Set CUDA arch list for the Gaussian-rasterization CUDA extension build (no GPU at build time).
ENV TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6;8.9;9.0+PTX"

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.2.0+cu121 torchvision==0.17.0+cu121 --extra-index-url https://download.pytorch.org/whl/cu121 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -r requirements.txt \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir --no-build-isolation ./submodules/diff_gaussian_rasterization_w_pose \
    && rm -rf assets

# --- Model downloads (HuggingFace) ---
# C3G Gaussian decoder checkpoint (initialization weights for C4G) and C4G checkpoints.
RUN --mount=type=secret,id=hf_token \
    conda run -n "${CONDA_ENV}" pip install --no-cache-dir "huggingface_hub[cli]" \
    && mkdir -p /opt/var/models/C3G /opt/var/models/C4G \
    && conda run -n "${CONDA_ENV}" hf download honggyuAn/C3G gaussian_decoder.ckpt \
         --repo-type model --local-dir /opt/var/models/C3G \
         --token $(cat /run/secrets/hf_token) \
    && conda run -n "${CONDA_ENV}" hf download mungyeom011/C4G \
         --repo-type model --local-dir /opt/var/models/C4G \
         --token $(cat /run/secrets/hf_token)

CMD ["python", "-c", "import torch, diff_gaussian_rasterization; print('C4G ready, torch', torch.__version__)"]
