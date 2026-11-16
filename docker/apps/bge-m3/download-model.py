#!/usr/bin/env python3
"""Download only the PyTorch assets required by BGE-M3 inference."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from huggingface_hub import snapshot_download


def git_blob_hash(path, size):
    digest = hashlib.sha1()
    digest.update(f"blob {size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path(__file__).with_name("model.lock.json"),
    )
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    if args.revision != lock["revision"]:
        raise RuntimeError("Revision does not match model.lock.json")

    args.root.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=lock["repo"],
        revision=lock["revision"],
        local_dir=args.root,
        allow_patterns=[record["path"] for record in lock["files"]],
        max_workers=4,
    )

    for record in lock["files"]:
        path = args.root / record["path"]
        if not path.is_file() or path.stat().st_size != record["size"]:
            raise RuntimeError(f"Missing or wrong-size model file: {path}")
        actual = sha256(path) if "sha256" in record else git_blob_hash(
            path, record["size"]
        )
        expected = record.get("sha256", record.get("git_blob"))
        if actual != expected:
            raise RuntimeError(f"Checksum mismatch: {path}")

    cache = args.root / ".cache"
    if cache.exists():
        shutil.rmtree(cache)
    total = sum(record["size"] for record in lock["files"])
    print(f"BGE-M3 assets verified: {len(lock['files'])} files, {total / 1024**3:.2f} GiB")


if __name__ == "__main__":
    main()
