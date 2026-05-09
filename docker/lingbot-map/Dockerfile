FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=lingbot-map

WORKDIR /lingbot-map

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

COPY thirdparty/lingbot-map .

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -e ".[vis]" \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        flashinfer-python --index-url https://pypi.org/simple \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir onnxruntime-gpu \
    && rm -rf example assets lingbot-map_paper.pdf

# --- Model download ---
RUN --mount=type=secret,id=hf_token \
    mkdir -p /opt/var/models/lingbot-map && \
    huggingface-cli download robbyant/lingbot-map \
        --local-dir /opt/var/models/lingbot-map \
        --token $(cat /run/secrets/hf_token)

RUN mkdir -p /opt/var/models/skyseg && \
    curl -L https://huggingface.co/JianyuanWang/skyseg/resolve/main/skyseg.onnx \
        -o /opt/var/models/skyseg/skyseg.onnx

CMD ["python", "-c", "import lingbot_map; print('ready')"]
