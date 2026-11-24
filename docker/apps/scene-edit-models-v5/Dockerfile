# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/scene-edit-models-v4@sha256:b1bb26b01888399f88fc58e1dcf0d729f85c8acf0242cdf2e7732cff6d29864c
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive CONDA_DIR=/opt/conda \
    PIP_NO_CACHE_DIR=1 MPLBACKEND=Agg WANDB_MODE=disabled \
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0+PTX" FORCE_CUDA=1 MAX_JOBS=2
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglu1-mesa libegl1 libosmesa6 libsm6 libxext6 libxrender1 \
    libxi6 libxfixes3 libxrandr2 libxinerama1 libxcursor1 \
    libxkbcommon0 libfontconfig1 libfreetype6 libopenmesh-dev \
    && rm -rf /var/lib/apt/lists/* \
    && conda create -n interpose python=3.8 -y \
    && conda create -n protomotions_interpose python=3.8 -y \
    && conda create -n light python=3.10 -y \
    && conda clean -afy

COPY thirdparty/InterPose /app/InterPose
COPY thirdparty/LIGHT /app/LIGHT
COPY docker/apps/scene-edit-models-v5/constraints-light.txt /tmp/constraints-light.txt

# InterPose's own preprocessing stack, matching its upstream install script.
RUN conda run -n interpose pip install 'pip<25' 'setuptools==69.5.1' wheel \
    && conda run -n interpose pip install torch==2.0.0 torchvision==0.15.1 torchaudio==2.0.1 --index-url https://download.pytorch.org/whl/cu117 \
    && conda run -n interpose pip install 'numpy==1.23.5' fvcore iopath ninja tqdm dotmap PyYAML omegaconf loguru \
    && conda run -n interpose pip install --no-index pytorch3d==0.7.3 -f https://dl.fbaipublicfiles.com/pytorch3d/packaging/wheels/py38_cu117_pyt200/download.html \
    && conda run -n interpose pip install \
      'human-body-prior @ git+https://github.com/nghorbani/human_body_prior.git@4c246d8a83ce16d3cff9c79dcf04d81fa440a6bc' \
      'chamfer-distance @ git+https://github.com/otaheri/chamfer_distance.git@f86f6f7cadd3aca642704573d1626c67ca2e2846' \
      'bps-torch @ git+https://github.com/otaheri/bps_torch.git@00fcac3dffd294211d4ea0363eaf6c2ca4e068dc' \
    && conda run -n interpose pip install -r /app/InterPose/requirements.txt 'numpy==1.23.5' \
    && conda run -n interpose pip check

# Isaac Gym Preview 4 is installed from NVIDIA, as required by InterPose's
# pinned ProtoMotion fork. Its assets and checkpoints are supplied at runtime.
RUN curl -fL --retry 3 --connect-timeout 30 https://developer.nvidia.com/isaac-gym-preview-4 -o /tmp/isaac-gym.tar.gz \
    && tar -xzf /tmp/isaac-gym.tar.gz -C /opt \
    && rm /tmp/isaac-gym.tar.gz \
    && conda run -n protomotions_interpose pip install 'pip<25' 'setuptools==69.5.1' wheel \
    && conda run -n protomotions_interpose pip install torch==2.2.0 torchvision==0.17.0 --index-url https://download.pytorch.org/whl/cu118 \
    && conda run -n protomotions_interpose pip install -e /opt/isaacgym/python \
    && conda run -n protomotions_interpose pip install -e /app/InterPose/third-party/ProtoMotion_for_InterPose \
    && conda run -n protomotions_interpose pip install -r /app/InterPose/third-party/ProtoMotion_for_InterPose/requirements_isaacgym.txt \
    && conda run -n protomotions_interpose pip install -e /app/InterPose/third-party/ProtoMotion_for_InterPose/isaac_utils -e /app/InterPose/third-party/ProtoMotion_for_InterPose/poselib \
    && conda run -n protomotions_interpose pip check

# LIGHT uses its own torch 2.5 / Python 3.10 environment and a matching
# PyTorch3D build; the base image provides the CUDA 12.8 compiler.
RUN conda run -n light pip install 'pip<25' 'setuptools==69.5.1' wheel ninja \
    && conda run -n light pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124 \
    && conda install -n light -c nvidia cuda-nvcc=12.4 cuda-cudart-dev=12.4 -y \
    && conda run -n light pip install fvcore iopath \
    && CUDA_HOME=/opt/conda/envs/light conda run -n light pip install --no-build-isolation 'git+https://github.com/facebookresearch/pytorch3d.git@v0.7.9' \
    && conda run -n light pip install -c /tmp/constraints-light.txt -r /app/LIGHT/requirements.txt \
    && conda run -n light pip check \
    && conda clean -afy

COPY --chmod=755 docker/apps/scene-edit-models-v5/smoke-test.sh /usr/local/bin/scene-edit-v5-smoke-test
RUN scene-edit-v5-smoke-test
WORKDIR /app
CMD ["/bin/bash"]
