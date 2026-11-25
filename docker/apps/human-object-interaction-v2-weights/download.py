#!/usr/bin/env python3
"""Download public, pinned assets into a local weight-packaging container."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import threading
import time
from urllib.parse import urljoin, urlsplit
import zipfile

import requests


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    if algorithm == "sha1":
        h.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def valid(path, spec):
    if not path.is_file() or (spec["size"] is not None and path.stat().st_size != spec["size"]):
        return False
    if path.stat().st_size == 0:
        return False
    if spec.get("sha256"):
        return digest(path) == spec["sha256"]
    if spec.get("git_blob"):
        return digest(path, "sha1") == spec["git_blob"]
    return True


def response(url, offset, size=None):
    # Route metadata through the public HF mirror and binary Xet/GitHub traffic
    # through the existing SOCKS connection. No proxy credentials are recorded.
    for _ in range(10):
        host = urlsplit(url).hostname
        session = requests.Session()
        session.trust_env = False
        if host and (host.endswith("google.com") or host.endswith("googleusercontent.com")):
            proxy = os.environ.get("HOI_HTTP_PROXY")
        elif host == "hf-mirror.com":
            proxy = None
        else:
            proxy = os.environ.get("HOI_SOCKS_PROXY")
        if proxy:
            session.proxies = {"https": proxy, "http": proxy}
        requested = f"bytes={offset}-{size - 1}" if size else f"bytes={offset}-"
        headers = {"Range": requested}
        if host == "api.github.com":
            headers["Accept"] = "application/vnd.github.raw+json"
        r = session.get(url, allow_redirects=False, stream=True,
                        headers=headers,
                        timeout=(20, 120))
        if r.is_redirect:
            url = urljoin(url, r.headers["Location"])
            r.close()
            continue
        return r
    raise RuntimeError("Too many download redirects")


def fetch_ranges(spec, target):
    """Bounded, resumable ranges avoid per-connection download throttling."""
    part = target.with_name(target.name + ".part")
    receipt = target.with_name(target.name + ".ranges.json")
    if receipt.exists():
        state = json.loads(receipt.read_text())
        if state["size"] != spec["size"]:
            raise ValueError("Range inventory size changed")
    else:
        state = {"size": spec["size"], "prefix": part.stat().st_size if part.exists() else 0, "done": []}
        receipt.write_text(json.dumps(state))
    done = set(state["done"])
    chunk_bytes = 512 * 1024 if spec["size"] < 64 * 1024**2 else 8 * 1024**2
    ranges = [(i, start, min(spec["size"] - 1, start + chunk_bytes - 1))
              for i, start in enumerate(range(state["prefix"], spec["size"], chunk_bytes))
              if i not in done]
    # Resolve expiring binary URLs once rather than rate-limit HF metadata.
    binary_url = spec.get("source_url", spec["url"])
    initial_size = 1024 if "raw.githubusercontent.com" in binary_url else spec["size"]
    with response(binary_url, 0, initial_size) as r:
        r.raise_for_status()
        resolved = r.url
    mutex = threading.Lock()
    fd = os.open(part, os.O_CREAT | os.O_RDWR, 0o644)
    os.ftruncate(fd, spec["size"])
    def worker(job):
        index, start, end = job
        for attempt in range(12):
            try:
                with response(resolved, start, end + 1) as r:
                    r.raise_for_status()
                    expected = f"bytes {start}-{end}/{spec['size']}"
                    if r.status_code != 206 or r.headers.get("Content-Range") != expected:
                        raise ValueError("Incorrect bounded range response")
                    offset = start
                    for block in r.iter_content(256 * 1024):
                        if offset + len(block) > end + 1:
                            raise ValueError("Range response exceeds requested bytes")
                        written = 0
                        while written < len(block):
                            written += os.pwrite(fd, block[written:], offset + written)
                        offset += len(block)
                    if offset != end + 1:
                        raise ValueError("Incomplete byte range")
                with mutex:
                    done.add(index)
                    state["done"] = sorted(done)
                    receipt.write_text(json.dumps(state))
                    print(f"Range {target.name}: {len(done)} chunks verified by size", flush=True)
                return
            except Exception as error:
                print(f"Range retry {target.name} {index}: {type(error).__name__}", flush=True)
                if attempt == 11:
                    raise RuntimeError(f"Failed range {index} of {target.name}") from None
                time.sleep(min(3 * (attempt + 1), 20))
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            list(pool.map(worker, ranges))
    finally:
        os.close(fd)
    if not valid(part, spec):
        raise ValueError(f"Final ranged download integrity check failed: {target}")
    part.replace(target)
    receipt.unlink()
    print(f"Installed {target} sha256={digest(target)}", flush=True)


def fetch(spec):
    target = Path(spec["target"])
    if valid(target, spec):
        print(f"Verified {target}", flush=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if spec.get("ranged", True) and spec["size"] is not None and (spec["size"] >= 64 * 1024**2 or
                                       (spec["group"] in {"haic-onnx", "grail-esrgan"} and spec["size"] >= 1024**2)):
        fetch_ranges(spec, target)
        return
    part = target.with_name(target.name + ".part")
    receipt = target.with_name(target.name + ".ranges.json")
    if receipt.exists():
        # An endpoint that ignores ranges needs a fresh sequential download.
        part.unlink(missing_ok=True)
        receipt.unlink()
    for attempt in range(12):
        try:
            offset = part.stat().st_size if part.exists() else 0
            if offset == spec["size"] and valid(part, spec):
                part.replace(target)
                return
            with response(spec["url"], offset, spec["size"]) as r:
                r.raise_for_status()
                if "html" in r.headers.get("Content-Type", ""):
                    raise RuntimeError("Server returned HTML instead of model data")
                if r.status_code == 206:
                    if not r.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                        raise RuntimeError("Download byte range differs from requested offset")
                else:
                    offset = 0
                print(f"Downloading {target.name} at {offset}/{spec['size']} bytes", flush=True)
                last = time.monotonic()
                with part.open("ab" if offset else "wb") as out:
                    for block in r.iter_content(256 * 1024):
                        out.write(block)
                        if time.monotonic() - last > 30:
                            print(f"Progress {target.name}: {out.tell()}/{spec['size']}", flush=True)
                            last = time.monotonic()
            if not valid(part, spec):
                if spec["size"] is None or part.stat().st_size == spec["size"]:
                    # Preserve unexpected complete files for inspection.
                    part.rename(part.with_name(part.name + f".mismatch-{int(time.time())}"))
                raise RuntimeError("Downloaded file differs from the pinned inventory")
            part.replace(target)
            target.chmod(0o644)
            print(f"Installed {target} sha256={digest(target)}", flush=True)
            return
        except Exception as error:
            # Exception messages may contain signed URLs: print only the type.
            print(f"Retry {attempt + 1}/12 {target.name}: {type(error).__name__}", flush=True)
            if attempt == 11:
                raise RuntimeError(f"Download failed: {target}") from None
            time.sleep(min(3 * (attempt + 1), 20))


def configure(lock):
    import runpy
    setup_path = Path("/workspace/grail/scripts/setup/setup_gem_x.py")
    if setup_path.exists():
        setup = runpy.run_path(str(setup_path))
        root = Path("/models/grail/gem-x")
        root.mkdir(parents=True, exist_ok=True)
        config = setup["native77_config"](root, camera_mode="background")
        (root / "body_video_native77_background.json").write_text(json.dumps(config, indent=2) + "\n")
    for spec in lock["assets"]:
        if not spec.get("extract_suffix") or not Path(spec["target"]).is_file():
            continue
        output = Path(spec["extracted_target"])
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(spec["target"]) as bundle:
            members = [m for m in bundle.infolist() if m.filename.endswith(spec["extract_suffix"])]
            if len(members) != 1:
                raise ValueError("Expected exactly one YOLOX ONNX archive member")
            with bundle.open(members[0]) as src, output.open("wb") as dst:
                shutil.copyfileobj(src, dst, 8 * 1024**2)
        if output.stat().st_size != spec["extracted_size"] or digest(output) != spec["extracted_sha256"]:
            raise ValueError("Extracted detector differs from the pinned release")
    for spec in lock["assets"]:
        if "hf" not in spec or not Path(spec["target"]).is_file():
            continue
        hf = spec["hf"]
        prefix = "datasets" if hf.get("repo_type") == "dataset" else "models"
        cache = Path("/models/huggingface/hub") / (prefix + "--" + hf["repo"].replace("/", "--"))
        dest = cache / "snapshots" / hf["revision"] / hf["filename"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.symlink_to(spec["target"])
        refs = cache / "refs"
        refs.mkdir(parents=True, exist_ok=True)
        (refs / "main").write_text(hf["revision"])
    # InterAct uses the older unnamespaced DistilBERT repository ID.
    alias = Path("/models/huggingface/hub/models--distilbert-base-uncased")
    alias.parent.mkdir(parents=True, exist_ok=True)
    if not alias.exists() and not alias.is_symlink():
        alias.symlink_to("models--distilbert--distilbert-base-uncased")
    for spec in lock.get("archives", []):
        archive = Path(spec["path"])
        if not archive.is_file():
            continue
        root = Path(spec["destination"])
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if member.is_dir() or "__MACOSX" in member.filename or member.filename.endswith(".DS_Store"):
                    continue
                relative = Path(member.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Unsafe checkpoint archive path")
                output = root / relative
                if output.is_file() and output.stat().st_size == member.file_size:
                    continue
                output.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as src, output.open("wb") as dst:
                    shutil.copyfileobj(src, dst, 8 * 1024**2)
        print(f"Extracted {archive} into {root}", flush=True)
    for source, destination in lock.get("links", []):
        dst = Path(destination)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.is_symlink() and os.readlink(dst) == source:
            continue
        if dst.exists():
            if dst.is_dir() and not any(dst.iterdir()):
                dst.rmdir()
            else:
                raise ValueError(f"Preserving existing path: {dst}")
        dst.symlink_to(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path(__file__).with_name("weights.lock.json"))
    parser.add_argument("--group")
    parser.add_argument("--root", type=Path, help="Host staging root instead of /models")
    parser.add_argument("--configure", action="store_true")
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    if args.group:
        assets = [a for a in lock["assets"] if a["group"] == args.group]
        if args.root:
            assets = [{**a, "target": str(args.root / Path(a["target"]).relative_to("/models"))}
                      for a in assets]
        if not assets:
            parser.error(f"Unknown asset group: {args.group}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(fetch, assets))
    if args.configure:
        configure(lock)


if __name__ == "__main__":
    main()
