#!/usr/bin/env bash
set -euo pipefail

# Exercise the binary PyTorch3D extension on CPU; hosted Actions has no GPU.
conda run --no-capture-output -n hoi python - <<'PY'
import torch
import pytorch3d
from pytorch3d import _C
from pytorch3d.ops import knn_points
from bps_torch.bps import bps_torch
from human_body_prior.body_model.body_model import BodyModel
import chamfer_distance
import clip

assert torch.__version__ == '1.11.0+cu113', torch.__version__
assert torch.version.cuda == '11.3', torch.version.cuda
points = torch.tensor([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
nearest = knn_points(points, points, K=1)
assert torch.equal(nearest.idx[..., 0], torch.tensor([[0, 1, 2]]))
basis = bps_torch(bps_type='custom', custom_basis=points[0].numpy())
encoded = basis.encode(points, feature_type=['dists'])
assert torch.allclose(encoded['dists'], torch.zeros(1, 3))
print('HOI binary extension and BPS ready:', torch.__version__, pytorch3d.__version__)
PY

# Separate processes prevent the two unrelated `manip` packages colliding.
cd /app/chois_release
conda run --no-capture-output -n hoi python -c 'import trainer_chois; print("CHOIS inference imports ready")'
chois-infer --help >/dev/null
conda run -n hoi pip check

cd /app/omomo_release
conda run --no-capture-output -n hoi python -c 'import trainer_hand_foot_manip_diffusion, trainer_full_body_manip_diffusion; print("OMOMO two-stage inference imports ready")'
omomo-infer --help >/dev/null

cd /app/kimodo
conda run --no-capture-output -n kimodo python - <<'PY'
import torch, transformers, kimodo
assert torch.__version__ == '2.5.1+cu124', torch.__version__
assert torch.version.cuda == '12.4', torch.version.cuda
print('Kimodo ready:', torch.__version__, transformers.__version__)
PY
kimodo-gen --help >/dev/null
conda run -n kimodo pip check
blender --background --factory-startup --python-expr 'import bpy; print("Blender ready:", bpy.app.version_string)' >/dev/null

unexpected=$(find /app /models -type f \
    \( -name '*.ckpt' -o -name '*.safetensors' -o -name '*.pth' -o -name '*.pt' \) \
    ! -path /app/chois_release/bps.pt ! -path /app/omomo_release/bps.pt -print -quit)
if [[ -n "$unexpected" ]]; then
    echo "Unexpected learned weights: $unexpected" >&2
    exit 1
fi
echo 'human-object-interaction-v1 smoke test passed (no learned weights, no GPU inference)'
