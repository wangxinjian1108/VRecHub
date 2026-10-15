#!/usr/bin/env bash
set -euo pipefail

cd /app/skintokens
conda run --no-capture-output -n skintokens python - <<'PY'
import bpy
import diffusers
import torch
import transformers
from src.rig_package.info.asset import Asset

assert bpy.app.version == (4, 5, 3), bpy.app.version
assert torch.ones(2).sum().item() == 2
print("SkinTokens ready:", torch.__version__, transformers.__version__, bpy.app.version_string)
PY

cd /app/qwen3-vl
conda run --no-capture-output -n qwen3-vl python - <<'PY'
import torch
import torchcodec
import vllm
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from qwen_vl_utils import process_vision_info

assert torch.ones(2).sum().item() == 2
print("Qwen3-VL ready:", torch.__version__, "vLLM", vllm.__version__)
PY

blender --background --factory-startup --python-exit-code 1 --python-expr \
    "import bpy; assert bpy.app.version == (4, 5, 3); bpy.ops.mesh.primitive_cube_add(); assert bpy.context.object.type == 'MESH'; print('Blender background ready:', bpy.app.version_string)"
