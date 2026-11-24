# syntax=docker/dockerfile:1
# The upstream release contains grail, hunyuan and sonic environments.
FROM nvgrail/grail@sha256:14eb489f0d6eb80b8ae198d44bfd4800695af27202a7a38b504c57d22f65ad8e
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1
WORKDIR /workspace/grail
COPY thirdparty/GRAIL/ /workspace/grail/
COPY docker/apps/hoi-grail-runtime/checkout-imports.sh /tmp/checkout-imports.sh

# The setup scripts check nested Git revisions and use git archive. Restore
# those pinned repositories as Git checkouts instead of copying .git pointers
# that refer to the Actions runner's checkout.
RUN bash /tmp/checkout-imports.sh \
    && rm /tmp/checkout-imports.sh

# The standard installer checks CUDA rasterization only when a GPU is present.
# MoGe's FlexGEMM import likewise has to be checked later on a GPU host.
RUN sed -i 's@bash scripts/setup/install_moge3.sh --python "$GRAIL_PYTHON"@bash scripts/setup/install_moge3.sh --python "$GRAIL_PYTHON" --no-gpu-import@' scripts/setup/install_env_docker.sh \
    && bash scripts/setup/install_env_docker.sh

CMD ["bash"]
