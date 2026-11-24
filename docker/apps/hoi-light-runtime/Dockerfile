# syntax=docker/dockerfile:1
FROM ghcr.io/wangxinjian1108/scene-edit-models-v5@sha256:60adbaf95bf7f7e725461b5d9b4365d2e56a5f28f24dde319fb4d8cad80e053a
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
WORKDIR /app/LIGHT
# Raw-text dataset processing loads this spaCy pipeline by name. Keep the
# package offline in the image, independently of model checkpoints.
RUN conda run -n light pip install --no-deps \
      https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl \
    && conda run -n light pip install 'joblib==1.4.2' 'transformers==4.57.6' \
    && conda run -n light pip check \
    && conda run -n light python -c 'import spacy; from transformers.utils import is_torch_available; spacy.load("en_core_web_sm"); assert is_torch_available()'
COPY scripts/hoi/check_entrypoint.py /tmp/check_entrypoint.py
RUN conda run -n light python /tmp/check_entrypoint.py sample.generate \
    && rm /tmp/check_entrypoint.py
CMD ["bash"]
