#!/usr/bin/env bash
# Run inside the composed image. SMPL-H is mocked solely for --help checks.
set -euo pipefail

human-object-interaction-smoke-test

cd /app/LIGHT
conda run --no-capture-output -n light python -c 'import torch,pytorch3d,clip,smplx,spacy; from transformers.utils import is_torch_available; assert is_torch_available(); spacy.load("en_core_web_sm")'
conda run --no-capture-output -n light python /tmp/check_entrypoint.py sample.generate

cd /app/InterAct/text2interaction
conda run --no-capture-output -n interact python -c 'import torch,pytorch3d,pointnet2_ops._ext,spacy; assert spacy.load("en_core_web_sm")'
conda run --no-capture-output -n interact python /tmp/check_entrypoint.py sample.local_generate_obj
conda run --no-capture-output -n interact python /tmp/check_entrypoint.py sample.local_generate_obj_guide_contactv2

conda run --no-capture-output -n haic python -c 'import torch,isaaclab,isaacsim,active_adaptation; assert torch.version.cuda == "12.8"; print("HAIC imports ready")'

if [[ "${HOI_CHECK_SCOPE:-complete}" == complete ]]; then
    cd /workspace/grail
    /root/miniconda3/bin/conda run --no-capture-output -n grail python -c 'import grail,soma; print("GRAIL ready")'
    test -x /root/.cache/grail/envs/gem-x/bin/python
    test -x /workspace/grail/.venvs/moge3/bin/python
    test -x /workspace/grail/.venvs/mose3/bin/python
    test -x /workspace/grail/imports/soma-retargeter/.venv/bin/python
    /workspace/grail/imports/blender/blender --background --version | sed -n '1p'
elif [[ "${HOI_CHECK_SCOPE}" != components ]]; then
    echo "Unsupported HOI_CHECK_SCOPE: ${HOI_CHECK_SCOPE}" >&2
    exit 2
fi

echo "HOI ${HOI_CHECK_SCOPE:-complete} environment checks passed (no GPU inference)"
