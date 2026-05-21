FROM colmap/colmap:latest

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda \
    CONDA_ENV=colmap

WORKDIR /colmap

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    nano \
    net-tools \
    sudo \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 and zh_CN.UTF-8 so bash / perl / python don't fall back to POSIX
RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && update-locale LANG=en_US.UTF-8

# Place ENV LANG/LC_ALL AFTER locale-gen, otherwise later RUN steps inherit
# LC_ALL=en_US.UTF-8 before the locale is generated and emit warnings.
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=3.10 -y \
    && "${CONDA_DIR}/bin/conda" clean -afy

ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}

CMD ["colmap"]
