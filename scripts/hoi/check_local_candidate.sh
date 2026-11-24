#!/usr/bin/env bash
# Run offline container checks, then small CUDA/extension checks on the host.
# This does not download weights or execute dataset-dependent generation.
set -uo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <already-pulled-image-reference>" >&2
    exit 2
fi
image="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
docker image inspect "$image" >/dev/null || exit 1

result=0
if ! docker run --rm --network none \
    -v "$repo_root/scripts/hoi/check_entrypoint.py:/tmp/check_entrypoint.py:ro" \
    -v "$repo_root/scripts/hoi/check_aggregate.sh:/tmp/check_aggregate.sh:ro" \
    -e HOI_CHECK_SCOPE=complete \
    --entrypoint /bin/bash "$image" /tmp/check_aggregate.sh; then
    echo 'Complete CPU / entry-point validation failed.' >&2
    result=1
fi

echo 'Checking Blender headless rendering'
if ! docker run --rm --network none \
    -v "$repo_root/scripts/hoi/check_blender.py:/tmp/check_blender.py:ro" \
    --entrypoint /opt/blender/blender "$image" \
    --background -noaudio --python-exit-code 1 --python /tmp/check_blender.py; then
    echo 'Blender headless render failed.' >&2
    result=1
fi

for env_name in hoi light interact haic grail; do
    if [[ "$env_name" == grail ]]; then
        python_bin=/root/miniconda3/envs/grail/bin/python
    else
        python_bin="/opt/conda/envs/$env_name/bin/python"
    fi
    echo "Checking GPU environment: $env_name"
    if ! docker run --rm --gpus all --network none \
        -v "$repo_root/scripts/hoi/check_gpu.py:/tmp/check_gpu.py:ro" \
        --entrypoint "$python_bin" "$image" /tmp/check_gpu.py "$env_name"; then
        echo "GPU check failed: $env_name" >&2
        result=1
    fi
done
exit "$result"
