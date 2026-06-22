FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda

WORKDIR /app

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
    libarchive-tools \
    netcat-openbsd \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libturbojpeg0-dev \
    && rm -rf /var/lib/apt/lists/*

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
    && "${CONDA_DIR}/bin/conda" init bash \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh \
    && ssh-keygen -A

ENV PATH=${CONDA_DIR}/bin:${PATH}

RUN conda create -n fast-foundationstereo python=3.12 -y \
 && conda create -n pi3                python=3.10 -y \
 && conda create -n vggt-omega         python=3.10 -y \
 && conda create -n sam3               python=3.12 -y \
 && conda clean -afy

COPY thirdparty/Fast-FoundationStereo /app/fast-foundationstereo

RUN conda run -n fast-foundationstereo pip install --no-cache-dir \
        torch==2.6.0 torchvision==0.21.0 xformers \
        --index-url https://download.pytorch.org/whl/cu124 \
 && conda run -n fast-foundationstereo pip install --no-cache-dir \
        -r /app/fast-foundationstereo/requirements.txt

COPY thirdparty/Pi3 /app/pi3

RUN conda run -n pi3 pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124 \
 && conda run -n pi3 pip install --no-cache-dir -r /app/pi3/requirements.txt \
 && conda run -n pi3 pip install --no-cache-dir -e /app/pi3 \
 && rm -rf /app/pi3/assets

COPY thirdparty/vggt-omega /app/vggt-omega

RUN conda run -n vggt-omega pip install --no-cache-dir \
        torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126 \
 && conda run -n vggt-omega pip install --no-cache-dir -r /app/vggt-omega/requirements.txt \
 && conda run -n vggt-omega pip install --no-cache-dir -e /app/vggt-omega

COPY thirdparty/sam3 /app/sam3

RUN conda run -n sam3 pip install --no-cache-dir \
        torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128 \
 && conda run -n sam3 pip install --no-cache-dir -e "/app/sam3[notebooks]" \
 && conda run -n sam3 pip install --no-cache-dir einops ninja \
 && conda run -n sam3 pip install --no-cache-dir flash-attn-3 --no-deps --index-url https://download.pytorch.org/whl/cu128 \
 && rm -rf /app/sam3/examples /app/sam3/assets

RUN mkdir -p /opt/var/models

CMD ["/bin/bash"]
