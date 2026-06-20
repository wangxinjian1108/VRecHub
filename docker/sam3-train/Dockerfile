ARG BASE_IMAGE=ghcr.io/wangxinjian1108/sam3:latest
FROM ${BASE_IMAGE}

# Add sam3 [train] extras on top of the inherited [notebooks] install:
#   hydra-core, submitit, tensorboard, zstandard, scipy,
#   torchmetrics, fvcore, fairscale, scikit-image, scikit-learn
RUN conda run -n sam3 pip install --no-cache-dir -e "/app/sam3[train]"

CMD ["/bin/bash"]
