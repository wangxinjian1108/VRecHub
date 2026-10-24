#!/usr/bin/env bash
set -euo pipefail

# Everything inherited from v2 must still work.
scene-edit-v2-smoke-test

# Kimodo
cd /app/kimodo
conda run --no-capture-output -n kimodo python - <<'PY'
import torch, transformers, kimodo
assert torch.version.cuda and torch.version.cuda.startswith("12."), torch.version.cuda
print("Kimodo ready:", torch.__version__, transformers.__version__)
PY
conda run --no-capture-output -n kimodo kimodo_gen --help >/dev/null
echo "kimodo_gen CLI ready"

if find /app/kimodo -type f \
     \( -name '*.ckpt' -o -name '*.safetensors' -o -name '*.pth' \) -print -quit | read -r _; then
  echo "unexpected model weights inside the image" >&2
  exit 1
fi
echo "scene-edit-models-v3 smoke test passed"
