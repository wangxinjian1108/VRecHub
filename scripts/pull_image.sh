#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <image-name> [tag]"
    echo "Example: $0 scal3r latest"
    exit 1
fi

IMAGE="$1"
TAG="${2:-latest}"
REGISTRY="ghcr.io/wangxinjian1108"

GH_TOKEN="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"

if [[ -z "${GH_TOKEN}" ]]; then
    read -rsp "GitHub Token: " GH_TOKEN
    echo
fi

echo "${GH_TOKEN}" | docker login ghcr.io -u wangxinjian1108 --password-stdin
docker pull "${REGISTRY}/${IMAGE}:${TAG}"

echo "Done: ${REGISTRY}/${IMAGE}:${TAG}"
