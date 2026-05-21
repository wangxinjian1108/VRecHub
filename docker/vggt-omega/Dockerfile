FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=vggt-omega

WORKDIR /vggt-omega

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
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 and zh_CN.UTF-8 so bash / perl / python don't fall back to POSIX
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

COPY thirdparty/vggt-omega .

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -r requirements.txt \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -e .

# --- Model download (HuggingFace gated repo facebook/VGGT-Omega) ---
RUN --mount=type=secret,id=hf_token \
    conda run -n "${CONDA_ENV}" pip install --no-cache-dir "huggingface_hub[cli]" \
    && mkdir -p /opt/var/models/vggt-omega \
    && conda run -n "${CONDA_ENV}" hf download facebook/VGGT-Omega vggt_omega_1b_512.pt \
         --repo-type model --local-dir /opt/var/models/vggt-omega \
         --token $(cat /run/secrets/hf_token)

CMD ["python", "-c", "from vggt_omega.models import VGGTOmega; print('ready')"]
