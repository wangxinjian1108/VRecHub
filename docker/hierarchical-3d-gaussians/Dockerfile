FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6;8.9;9.0"

WORKDIR /h3dgs

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    cmake \
    make \
    g++ \
    ninja-build \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    python3.10 \
    python3.10-dev \
    python3-pip \
    locales \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Generate en_US.UTF-8 and zh_CN.UTF-8 so bash / perl / python don't fall back to POSIX
RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && update-locale LANG=en_US.UTF-8

# Place ENV LANG/LC_ALL AFTER locale-gen, otherwise later RUN steps inherit
# LC_ALL=en_US.UTF-8 before the locale is generated and emit warnings.
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

COPY thirdparty/hierarchical-3d-gaussians .

RUN if [ ! -f submodules/hierarchy-rasterizer/third_party/glm/CMakeLists.txt ]; then \
        rm -rf submodules/hierarchy-rasterizer/third_party/glm && \
        git clone --depth 1 https://github.com/g-truc/glm.git submodules/hierarchy-rasterizer/third_party/glm; \
    fi && \
    if [ ! -f submodules/gaussianhierarchy/dependencies/eigen/CMakeLists.txt ]; then \
        rm -rf submodules/gaussianhierarchy/dependencies/eigen && \
        git clone --depth 1 https://gitlab.com/libeigen/eigen.git submodules/gaussianhierarchy/dependencies/eigen; \
    fi

RUN pip install --no-cache-dir \
        torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118

RUN pip install --no-cache-dir \
        "numpy<2" \
        plyfile tqdm joblib exif scikit-learn opencv-python==4.9.0.80 matplotlib \
        timm==0.4.5 lpips tensorboard

RUN pip install --no-cache-dir --no-build-isolation \
        submodules/simple-knn \
        submodules/hierarchy-rasterizer \
        submodules/gaussianhierarchy

CMD ["python", "-c", "import torch; from diff_gaussian_rasterization import GaussianRasterizer; print('ready')"]
