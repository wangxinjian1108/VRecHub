# Pin the Pi4 environment built by GitHub Actions at VRecHub commit 2c560d1.
FROM ghcr.io/wangxinjian1108/pi4@sha256:1ef4ffa4e230dfb3ba9a4bc03e64f933a04f198a1b3fd8897ead94d4ef51c13f

ARG PI4_REVISION=59f307317fb630c9c5a5aa635038d98ed106aaf5
ARG PI4_SHA256=fefacac1fb3d23d33c628c41f40d3ce3be98ca064c271948371805db7b5a0e69
ENV PI4_WEIGHTS=/models/Pi4/model.safetensors \
    HF_HUB_OFFLINE=1

# Populate both a stable file path and the Hugging Face cache so upstream
# Pi4.from_pretrained() and example.py work without network access.
RUN set -eu; \
    mkdir -p /models/Pi4 "${HF_HOME}/hub/models--yyfz233--Pi4/snapshots/${PI4_REVISION}" "${HF_HOME}/hub/models--yyfz233--Pi4/refs"; \
    curl -fL --retry 3 --connect-timeout 30 "https://huggingface.co/yyfz233/Pi4/resolve/${PI4_REVISION}/model.safetensors" -o "${PI4_WEIGHTS}"; \
    echo "${PI4_SHA256}  ${PI4_WEIGHTS}" | sha256sum -c -; \
    ln "${PI4_WEIGHTS}" "${HF_HOME}/hub/models--yyfz233--Pi4/snapshots/${PI4_REVISION}/model.safetensors"; \
    printf '%s' "${PI4_REVISION}" > "${HF_HOME}/hub/models--yyfz233--Pi4/refs/main"; \
    python -c "from huggingface_hub import hf_hub_download; from safetensors import safe_open; p=hf_hub_download('yyfz233/Pi4', 'model.safetensors', local_files_only=True); f=safe_open(p, framework='pt', device='cpu'); assert len(f.keys()) > 0; print('Offline checkpoint:', p, 'tensors:', len(f.keys()))"
