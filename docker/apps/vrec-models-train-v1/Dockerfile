ARG BASE_IMAGE=ghcr.io/wangxinjian1108/vrec-models-v1:latest
FROM ${BASE_IMAGE}

# Add sam3 [train] extras on top of the inherited [notebooks] install:
#   hydra-core, submitit, tensorboard, zstandard, scipy,
#   torchmetrics, fvcore, fairscale, scikit-image, scikit-learn
# Note: vrec-models-v1 lays out sam3 at /app/sam3 (NOT /sam3 like the
# standalone sam3 image — different layout convention per image family).
RUN cd /app/sam3 && conda run -n sam3 pip install --no-cache-dir -e ".[train]"

CMD ["/bin/bash"]
