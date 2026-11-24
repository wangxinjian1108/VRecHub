# syntax=docker/dockerfile:1
# Pin GRAIL to its immutable digest after its stage passes CI.
ARG GRAIL_IMAGE=ghcr.io/wangxinjian1108/hoi-grail-runtime:latest
ARG HOI_IMAGE=ghcr.io/wangxinjian1108/human-object-interaction-v1@sha256:bd956d166bcf92367096c281fe5bf6902e82566e579094d189420dbebc8637b2
ARG LIGHT_IMAGE=ghcr.io/wangxinjian1108/scene-edit-models-v5@sha256:60adbaf95bf7f7e725461b5d9b4365d2e56a5f28f24dde319fb4d8cad80e053a
ARG INTERACT_IMAGE=ghcr.io/wangxinjian1108/hoi-interact-runtime-headless@sha256:3701a71e590502e55f58ab5ee5a2a006ab399ec9f33b8a887d534ec2e371659c
ARG HAIC_IMAGE=ghcr.io/wangxinjian1108/hoi-haic-runtime@sha256:4740c6dd677ee900c1bba727a066c78a4b9ef349aba5d767291d7873b03d0f30
FROM ${HOI_IMAGE} AS hoi
FROM ${LIGHT_IMAGE} AS light
FROM ${INTERACT_IMAGE} AS interact
FROM ${HAIC_IMAGE} AS haic
FROM ${GRAIL_IMAGE} AS aggregate

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive CONDA_DIR=/opt/conda \
    PATH=/opt/conda/bin:${PATH} MPLBACKEND=Agg WANDB_MODE=disabled \
    SMPLH_PATH=/models/smplh_amass BLENDER_PATH=/usr/local/bin/blender \
    HF_HOME=/models/huggingface
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglu1-mesa libegl1 libosmesa6 libglib2.0-0 libspatialindex-dev \
    libsm6 libxext6 libxrender1 libxi6 libxfixes3 libxrandr2 libxinerama1 \
    libxcursor1 libxkbcommon0 libfontconfig1 libfreetype6 libdbus-1-3 \
    libasound2 libvulkan1 ffmpeg && rm -rf /var/lib/apt/lists/*

# GRAIL's official distribution resides in /root/miniconda3. The independent
# environments below were all created at /opt/conda and retain that prefix.
COPY --from=hoi /opt/conda /opt/conda
COPY --from=hoi /opt/blender /opt/blender
COPY --from=hoi /app/chois_release /app/chois_release
COPY --from=hoi /app/omomo_release /app/omomo_release
COPY --from=hoi /app/kimodo /app/kimodo
COPY --from=hoi /usr/local/bin/chois-infer /usr/local/bin/chois-infer
COPY --from=hoi /usr/local/bin/omomo-infer /usr/local/bin/omomo-infer
COPY --from=hoi /usr/local/bin/kimodo-gen /usr/local/bin/kimodo-gen
COPY --from=hoi /usr/local/bin/human-object-interaction-smoke-test /usr/local/bin/human-object-interaction-smoke-test
RUN ln -sf /opt/blender/blender /usr/local/bin/blender \
    && mkdir -p /models /outputs \
    && human-object-interaction-smoke-test
COPY --from=light /opt/conda/envs/light /opt/conda/envs/light
COPY --from=light /app/LIGHT /app/LIGHT
COPY --from=interact /opt/conda/envs/interact /opt/conda/envs/interact
COPY --from=interact /app/InterAct /app/InterAct
COPY --from=haic /opt/conda/envs/haic /opt/conda/envs/haic
COPY --from=haic /opt/IsaacLab /opt/IsaacLab
COPY --from=haic /app/HAIC /app/HAIC
COPY scripts/hoi/check_entrypoint.py /tmp/check_entrypoint.py
RUN conda run -n light python -c 'import torch, pytorch3d, clip, smplx; print("LIGHT ready", torch.__version__)' \
    && conda run -n interact python -c 'import torch, pytorch3d, pointnet2_ops._ext, spacy; from human_body_prior.tools import tgm_conversion; assert spacy.load("en_core_web_sm"); print("InterAct ready", torch.__version__)' \
    && conda run -n haic python -c 'import torch, isaaclab, isaacsim, active_adaptation; print("HAIC ready", torch.__version__)' \
    && /root/miniconda3/bin/conda run -n grail python -c 'import grail; print("GRAIL source ready")' \
    && cd /app/InterAct/text2interaction \
    && PYGLET_HEADLESS=1 PYOPENGL_PLATFORM=egl conda run -n interact python /tmp/check_entrypoint.py sample.local_generate_obj \
    && PYGLET_HEADLESS=1 PYOPENGL_PLATFORM=egl conda run -n interact python /tmp/check_entrypoint.py sample.local_generate_obj_guide_contactv2 \
    && rm /tmp/check_entrypoint.py

WORKDIR /workspace/grail
CMD ["bash"]
