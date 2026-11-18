FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=pi4

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash build-essential ca-certificates cmake curl ffmpeg git git-lfs \
    htop libgl1 libglib2.0-0 locales nano ninja-build openssh-client \
    pciutils rsync sudo tmux unzip vim wget xz-utils zsh \
    && rm -rf /var/lib/apt/lists/* \
    && locale-gen en_US.UTF-8 zh_CN.UTF-8

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.11 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy
ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH} \
    HF_HOME=/root/.cache/huggingface

WORKDIR /Pi4
COPY thirdparty/Pi4/ /Pi4/
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-cu126.txt \
    && python -m pip check \
    && python -c "import torch, triton, cv2, flex_gemm; from pi4 import Pi4; assert torch.version.cuda == '12.6'; print('PyTorch:', torch.__version__, 'CUDA:', torch.version.cuda, 'Triton:', triton.__version__)" \
    && python example.py --help >/dev/null

CMD ["python", "example.py", "--help"]
