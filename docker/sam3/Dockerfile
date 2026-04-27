FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=sam3

WORKDIR /sam3

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
    && rm -rf /var/lib/apt/lists/*

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

COPY thirdparty/sam3 .

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -e ".[notebooks]" \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        einops ninja \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        flash-attn-3 --no-deps --index-url https://download.pytorch.org/whl/cu128 \
    && rm -rf examples assets

# --- HuggingFace model download ---
# SAM 3 / SAM 3.1 checkpoints — gated model, requires HF auth:
# RUN --mount=type=secret,id=hf_token \
#     HF_TOKEN=$(cat /run/secrets/hf_token) python -c \
#     "from huggingface_hub import snapshot_download; snapshot_download('facebook/sam3.1', local_dir='/models/sam3.1', token=open('/run/secrets/hf_token').read().strip())"
# ----------------------------------

CMD ["python", "-c", "import sam3; print(sam3.__version__)"]
