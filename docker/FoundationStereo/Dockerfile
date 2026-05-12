FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=foundation_stereo \
    OPENCV_IO_ENABLE_OPENEXR=1

WORKDIR /FoundationStereo

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    wget \
    unzip \
    bzip2 \
    ca-certificates \
    openssh-server \
    htop \
    rsync \
    ffmpeg \
    curl \
    cmake \
    make \
    less \
    g++ \
    ninja-build \
    build-essential \
    tmux \
    locales \
    nano \
    net-tools \
    sudo \
    pciutils \
    libgl1 \
    libglib2.0-0 \
    libturbojpeg0-dev \
    && rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.11 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh && ssh-keygen -A

ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}

COPY thirdparty/FoundationStereo .

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
        --index-url https://download.pytorch.org/whl/cu124

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        scikit-image omegaconf opencv-contrib-python imgaug ninja timm \
        albumentations scipy joblib scikit-learn ruamel.yaml trimesh \
        pyyaml imageio open3d transformations einops gdown \
        huggingface-hub xformers==0.0.28.post1

RUN conda run -n "${CONDA_ENV}" pip install --no-cache-dir \
        flash-attn --no-build-isolation

CMD ["python", "scripts/run_demo.py"]
