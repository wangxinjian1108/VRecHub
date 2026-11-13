# syntax=docker/dockerfile:1
# GHA-built environment image; all source and dependency revisions stay fixed.
FROM ghcr.io/wangxinjian1108/human-object-interaction-v1@sha256:bd956d166bcf92367096c281fe5bf6902e82566e579094d189420dbebc8637b2
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
COPY docker/apps/human-object-interaction-v1-weights /opt/hoi-weights
RUN conda run -n kimodo pip install gdown==5.2.0 \
    && conda run --no-capture-output -n kimodo python /opt/hoi-weights/download-weights.py \
    && ln -s /models/omomo/stage1/model.pt /models/omomo/stage1.pt \
    && ln -s /models/omomo/stage2/model.pt /models/omomo/stage2.pt

ENV CHECKPOINT_DIR=/models/kimodo \
    TEXT_ENCODERS_DIR=/models/text-encoders \
    TEXT_ENCODER_MODE=local \
    LOCAL_CACHE=True \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    CLIP_MODEL_PATH=/models/clip/ViT-B-32.pt \
    CLIP_DOWNLOAD_ROOT=/models/clip

COPY --chmod=755 docker/apps/human-object-interaction-v1-weights/chois-infer.sh /usr/local/bin/chois-infer
COPY --chmod=755 docker/apps/human-object-interaction-v1-weights/omomo-infer.sh /usr/local/bin/omomo-infer
COPY --chmod=755 docker/apps/human-object-interaction-v1-weights/smoke-test.sh /usr/local/bin/human-object-interaction-smoke-test
RUN human-object-interaction-smoke-test
CMD ["/bin/bash"]
