#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SINGLE_SCRIPT = REPO_ROOT / "scripts" / "run_vggt_omega_inference.py"


DEFAULT_CAMERA_NAMES = (
    "CAM360_BLEFT",
    "CAM360_BRIGHT",
    "CAM360_FLEFT",
    "CAM360_FRIGHT",
    "CAM360_F_LEFT",
    "CAM360_F_RIGHT",
    "CAM360_REAR",
)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interleave multiple camera folders and run VGGT-Omega inference on the merged sequence."
    )
    parser.add_argument("--camera-root", type=Path, required=True, help="Directory containing camera subdirectories.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory.")
    parser.add_argument("--camera-names", default=",".join(DEFAULT_CAMERA_NAMES))
    parser.add_argument("--max-frames-per-camera", type=int, default=200)
    parser.add_argument("--image-resolution", type=int, default=512)
    parser.add_argument("--checkpoint", type=Path, default=Path("/opt/var/models/vggt-omega/vggt_omega_1b_512.pt"))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--conf-thres", type=float, default=20.0)
    parser.add_argument("--max-points", type=int, default=300000)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser.parse_args()


def list_images(path: Path) -> list[Path]:
    return sorted(
        item for item in path.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES
    )


def safe_rel_symlink(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    dst.symlink_to(os.path.relpath(src, dst.parent))


def build_interleaved_input(
    camera_root: Path,
    camera_names: list[str],
    generated_image_dir: Path,
    max_frames_per_camera: int,
    force: bool,
) -> list[dict[str, object]]:
    generated_image_dir.mkdir(parents=True, exist_ok=True)
    mapping: list[dict[str, object]] = []
    camera_to_images: dict[str, list[Path]] = {}
    for camera_name in camera_names:
        camera_dir = camera_root / camera_name
        if not camera_dir.is_dir():
            raise FileNotFoundError(f"Camera directory not found: {camera_dir}")
        images = list_images(camera_dir)
        if not images:
            raise FileNotFoundError(f"No images found in {camera_dir}")
        if max_frames_per_camera > 0:
            images = images[:max_frames_per_camera]
        camera_to_images[camera_name] = images

    reference_names = [path.name for path in camera_to_images[camera_names[0]]]
    for camera_name in camera_names[1:]:
        candidate_names = [path.name for path in camera_to_images[camera_name]]
        if candidate_names != reference_names:
            raise ValueError(f"Camera {camera_name} frame names do not match {camera_names[0]}")

    sequence_index = 0
    for frame_index, frame_name in enumerate(reference_names):
        for camera_name in camera_names:
            src = camera_to_images[camera_name][frame_index]
            dst_name = f"{sequence_index:06d}_{camera_name}_{frame_name}"
            dst = generated_image_dir / dst_name
            if dst.exists() and not force:
                raise FileExistsError(f"{dst} already exists. Use --force to overwrite.")
            safe_rel_symlink(src, dst)
            mapping.append(
                {
                    "sequence_index": sequence_index,
                    "frame_index": frame_index,
                    "camera": camera_name,
                    "source_name": frame_name,
                    "interleaved_name": dst_name,
                    "source_path": str(src.resolve()),
                }
            )
            sequence_index += 1
    return mapping


def main() -> int:
    args = parse_args()
    camera_names = [item.strip() for item in args.camera_names.split(",") if item.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    generated_image_dir = args.output_dir / "images"
    mapping = build_interleaved_input(
        args.camera_root.resolve(),
        camera_names,
        generated_image_dir,
        args.max_frames_per_camera,
        args.force,
    )
    mapping_path = args.output_dir / "interleaved_mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")

    metadata = {
        "camera_root": str(args.camera_root.resolve()),
        "camera_names": camera_names,
        "frame_count_per_camera": args.max_frames_per_camera,
        "interleaved_frames": len(mapping),
        "image_resolution": args.image_resolution,
        "checkpoint": str(args.checkpoint),
        "device": args.device,
    }
    (args.output_dir / "interleaved_summary.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if args.prepare_only:
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        return 0

    command = [
        sys.executable,
        str(RUN_SINGLE_SCRIPT),
            "--image-dir",
            str(generated_image_dir),
            "--output-dir",
            str(args.output_dir),
            "--checkpoint",
            str(args.checkpoint),
            "--image-resolution",
            str(args.image_resolution),
            "--max-frames",
            str(len(mapping)),
            "--device",
            args.device,
            "--conf-thres",
            str(args.conf_thres),
            "--max-points",
            str(args.max_points),
    ]
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
