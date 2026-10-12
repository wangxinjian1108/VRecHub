FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=skintokens

WORKDIR /SkinTokens

# The tail of the package list is the X/GL stack that bpy (Blender shipped as a
# python module) links against, plus open3d's GL dependency.
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
    libglu1-mesa \
    libegl1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxkbcommon0 \
    libsm6 \
    libice6 \
    libfontconfig1 \
    libfreetype6 \
    libdbus-1-3 \
    libasound2 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 and zh_CN.UTF-8 so bash / perl / python don't fall back to POSIX
RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && update-locale LANG=en_US.UTF-8

# Place ENV LANG/LC_ALL AFTER locale-gen, otherwise later RUN steps inherit
# LC_ALL=en_US.UTF-8 before the locale is generated and emit warnings.
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

COPY thirdparty/SkinTokens .

# The project pins torch 2.7.0 + CUDA 12.8 in its README; torchaudio is not used.
RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128 \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir -r requirements.txt \
    && conda run -n "${CONDA_ENV}" pip install --no-cache-dir "huggingface_hub[cli]"

# --- Model weights -----------------------------------------------------------
# download.py pulls the two TokenRig checkpoints (1.1 GB + 0.5 GB) into
# experiments/ and only the *config* of Qwen3-0.6B into models/Qwen3-0.6B - the
# LLM weights live inside grpo_1400.ckpt, so the base weights are not needed.
# Both repos are public, so no HF token is required; the secret is honoured when
# present to avoid anonymous rate limits.
RUN --mount=type=secret,id=hf_token,required=false \
    export HF_TOKEN="$(cat /run/secrets/hf_token 2>/dev/null || true)" \
    && conda run -n "${CONDA_ENV}" python download.py --model \
    && test -f experiments/articulation_xl_quantization_256_token_4/grpo_1400.ckpt \
    && test -f experiments/skin_vae_2_10_32768/last.ckpt \
    && test -f models/Qwen3-0.6B/config.json

# Fail the build (not just the container start) if the runtime stack is broken:
# bpy is the fragile one because it dlopens the X/GL libraries.
RUN conda run -n "${CONDA_ENV}" python -c "import bpy, torch, trimesh, transformers; print('skintokens ready:', torch.__version__, torch.version.cuda, bpy.app.version_string)"

CMD ["python", "-c", "import bpy, torch, trimesh, transformers; print('skintokens ready:', torch.__version__, torch.version.cuda, bpy.app.version_string)"]
