#!/usr/bin/env python3
"""Verify baked weights and write an inventory of their final installed bytes."""
import argparse
import json
from pathlib import Path

from download import digest, valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path(__file__).with_name("weights.lock.json"))
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    records = {}
    inherited = json.loads(Path("/models/weights-manifest.json").read_text())
    for record in inherited["files"]:
        path = Path("/models") / record["path"]
        if not valid(path, record):
            raise ValueError(f"Inherited weight integrity check failed: {path}")
        records[str(path)] = {**record, "path": str(path), "origin": "weighted-v1"}
    for spec in lock["assets"]:
        path = Path(spec["target"])
        if not valid(path, spec):
            raise ValueError(f"Weight integrity check failed: {path}")
        records[str(path)] = {"path": str(path), "size": path.stat().st_size,
                              "sha256": digest(path), "origin": spec["group"]}
        if spec.get("extracted_target"):
            path = Path(spec["extracted_target"])
            if path.stat().st_size != spec["extracted_size"] or digest(path) != spec["extracted_sha256"]:
                raise ValueError(f"Extracted detector integrity check failed: {path}")
            records[str(path)] = {"path": str(path), "size": path.stat().st_size,
                                  "sha256": digest(path), "origin": spec["group"]}
    # Validate ZIP CRCs and compare installed files with their archive contents.
    import zipfile
    import zlib
    for bundle in lock["archives"]:
        with zipfile.ZipFile(bundle["path"]) as archive:
            for member in archive.infolist():
                if member.is_dir() or "__MACOSX" in member.filename or member.filename.endswith(".DS_Store"):
                    continue
                path = Path(bundle["destination"]) / member.filename
                if not path.is_file() or path.stat().st_size != member.file_size:
                    raise ValueError(f"Missing extracted checkpoint: {path}")
                crc = 0
                with path.open("rb") as stream:
                    for data in iter(lambda: stream.read(8 * 1024**2), b""):
                        crc = zlib.crc32(data, crc)
                if crc & 0xffffffff != member.CRC:
                    raise ValueError(f"Checkpoint archive CRC differs: {path}")
                records[str(path)] = {"path": str(path), "size": path.stat().st_size,
                                      "sha256": digest(path), "origin": "checkpoint-archive"}
    for source, destination in lock["links"]:
        if Path(destination).resolve() != Path(source).resolve() or not Path(destination).exists():
            raise ValueError(f"Model path link is missing or incorrect: {destination}")
    generated = Path("/models/grail/gem-x/body_video_native77_background.json")
    if not generated.is_file():
        raise ValueError("Generated GEM-X runtime configuration is missing")
    records[str(generated)] = {
        "path": str(generated), "size": generated.stat().st_size,
        "sha256": digest(generated), "origin": "generated-gem-x-runtime-config",
    }
    total = sum(r["size"] for r in records.values())
    output = {"base_image": lock["base_image"], "sources": lock,
              "files": list(records.values()), "bytes": total,
              "limitations": [
                  "SMPL-H/SMPL-X/DMPL body models are not supplied without a user-provided directory.",
                  "HAIC contains seven upstream MuJoCo ONNX policies, not Isaac Sim PyTorch checkpoints.",
                  "Training/evaluation datasets and full simulation assets are not model weights.",
              ]}
    if args.write_manifest:
        Path("/models/weights-manifest-v2.json").write_text(json.dumps(output, indent=2) + "\n")
    print(f"Verified {len(records)} assets, {total / 1024**3:.2f} GiB")


if __name__ == "__main__":
    main()
