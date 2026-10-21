# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/scene-edit-models-v1:latest
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda

WORKDIR /app

# Two isolated stacks:
#   gvhmr : official research code (hmr4d package, python 3.10, torch 2.3 cu121)
#   m2mr  : Motion2MixamoRig (python 3.11) which depends on the PyPI gvhmr>=1.6
RUN "${CONDA_DIR}/bin/conda" create -n gvhmr python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" create -n m2mr python=3.11 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

COPY thirdparty/GVHMR /app/GVHMR

# chumpy has to be built without PEP 517 isolation; numpy/cython go first so
# cython_bbox (pulled in by the requirements) can compile.
RUN conda run -n gvhmr pip install --no-cache-dir --upgrade pip setuptools wheel \
    && conda run -n gvhmr pip install --no-cache-dir "numpy==1.23.5" cython \
    && conda run -n gvhmr pip install --no-cache-dir --no-build-isolation "chumpy==0.70" \
    && conda run -n gvhmr pip install --no-cache-dir -r /app/GVHMR/requirements.txt \
    && conda run -n gvhmr pip install --no-cache-dir -e /app/GVHMR

COPY thirdparty/Motion2MixamoRig /app/Motion2MixamoRig

# Motion2MixamoRig resolves its assets/, weights/ and outputs/ relative to the
# project directory, so keep it editable and leave those folders writable.
RUN conda run -n m2mr pip install --no-cache-dir --upgrade pip setuptools wheel \
    && conda run -n m2mr pip install --no-cache-dir "numpy>=1.26" \
    && conda run -n m2mr pip install --no-cache-dir --no-build-isolation "chumpy==0.70" \
    && conda run -n m2mr pip install --no-cache-dir -e /app/Motion2MixamoRig \
    && mkdir -p /app/Motion2MixamoRig/assets/mixamo \
                /app/Motion2MixamoRig/assets/video \
                /app/Motion2MixamoRig/assets/image \
                /app/Motion2MixamoRig/weights \
                /app/Motion2MixamoRig/outputs

COPY --chmod=755 docker/apps/scene-edit-models-v2/m2mr.sh /usr/local/bin/m2mr
COPY --chmod=755 docker/apps/scene-edit-models-v2/gvhmr-demo.sh /usr/local/bin/gvhmr-demo
COPY --chmod=755 docker/apps/scene-edit-models-v2/smoke-test.sh /usr/local/bin/scene-edit-v2-smoke-test

RUN scene-edit-v2-smoke-test

CMD ["/bin/bash"]
