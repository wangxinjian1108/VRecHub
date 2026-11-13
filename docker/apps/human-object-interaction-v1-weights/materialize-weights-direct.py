#!/usr/bin/env python3
"""Download chunked OCI layers with resume, then verify materialized weights."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
from urllib.parse import urlsplit

import requests


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def layer_manifest(image):
    output = subprocess.check_output(
        ["docker", "manifest", "inspect", "--verbose", image], text=True
    )
    versions = json.loads(output)
    for version in versions:
        platform = version["Descriptor"].get("platform", {})
        if platform.get("architecture") == "amd64" and platform.get("os") == "linux":
            return version["OCIManifest"]["layers"]
    raise RuntimeError(f"No linux/amd64 manifest found for {image}")


def download_layer(url, digest, cache_dir, proxy):
    target = cache_dir / (digest.removeprefix("sha256:") + ".tar")
    if target.is_file() and sha256(target) == digest.removeprefix("sha256:"):
        print(f"Verified cached layer {digest}", flush=True)
        return target
    partial = target.with_suffix(".part")
    for attempt in range(12):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=(30, 300),
                proxies={"http": proxy, "https": proxy},
            ) as response:
                if response.status_code == 416:
                    partial.unlink(missing_ok=True)
                    continue
                response.raise_for_status()
                mode = "ab" if response.status_code == 206 else "wb"
                with partial.open(mode) as stream:
                    for block in response.iter_content(8 * 1024 * 1024):
                        stream.write(block)
            if sha256(partial) == digest.removeprefix("sha256:"):
                partial.replace(target)
                print(f"Downloaded layer {digest}", flush=True)
                return target
            print(f"Checksum mismatch for {digest}; restarting", flush=True)
            partial.unlink(missing_ok=True)
        except Exception as error:
            if attempt == 11:
                raise
            print(
                f"Retry {attempt + 1}/12 for {digest}: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            time.sleep(min(5 * (attempt + 1), 30))
    raise RuntimeError(f"Could not download {digest}")


def safe_extract(layer, destination):
    destination = destination.resolve()
    with tarfile.open(layer) as archive:
        for member in archive:
            target = (destination / member.name).resolve()
            if destination not in target.parents and target != destination:
                raise RuntimeError(f"Unsafe path in layer: {member.name}")
        archive.extractall(destination)


def assemble(staging, weights_root):
    text_root = (
        weights_root
        / "text-encoders/meta-llama/Meta-Llama-3-8B-Instruct"
    )
    text_root.mkdir(parents=True, exist_ok=True)
    for number in range(1, 5):
        chunks = sorted((staging / "chunks").glob(f"llama{number:02d}.*"))
        if not chunks:
            raise RuntimeError(f"No chunks found for Llama shard {number}")
        output = text_root / f"model-{number:05d}-of-00004.safetensors"
        with output.open("wb") as stream:
            for chunk in chunks:
                with chunk.open("rb") as source:
                    shutil.copyfileobj(source, stream)
        print(f"Assembled {output} from {len(chunks)} chunks", flush=True)

    shutil.copytree(
        staging / "weights", weights_root, dirs_exist_ok=True, symlinks=True
    )
    for name in ("stage1.pt", "stage2.pt"):
        path = weights_root / "omomo" / name
        if path.is_symlink():
            path.unlink()
    os.symlink("stage1/model.pt", weights_root / "omomo/stage1.pt")
    os.symlink("stage2/model.pt", weights_root / "omomo/stage2.pt")


def verify(weights_root):
    manifest = json.loads((weights_root / "weights-manifest.json").read_text())
    for record in manifest["files"]:
        path = weights_root / record["path"]
        if not path.is_file():
            raise RuntimeError(f"Missing weight: {path}")
        if path.stat().st_size != record["size"]:
            raise RuntimeError(f"Wrong size: {path}")
        if sha256(path) != record["sha256"]:
            raise RuntimeError(f"Wrong SHA256: {path}")
    print(f"Verified {len(manifest['files'])} weight files", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "weights_root",
        nargs="?",
        type=Path,
        default=Path("/root/models/human-object-interaction-v1"),
    )
    parser.add_argument(
        "--image",
        default=(
            "ghcr.nju.edu.cn/wangxinjian1108/"
            "human-object-interaction-v1-weights-chunks:latest"
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("/tmp/hoi-weight-layers"),
    )
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument(
        "--proxies",
        default="http://127.0.0.1:18889,http://127.0.0.1:18444",
        help="Comma-separated HTTP proxies assigned round-robin to layer downloads",
    )
    args = parser.parse_args()

    parsed = urlsplit("https://" + args.image.split("/", 1)[0])
    repository = args.image.split("/", 1)[1].rsplit(":", 1)[0]
    layers = layer_manifest(args.image)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    proxies = [proxy.strip() for proxy in args.proxies.split(",") if proxy.strip()]
    if not proxies:
        raise RuntimeError("At least one HTTP proxy is required")
    jobs = []
    for index, layer in enumerate(layers):
        digest = layer["digest"]
        url = (
            f"https://{parsed.netloc}/v2/{repository}/blobs/{digest}"
        )
        jobs.append((url, digest, proxies[index % len(proxies)]))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = [
            executor.submit(
                download_layer, url, digest, args.cache_dir, proxy
            )
            for url, digest, proxy in jobs
        ]
        downloaded = [future.result() for future in futures]

    staging = args.cache_dir / "unpacked"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    for layer in downloaded:
        safe_extract(layer, staging)

    args.weights_root.mkdir(parents=True, exist_ok=True)
    assemble(staging, args.weights_root)
    verify(args.weights_root)
    shutil.rmtree(args.cache_dir)
    print(f"Weights ready at {args.weights_root}", flush=True)


if __name__ == "__main__":
    main()
