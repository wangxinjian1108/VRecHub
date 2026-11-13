#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
weights_root=${1:-/root/models/human-object-interaction-v1}
target_image=${2:-repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest}

if [[ ! -f "$weights_root/weights-manifest.json" ]]; then
    echo "Weight manifest is missing from $weights_root" >&2
    exit 1
fi

cd "$repo_root"
docker tag \
    ghcr.nju.edu.cn/wangxinjian1108/human-object-interaction-v1:latest \
    local/human-object-interaction-v1:base

docker buildx build \
    --load \
    --build-context "weights=$weights_root" \
    --file docker/apps/human-object-interaction-v1-weights/Dockerfile.local \
    --tag "$target_image" \
    .
