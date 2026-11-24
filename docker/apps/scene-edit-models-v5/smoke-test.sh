#!/usr/bin/env bash
set -euo pipefail
scene-edit-v3-smoke-test
conda run --no-capture-output -n light python -c 'import torch, pytorch3d, clip, smplx; print("LIGHT:", torch.__version__)'
