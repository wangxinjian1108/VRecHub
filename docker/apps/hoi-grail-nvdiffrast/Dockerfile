# syntax=docker/dockerfile:1
# Build only the missing CUDA extension for the pinned GRAIL Python / torch ABI.
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04 AS build
ENV DEBIAN_FRONTEND=noninteractive CUDA_HOME=/usr/local/cuda \
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0;12.0" MAX_JOBS=2 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      git python3 python3-pip python3-dev unzip \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir 'pip<25' wheel setuptools ninja packaging \
    && python3 -m pip install --no-cache-dir torch==2.7.1 \
       --index-url https://download.pytorch.org/whl/cu128
RUN git clone https://github.com/NVlabs/nvdiffrast.git /tmp/nvdiffrast \
    && git -C /tmp/nvdiffrast checkout 253ac4fcea7de5f396371124af597e6cc957bfae \
    && cd /tmp/nvdiffrast \
    && python3 -m pip wheel --no-deps --no-build-isolation -w /tmp/wheels . \
    && mkdir /output \
    && unzip -j '/tmp/wheels/nvdiffrast-*.whl' '_nvdiffrast_c*.so' -d /output \
    && test "$(find /output -name '_nvdiffrast_c*.so' | wc -l)" -eq 1 \
    && for arch in 80 86 89 90 120; do \
         cuobjdump --list-elf /output/_nvdiffrast_c*.so | grep -q "sm_${arch}\\.cubin"; \
       done

# This component overlays the same pinned 0.4.0 extension in the GRAIL env.
FROM scratch
COPY --from=build /output/_nvdiffrast_c*.so /root/miniconda3/envs/grail/lib/python3.10/site-packages/
