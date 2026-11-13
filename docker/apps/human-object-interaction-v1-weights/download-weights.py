#!/usr/bin/env python3
"""Download pinned inference assets; verify every byte against weights.lock.json."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import time

import gdown
import requests


def checksum(path, spec):
    if not path.is_file() or ("size" in spec and path.stat().st_size != spec["size"]):
        return False
    algorithm = "sha256" if "sha256" in spec else "sha1"
    digest = hashlib.new(algorithm)
    if algorithm == "sha1":
        digest.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest() == spec.get("sha256", spec.get("git_blob"))


def download(url, path, spec):
    path.parent.mkdir(parents=True, exist_ok=True)
    if checksum(path, spec):
        print(f"Verified existing {path}", flush=True)
        return
    part = path.with_name(path.name + ".part")
    for attempt in range(5):
        try:
            if "drive_id" in spec:
                gdown.download(id=spec["drive_id"], output=str(part), quiet=True,
                               use_cookies=False, resume=True)
            else:
                offset = part.stat().st_size if part.exists() else 0
                headers = {"Range": f"bytes={offset}-"} if offset else {}
                with requests.get(url, stream=True, timeout=(30, 120), headers=headers) as response:
                    if response.status_code == 416:
                        part.unlink(missing_ok=True)
                        continue
                    response.raise_for_status()
                    if response.status_code == 206:
                        if not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                            raise RuntimeError("Server returned an unexpected byte range")
                        mode = "ab"
                    else:
                        mode = "wb"
                    with part.open(mode) as stream:
                        for block in response.iter_content(8 * 1024 * 1024):
                            stream.write(block)
            if not checksum(part, spec):
                part.unlink(missing_ok=True)
                raise RuntimeError(f"Checksum mismatch: {path.name}")
            part.replace(path)
            path.chmod(0o644)
            print(f"Downloaded and verified {path} ({path.stat().st_size} bytes)", flush=True)
            return
        except Exception as error:
            if attempt == 4:
                raise
            print(f"Retry {attempt + 1}/5 for {path.name}: {type(error).__name__}", flush=True)
            time.sleep(5 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/models"))
    parser.add_argument("--lock", type=Path, default=Path(__file__).with_name("weights.lock.json"))
    parser.add_argument("--hf-endpoint", default=os.environ.get("HF_ENDPOINT", "https://huggingface.co"))
    parser.add_argument("--omomo-archive", type=Path, help="Reuse a previously downloaded archive")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = json.loads(args.lock.read_text())
    jobs = []
    for repo in lock["huggingface"]:
        for asset in repo["files"]:
            url = f"{args.hf_endpoint.rstrip('/')}/{repo['repo']}/resolve/{repo['revision']}/{asset['path']}"
            jobs.append((url, root / repo["destination"] / asset["path"], asset))
    for asset in lock["downloads"]:
        jobs.append((asset["url"], root / asset["path"], asset))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        # Consume all results so worker exceptions fail the build.
        list(pool.map(lambda job: download(*job), jobs))
    omomo = lock["omomo_archive"]
    with tempfile.TemporaryDirectory(prefix="hoi-omomo-") as temporary:
        archive = args.omomo_archive or Path(temporary) / "pretrained_models.tar.gz"
        download(omomo["url"], archive, omomo)
        with tarfile.open(archive) as bundle:
            for name, destination in omomo["members"].items():
                member = bundle.getmember(name)
                if not member.isfile():
                    raise RuntimeError(f"Expected a regular checkpoint file: {name}")
                target = root / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o644)
                print(f"Extracted {target}", flush=True)
    # Transformers detects the MNTP adapter and follows this base-model path.
    # Preserve config.json's original _name_or_path for LLM2Vec prompt formatting.
    base = root / "text-encoders/meta-llama/Meta-Llama-3-8B-Instruct"
    for repo in lock["huggingface"]:
        config = root / repo["destination"] / "adapter_config.json"
        if config.exists():
            data = json.loads(config.read_text())
            data["base_model_name_or_path"] = str(base)
            config.write_text(json.dumps(data, indent=2) + "\n")
    # Record hashes of the final installed files, including the relocated configs.
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "weights-manifest.json":
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(block)
            files.append({"path": str(path.relative_to(root)), "size": path.stat().st_size,
                          "sha256": digest.hexdigest()})
    (root / "weights-manifest.json").write_text(json.dumps({"sources": lock, "files": files}, indent=2) + "\n")
    print(f"Installed {len(files)} verified assets, {sum(f['size'] for f in files) / 1024**3:.2f} GiB", flush=True)


if __name__ == "__main__":
    main()
