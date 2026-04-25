FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=scal3r

WORKDIR /Scal3R

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
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh \
    && ssh-keygen -A

ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}

COPY thirdparty/Scal3R .

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch torchvision --index-url https://download.pytorch.org/whl/cu128 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -r requirements.txt \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir . \
    && rm -rf requirements.txt scripts assets docs

# --- HuggingFace model download ---
# scal3r.pt — xbillowy/Scal3R 私有模型，通过 BuildKit secret 注入 HF token：
# RUN --mount=type=secret,id=hf_token \
#     mkdir -p data/checkpoints && \
#     HF_TOKEN=$(cat /run/secrets/hf_token) \
#     huggingface-cli download xbillowy/Scal3R scal3r.pt \
#         --repo-type model --local-dir data/checkpoints
#
# dino_salad.ckpt — 公开 GitHub release：
# RUN mkdir -p data/checkpoints && \
#     curl -L https://github.com/serizba/salad/releases/download/v1.0.0/dino_salad.ckpt \
#         -o data/checkpoints/dino_salad.ckpt
#
# 其他公开模型：
# RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('org/model-name', local_dir='/models/model-name')"
# 其他私有模型：
# RUN --mount=type=secret,id=hf_token \
#     HF_TOKEN=$(cat /run/secrets/hf_token) python -c \
#     "from huggingface_hub import snapshot_download; snapshot_download('org/model-name', local_dir='/models/model-name', token=open('/run/secrets/hf_token').read().strip())"
# ----------------------------------

CMD ["python", "-m", "scal3r.run", "--help"]
