#!/usr/bin/env bash
set -euo pipefail

# --- v1 stack must still work -------------------------------------------------
conda run --no-capture-output -n skintokens python - <<'PY'
import bpy
import torch
assert bpy.app.version == (4, 5, 3), bpy.app.version
assert torch.ones(2).sum().item() == 2
print("SkinTokens ready:", torch.__version__, bpy.app.version_string)
PY

conda run --no-capture-output -n qwen3-vl python - <<'PY'
import torch
import vllm
import transformers
print("Qwen3-VL ready:", torch.__version__, "vLLM", vllm.__version__)
PY

blender --background --factory-startup --python-exit-code 1 --python-expr \
    "import bpy; assert bpy.app.version == (4, 5, 3); print('Blender ready:', bpy.app.version_string)"

# --- GVHMR research code ------------------------------------------------------
conda run --no-capture-output -n gvhmr python - <<'PY'
import hmr4d
import torch
print("GVHMR ready:", torch.__version__, "project", hmr4d.PROJ_ROOT)
PY

# --- Motion2MixamoRig ---------------------------------------------------------
cd /app/Motion2MixamoRig
export GVHMR_CHECKPOINTS=/app/Motion2MixamoRig/weights
export GVHMR_BODY_MODELS=/app/Motion2MixamoRig/assets/body_models
conda run --no-capture-output -n m2mr python - <<'PY'
import gvhmr
import motion2mixamorig
import torch
# CUDA 13 wheels need a driver newer than the 12.x drivers used by these hosts.
assert torch.version.cuda is not None and torch.version.cuda.startswith("12."), torch.version.cuda
print("Motion2MixamoRig ready:", torch.__version__, "gvhmr", getattr(gvhmr, "__version__", "?"))
PY
conda run --no-capture-output -n m2mr m2mr --help >/dev/null
echo "m2mr CLI ready"

if find /app/GVHMR /app/Motion2MixamoRig -type f \
     \( -name '*.ckpt' -o -name '*.pth' -o -name '*.safetensors' \) -print -quit | read -r _; then
  echo "unexpected model weights inside the image" >&2
  exit 1
fi
echo "scene-edit-models-v2 smoke test passed"
