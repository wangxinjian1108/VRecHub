# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    MPLBACKEND=Agg \
    WANDB_MODE=disabled

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs zsh vim wget curl unzip bzip2 xz-utils ca-certificates \
    build-essential cmake ninja-build pkg-config ffmpeg rsync tmux htop \
    less tree locales sudo fonts-dejavu-core \
    libgl1 libglu1-mesa libegl1 libgles2 libosmesa6 libglib2.0-0 \
    libsm6 libxext6 libxrender1 libxi6 libxfixes3 libxrandr2 libxinerama1 \
    libxcursor1 libxkbcommon0 libfontconfig1 libfreetype6 libdbus-1-3 libasound2 \
    && locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" init bash \
    && "${CONDA_DIR}/bin/conda" create -n hoi python=3.8 -y \
    && "${CONDA_DIR}/bin/conda" create -n kimodo python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

ENV PATH=${CONDA_DIR}/bin:${PATH}

# CHOIS and OMOMO publish identical requirements and use the same torch 1.11
# APIs. Keep their shared stack isolated from Kimodo's transformers 5 stack.
# The cu113 wheels supply the CUDA 11.3 runtime independently of the base SDK.
COPY docker/apps/human-object-interaction-v1/hoi-constraints.txt /opt/hoi-constraints.txt
RUN conda run -n hoi pip install "pip==24.0" "setuptools==69.5.1" wheel \
    && conda run -n hoi pip install \
        torch==1.11.0+cu113 torchvision==0.12.0+cu113 torchaudio==0.11.0+cu113 \
        --extra-index-url https://download.pytorch.org/whl/cu113 \
    && conda run -n hoi pip install -c /opt/hoi-constraints.txt \
        numpy fvcore iopath ninja tqdm dotmap PyYAML omegaconf loguru \
    && conda run -n hoi pip install --no-index \
        pytorch3d==0.7.2 \
        -f https://dl.fbaipublicfiles.com/pytorch3d/packaging/wheels/py38_cu113_pyt1110/download.html

# Pin research dependencies to known source revisions. No pretrained assets are
# fetched by these pip installs; CLIP weights are supplied at runtime.
RUN conda run -n hoi pip install -c /opt/hoi-constraints.txt \
        "human-body-prior @ git+https://github.com/nghorbani/human_body_prior.git@4c246d8a83ce16d3cff9c79dcf04d81fa440a6bc" \
        "chamfer-distance @ git+https://github.com/otaheri/chamfer_distance.git@f86f6f7cadd3aca642704573d1626c67ca2e2846" \
        "bps-torch @ git+https://github.com/otaheri/bps_torch.git@00fcac3dffd294211d4ea0363eaf6c2ca4e068dc" \
        "clip @ git+https://github.com/openai/CLIP.git@a1d071733d7111c9c014f024669f959182114e33" \
    && conda clean -afy

COPY thirdparty/chois_release /app/chois_release
COPY thirdparty/omomo_release /app/omomo_release
RUN conda run -n hoi pip install -c /opt/hoi-constraints.txt \
        -r /app/chois_release/requirements.txt -r /app/omomo_release/requirements.txt \
    && conda run -n hoi pip check \
    && conda clean -afy

COPY thirdparty/kimodo /app/kimodo
RUN conda run -n kimodo pip install --upgrade pip setuptools wheel \
    && conda run -n kimodo pip install \
        torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cu124 \
    && conda run -n kimodo pip install -e /app/kimodo \
    && conda run -n kimodo pip check \
    && conda clean -afy

# Use the Blender release referenced by CHOIS, including its bundled Python.
RUN curl -fL --retry 3 \
        https://download.blender.org/release/Blender3.6/blender-3.6.3-linux-x64.tar.xz \
        -o /tmp/blender.tar.xz \
    && mkdir /opt/blender \
    && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && ln -s /opt/blender/blender /usr/local/bin/blender \
    && rm /tmp/blender.tar.xz

COPY docker/apps/human-object-interaction-v1/configure-paths.py /opt/configure-hoi-paths.py
RUN conda run -n hoi python /opt/configure-hoi-paths.py \
    && mkdir -p /app/chois_release/pretrained_models /app/chois_release/processed_data \
                 /app/omomo_release/pretrained_models /app/omomo_release/data \
                 /models /outputs

ENV SMPLH_PATH=/models/smplh_amass \
    BLENDER_PATH=/usr/local/bin/blender \
    HF_HOME=/models/huggingface

COPY --chmod=755 docker/apps/human-object-interaction-v1/chois-infer.sh /usr/local/bin/chois-infer
COPY --chmod=755 docker/apps/human-object-interaction-v1/omomo-infer.sh /usr/local/bin/omomo-infer
COPY --chmod=755 docker/apps/human-object-interaction-v1/kimodo-gen.sh /usr/local/bin/kimodo-gen
COPY --chmod=755 docker/apps/human-object-interaction-v1/smoke-test.sh /usr/local/bin/human-object-interaction-smoke-test
RUN human-object-interaction-smoke-test

CMD ["/bin/bash"]
