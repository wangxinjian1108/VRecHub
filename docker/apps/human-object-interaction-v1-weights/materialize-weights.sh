#!/usr/bin/env bash
set -euo pipefail

chunk_image=${HOI_WEIGHT_CHUNK_IMAGE:-ghcr.nju.edu.cn/wangxinjian1108/human-object-interaction-v1-weights-chunks:latest}
weights_root=${1:-/root/models/human-object-interaction-v1}
tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/hoi-weights.XXXXXX")
container="hoi-weight-chunks-$$"

cleanup() {
    docker rm -f "$container" >/dev/null 2>&1 || true
    rm -rf -- "$tmp_dir"
}
trap cleanup EXIT

docker pull "$chunk_image"
docker create --name "$container" "$chunk_image" >/dev/null
docker cp "$container:/chunks" "$tmp_dir/chunks"
docker cp "$container:/weights/." "$tmp_dir/weights"

mkdir -p \
    "$weights_root/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct"

for number in 01 02 03 04; do
    output="$weights_root/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/model-0000${number:1}-of-00004.safetensors"
    cat "$tmp_dir"/chunks/llama"$number".* > "$output"
done

cp -a "$tmp_dir/weights/." "$weights_root/"

python3 - "$weights_root" <<'PY'
import hashlib
import json
from pathlib import Path
import os
import sys

root = Path(sys.argv[1])
for name in ("stage1.pt", "stage2.pt"):
    path = root / "omomo" / name
    if path.is_symlink():
        path.unlink()
os.symlink("stage1/model.pt", root / "omomo/stage1.pt")
os.symlink("stage2/model.pt", root / "omomo/stage2.pt")

manifest = json.loads((root / "weights-manifest.json").read_text())
for record in manifest["files"]:
    path = root / record["path"]
    if not path.is_file():
        raise SystemExit(f"Missing weight: {path}")
    if path.stat().st_size != record["size"]:
        raise SystemExit(f"Wrong size: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != record["sha256"]:
        raise SystemExit(f"Wrong SHA256: {path}")

print(f"Verified {len(manifest['files'])} weight files")
PY

du -sh "$weights_root"
