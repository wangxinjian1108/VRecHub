#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
THIRDPARTY_VGGT_OMEGA = REPO_ROOT / "thirdparty" / "vggt-omega"
if str(THIRDPARTY_VGGT_OMEGA) not in sys.path:
    sys.path.insert(0, str(THIRDPARTY_VGGT_OMEGA))

from vggt_omega.models import VGGTOmega  # noqa: E402
from vggt_omega.utils.load_fn import load_and_preprocess_images  # noqa: E402
from vggt_omega.utils.pose_enc import encoding_to_camera  # noqa: E402


DEFAULT_CHECKPOINT = Path("/opt/var/models/vggt-omega/vggt_omega_1b_512.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VGGT-Omega inference on a directory of images.")
    parser.add_argument("--image-dir", type=Path, required=True, help="Input image directory.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory.")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--image-resolution", type=int, default=512)
    parser.add_argument("--max-frames", type=int, default=200)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--conf-thres", type=float, default=20.0)
    parser.add_argument("--max-points", type=int, default=300000)
    return parser.parse_args()


def list_images(image_dir: Path, max_frames: int) -> list[Path]:
    images = sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    )
    if not images:
        raise FileNotFoundError(f"No images found under {image_dir}")
    if max_frames > 0:
        images = images[:max_frames]
    return images


def load_model(checkpoint_path: Path, device: str) -> VGGTOmega:
    if not torch.cuda.is_available() and device.startswith("cuda"):
        raise RuntimeError("CUDA is required for VGGT-Omega inference.")
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    model = VGGTOmega().eval()
    state_dict = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(state_dict)
    return model.to(device)


def tensor_to_numpy_batch(value: torch.Tensor) -> np.ndarray:
    array = value.detach().float().cpu().numpy()
    if array.shape[0] == 1:
        return array[0]
    return array


def unproject_depth_map_to_point_map(
    depth_map: np.ndarray,
    extrinsic_w2c: np.ndarray,
    intrinsic: np.ndarray,
) -> np.ndarray:
    depth = depth_map[..., 0]
    num_frames, height, width = depth.shape
    y, x = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    x = np.broadcast_to(x[None], (num_frames, height, width))
    y = np.broadcast_to(y[None], (num_frames, height, width))

    fx = intrinsic[:, 0, 0][:, None, None]
    fy = intrinsic[:, 1, 1][:, None, None]
    cx = intrinsic[:, 0, 2][:, None, None]
    cy = intrinsic[:, 1, 2][:, None, None]

    camera_points = np.stack(
        [
            (x - cx) / fx * depth,
            (y - cy) / fy * depth,
            depth,
        ],
        axis=-1,
    )

    rotation = extrinsic_w2c[:, :3, :3]
    translation = extrinsic_w2c[:, :3, 3]
    return np.einsum(
        "sij,shwj->shwi",
        np.transpose(rotation, (0, 2, 1)),
        camera_points - translation[:, None, None, :],
    )


def invert_extrinsics_w2c(extrinsic_w2c: np.ndarray) -> np.ndarray:
    full = np.tile(np.eye(4, dtype=np.float32), (extrinsic_w2c.shape[0], 1, 1))
    full[:, :3, :4] = extrinsic_w2c
    return np.linalg.inv(full)


def save_depth_preview(depth: np.ndarray, output_path: Path) -> None:
    valid = np.isfinite(depth) & (depth > 0.0)
    preview = np.zeros(depth.shape, dtype=np.float32)
    if np.any(valid):
        low = float(np.percentile(depth[valid], 1.0))
        high = float(np.percentile(depth[valid], 99.0))
        if high <= low:
            high = low + 1e-6
        preview = np.clip((depth - low) / (high - low), 0.0, 1.0)
    preview_u8 = np.round(preview * 255.0).astype(np.uint8)
    Image.fromarray(preview_u8, mode="L").save(output_path)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    depth_dir = args.output_dir / "depths"
    depth_vis_dir = args.output_dir / "depth_vis"
    pose_w2c_dir = args.output_dir / "poses_w2c"
    pose_c2w_dir = args.output_dir / "poses_c2w"
    for path in (depth_dir, depth_vis_dir, pose_w2c_dir, pose_c2w_dir):
        path.mkdir(parents=True, exist_ok=True)

    image_paths = list_images(args.image_dir, args.max_frames)
    manifest_path = args.output_dir / "selected_images.txt"
    manifest_path.write_text("\n".join(str(path) for path in image_paths) + "\n", encoding="utf-8")

    model = load_model(args.checkpoint, args.device)
    images = load_and_preprocess_images(
        [str(path) for path in image_paths],
        image_resolution=args.image_resolution,
    ).to(args.device)

    with torch.inference_mode():
        predictions = model(images)

    extrinsic_w2c, intrinsic = encoding_to_camera(
        predictions["pose_enc"],
        predictions["images"].shape[-2:],
    )
    predictions["extrinsic"] = extrinsic_w2c
    predictions["intrinsic"] = intrinsic

    predictions_np: dict[str, np.ndarray] = {}
    for key in ("depth", "depth_conf", "pose_enc", "extrinsic", "intrinsic", "images"):
        predictions_np[key] = tensor_to_numpy_batch(predictions[key])

    world_points = unproject_depth_map_to_point_map(
        predictions_np["depth"],
        predictions_np["extrinsic"],
        predictions_np["intrinsic"],
    )
    predictions_np["world_points_from_depth"] = world_points
    extrinsic_c2w = invert_extrinsics_w2c(predictions_np["extrinsic"])
    camera_centers = extrinsic_c2w[:, :3, 3]

    for image_path, depth, pose_w2c, pose_c2w in zip(
        image_paths,
        predictions_np["depth"],
        predictions_np["extrinsic"],
        extrinsic_c2w,
    ):
        stem = image_path.stem
        np.save(depth_dir / f"{stem}.npy", depth[..., 0].astype(np.float32))
        save_depth_preview(depth[..., 0], depth_vis_dir / f"{stem}.png")
        np.savetxt(pose_w2c_dir / f"{stem}.txt", pose_w2c, fmt="%.8f")
        np.savetxt(pose_c2w_dir / f"{stem}.txt", pose_c2w, fmt="%.8f")

    np.save(args.output_dir / "extrinsic_w2c.npy", predictions_np["extrinsic"].astype(np.float32))
    np.save(args.output_dir / "extrinsic_c2w.npy", extrinsic_c2w.astype(np.float32))
    np.save(args.output_dir / "intrinsic.npy", predictions_np["intrinsic"].astype(np.float32))
    np.save(args.output_dir / "camera_centers.npy", camera_centers.astype(np.float32))
    np.save(args.output_dir / "depth_conf.npy", predictions_np["depth_conf"].astype(np.float32))
    np.savez_compressed(
        args.output_dir / "prediction_bundle.npz",
        pose_enc=predictions_np["pose_enc"].astype(np.float32),
        extrinsic_w2c=predictions_np["extrinsic"].astype(np.float32),
        extrinsic_c2w=extrinsic_c2w.astype(np.float32),
        intrinsic=predictions_np["intrinsic"].astype(np.float32),
        camera_centers=camera_centers.astype(np.float32),
    )

    glb_exported = False
    glb_error = None
    try:
        from visual_util import predictions_to_glb  # noqa: E402

        scene = predictions_to_glb(
            predictions_np,
            conf_thres=args.conf_thres,
            show_cam=True,
            mask_sky=False,
            max_points=args.max_points,
        )
        scene.export(file_obj=args.output_dir / "scene.glb")
        glb_exported = True
    except Exception as exc:  # pragma: no cover
        glb_error = repr(exc)

    metadata = {
        "image_dir": str(args.image_dir.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "checkpoint": str(args.checkpoint),
        "image_resolution": args.image_resolution,
        "frame_count": len(image_paths),
        "image_names": [path.name for path in image_paths],
        "prediction_shape": list(predictions_np["depth"].shape),
        "device": args.device,
        "conf_thres": args.conf_thres,
        "max_points": args.max_points,
        "glb_exported": glb_exported,
        "glb_error": glb_error,
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    del predictions
    del images
    torch.cuda.empty_cache()
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
