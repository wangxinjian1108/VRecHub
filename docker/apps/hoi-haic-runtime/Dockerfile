# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive CONDA_DIR=/opt/conda PIP_NO_CACHE_DIR=1 \
    ACCEPT_EULA=Y OMNI_KIT_ACCEPT_EULA=YES
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs wget curl bzip2 ca-certificates build-essential cmake ninja-build \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libvulkan1 vulkan-tools \
    libx11-6 libxrandr2 libxcursor1 libxi6 libxinerama1 libxkbcommon0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "$CONDA_DIR" && rm /tmp/miniconda.sh \
    && "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
    && "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r \
    && "$CONDA_DIR/bin/conda" create -n haic python=3.11 -y && "$CONDA_DIR/bin/conda" clean -afy
ENV PATH=/opt/conda/envs/haic/bin:/opt/conda/bin:$PATH
WORKDIR /app/HAIC
COPY thirdparty/HAIC/ /app/HAIC/
RUN pip install 'pip==25.3' 'setuptools==80.10.2' 'wheel==0.46.3' \
    && pip install 'isaacsim[all,extscache]==5.1.0' --extra-index-url https://pypi.nvidia.com \
    && git clone --depth 1 --branch v2.3.2 https://github.com/isaac-sim/IsaacLab.git /opt/IsaacLab \
    && pip install --no-build-isolation 'flatdict==4.0.1' \
    && /opt/IsaacLab/isaaclab.sh -i none \
    && pip install -e /app/HAIC \
    && pip install 'numpy==1.26.0' 'click==8.1.7' 'psutil==5.9.8' 'typing_extensions==4.12.2' 'websockets==12.0' 'wheel==0.45.1' \
    && pip install torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128 \
    && python -m pip check \
    && python -c 'import importlib.util; assert importlib.util.find_spec("isaaclab") and importlib.util.find_spec("isaacsim") and importlib.util.find_spec("active_adaptation"); print("HAIC dependencies installed")'
CMD ["bash"]
