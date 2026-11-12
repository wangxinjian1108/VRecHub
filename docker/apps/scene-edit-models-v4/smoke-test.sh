#!/usr/bin/env bash
set -euo pipefail

# Everything inherited from v3 must still work.
scene-edit-v3-smoke-test

# TRELLIS.2
cd /app/TRELLIS.2
conda run --no-capture-output -n trellis2 python - <<'PY'
from importlib.metadata import distribution
from importlib.util import find_spec

import torch
import trellis2

assert torch.version.cuda == "12.4", torch.version.cuda
for package_name, module_name in (
    ("flash-attn", "flash_attn"),
    ("nvdiffrast", "nvdiffrast"),
    ("nvdiffrec_render", "nvdiffrec_render"),
    ("cumesh", "cumesh"),
    ("flex_gemm", "flex_gemm"),
    ("o_voxel", "o_voxel"),
):
    package = distribution(package_name)
    assert find_spec(module_name) is not None, module_name
    assert any(str(path).endswith(".so") for path in package.files or ()), package_name
    print("Compiled extension ready:", package_name, package.version)
print("TRELLIS.2 ready:", torch.__version__, "package", trellis2.__file__)
PY

if find /app/TRELLIS.2 -type f \
     \( -name '*.ckpt' -o -name '*.safetensors' -o -name '*.pth' \) -print -quit | read -r _; then
  echo "unexpected model weights inside the image" >&2
  exit 1
fi
echo "scene-edit-models-v4 smoke test passed"
