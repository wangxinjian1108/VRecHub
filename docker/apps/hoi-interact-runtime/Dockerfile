# syntax=docker/dockerfile:1
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda CUDA_HOME=/usr/local/cuda \
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0+PTX" FORCE_CUDA=1 MAX_JOBS=2
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends git curl wget bzip2 ca-certificates build-essential ninja-build libgl1 libglib2.0-0 libspatialindex-dev && rm -rf /var/lib/apt/lists/*
RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
 && bash /tmp/miniconda.sh -b -p "$CONDA_DIR" && rm /tmp/miniconda.sh \
 && "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
 && "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r \
 && "$CONDA_DIR/bin/conda" create -n interact python=3.8 -y && "$CONDA_DIR/bin/conda" clean -afy
ENV PATH=/opt/conda/envs/interact/bin:/opt/conda/bin:$PATH
WORKDIR /app/InterAct
COPY thirdparty/InterAct/ /app/InterAct/
COPY docker/apps/hoi-interact-runtime/constraints.txt /tmp/constraints.txt
RUN pip install 'pip<25' 'setuptools==69.5.1' wheel ninja \
 && pip install torch==2.0.0 torchvision==0.15.1 torchaudio==2.0.1 --index-url https://download.pytorch.org/whl/cu118 \
 && pip install fvcore iopath 'numpy==1.23.1' \
 && pip install --no-build-isolation 'git+https://github.com/facebookresearch/pytorch3d.git@v0.7.4' \
 && conda clean -afy
 && pip install -c /tmp/constraints.txt -r requirements.txt \
 && pip install --no-deps --ignore-requires-python 'git+https://github.com/nghorbani/human_body_prior.git@4c246d8a83ce16d3cff9c79dcf04d81fa440a6bc' \
 && pip install 'loguru<0.8' 'omegaconf==2.3.0' \
 && python -m spacy download en_core_web_sm \
 && git clone https://github.com/erikwijmans/Pointnet2_PyTorch.git /tmp/pointnet2 \
 && git -C /tmp/pointnet2 checkout b5ceb6d9ca0467ea34beb81023f96ee82228f626 \
 && pip install --no-build-isolation /tmp/pointnet2/pointnet2_ops_lib \
 && rm -rf /tmp/pointnet2 \
 && pip check \
 && python -c 'import torch, pytorch3d, pointnet2_ops._ext, spacy; from human_body_prior.tools import tgm_conversion; assert spacy.load("en_core_web_sm"); print("InterAct environment ready", torch.__version__)'
CMD ["bash"]
