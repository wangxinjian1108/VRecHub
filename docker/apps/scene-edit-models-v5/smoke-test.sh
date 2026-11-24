#!/usr/bin/env bash
set -euo pipefail
scene-edit-v3-smoke-test
conda run --no-capture-output -n interpose python -c 'import torch, pytorch3d, trimesh, bps_torch, human_body_prior; print("InterPose:", torch.__version__)'
conda run --no-capture-output -n light python -c 'import torch, pytorch3d, clip, smplx; print("LIGHT:", torch.__version__)'
# Import Isaac Gym before torch, as required by Isaac Gym. The hosted builder
# has no NVIDIA driver, so test simulator execution separately on a GPU host.
conda run --no-capture-output -n protomotions_interpose python -c 'import isaacgym; import torch, protomotions, poselib, isaac_utils; print("MaskedMimic:", torch.__version__)'
