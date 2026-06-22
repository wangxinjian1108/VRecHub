FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=Fast-FoundationStereo \
    OPENCV_IO_ENABLE_OPENEXR=1

WORKDIR /Fast-FoundationStereo

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
    libturbojpeg-dev \
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
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.12 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh \
    && ssh-keygen -A

ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}

COPY thirdparty/Fast-FoundationStereo .

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.6.0 torchvision==0.21.0 xformers \
        --index-url https://download.pytorch.org/whl/cu124 \
 && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -r requirements.txt

CMD ["python", "scripts/run_demo.py", "--help"]
