#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
conda run -n hoi pip check
conda run -n kimodo pip check
cd /app/chois_release
conda run --no-capture-output -n hoi python /opt/hoi-weights/verify-hoi-checkpoint.py chois /models/chois/model-10.pt
chois-infer --help >/dev/null
conda run --no-capture-output -n hoi python - <<'PY'
import os, clip, torch
model, _ = clip.load(os.environ['CLIP_MODEL_PATH'], device='cpu', jit=False)
with torch.inference_mode():
    embedding = model.encode_text(clip.tokenize(['a person carrying a box']))
assert embedding.shape == (1, 512) and torch.isfinite(embedding).all()
print('Local CLIP text encoder passed')
PY
cd /app/omomo_release
for name in stage1 stage2 stage1_object_split stage2_object_split; do
    stage=${name%%_object_split}
    conda run --no-capture-output -n hoi python /opt/hoi-weights/verify-hoi-checkpoint.py "$stage" "/models/omomo/$name/model.pt"
done
omomo-infer --help >/dev/null
cd /app/kimodo
conda run --no-capture-output -n kimodo python /opt/hoi-weights/verify-kimodo.py
kimodo-gen --help >/dev/null
blender --background --factory-startup --python-expr 'import bpy; print(bpy.app.version_string)' >/dev/null
echo 'HOI weighted image: checkpoint loads and local CLIP passed; GPU end-to-end inference is a separate check'
