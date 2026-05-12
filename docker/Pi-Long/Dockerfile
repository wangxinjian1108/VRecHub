FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=pi-long

WORKDIR /Pi-Long

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
    libopencv-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh && ssh-keygen -A

ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}

COPY thirdparty/Pi-Long .

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -r requirements.txt \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir --no-build-isolation . \
    && rm -rf assets

# --- Model download ---
RUN mkdir -p /opt/var/models/Pi-Long && \
    wget -O /opt/var/models/Pi-Long/dino_salad.ckpt "https://github.com/serizba/salad/releases/download/v1.0.0/dino_salad.ckpt" && \
    wget -O /opt/var/models/Pi-Long/dinov2_vitb14_pretrain.pth "https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14/dinov2_vitb14_pretrain.pth" && \
    wget -O /opt/var/models/Pi-Long/pi3.safetensors "https://huggingface.co/yyfz233/Pi3/resolve/main/model.safetensors" && \
    wget -O /opt/var/models/Pi-Long/pi3X.safetensors "https://huggingface.co/yyfz233/Pi3X/resolve/main/model.safetensors"

CMD ["python", "pi_long.py", "--help"]
