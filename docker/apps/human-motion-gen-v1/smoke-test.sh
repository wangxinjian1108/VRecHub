#!/usr/bin/env bash
set -euo pipefail

# HY-Motion 1.0
cd /app/HY-Motion-1.0
conda run --no-capture-output -n hy-motion python - <<'PY'
import torch, transformers, diffusers, hymotion
print("HY-Motion ready:", torch.__version__, transformers.__version__)
PY

# ARDY
cd /app/ardy
conda run --no-capture-output -n ardy python - <<'PY'
import torch, transformers, ardy
print("ARDY ready:", torch.__version__, transformers.__version__)
PY

# Kimodo
cd /app/kimodo
conda run --no-capture-output -n kimodo python - <<'PY'
import torch, transformers, kimodo
print("Kimodo ready:", torch.__version__, transformers.__version__)
PY
conda run --no-capture-output -n kimodo kimodo_gen --help >/dev/null
echo "kimodo_gen CLI ready"

# DART
cd /app/DART
conda run --no-capture-output -n dart python - <<'PY'
import torch, pytorch3d, mld
print("DART ready:", torch.__version__, torch.version.cuda)
PY

for env in hy-motion ardy kimodo dart; do
  conda run -n "${env}" python -c "import torch; assert torch.version.cuda in {'11.8','12.1','12.4','12.8'}, torch.version.cuda" \
    || { echo "${env} has an unsupported CUDA build" >&2; exit 1; }
done

if find /app/HY-Motion-1.0 /app/ardy /app/kimodo /app/DART -type f \
     \( -name '*.ckpt' -o -name '*.safetensors' -o -name '*.pth' \) -print -quit | read -r _; then
  echo "unexpected model weights inside the image" >&2
  exit 1
fi
echo "human-motion-gen-v1 smoke test passed"
