#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
THIRDPARTY_PI3 = REPO_ROOT / "thirdparty" / "Pi3"
if str(THIRDPARTY_PI3) not in sys.path:
    sys.path.insert(0, str(THIRDPARTY_PI3))

from pi3.models.pi3x import Pi3X  # noqa: E402
from pi3.utils.basic import load_images_as_tensor, write_ply  # noqa: E402
from pi3.utils.geometry import depth_edge, recover_intrinsic_from_rays_d  # noqa: E402


DEFAULT_CHECKPOINT = Path("/opt/var/models/Pi3X/model.safetensors")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Pi3X inference on a directory of images.")
    parser.add_argument("--image-dir", type=Path, required=True, help="Input image directory.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory.")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--max-frames", type=int, default=200)
    parser.add_argument("--interval", type=int, default=1)
    parser.add_argument("--pixel-limit", type=int, default=255000)
    parser.add_argument("--device", default="cuda")
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


def load_model(checkpoint_path: Path, device: str) -> Pi3X:
    if not torch.cuda.is_available() and device.startswith("cuda"):
        raise RuntimeError("CUDA is required for Pi3X inference.")
    model = Pi3X(use_multimodal=False).eval()
    if hasattr(model, "disable_multimodal"):
        model.disable_multimodal()
    if checkpoint_path.suffix == ".safetensors":
        from safetensors.torch import load_file

        state = load_file(str(checkpoint_path))
    else:
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model.load_state_dict(state, strict=False)
    return model.to(device)


def save_depth_preview(depth: np.ndarray, output_path: Path) -> None:
    valid = np.isfinite(depth) & (depth > 0.0)
    preview = np.zeros(depth.shape, dtype=np.float32)
    if np.any(valid):
        low = float(np.percentile(depth[valid], 1.0))
        high = float(np.percentile(depth[valid], 99.0))
        if high <= low:
            high = low + 1e-6
        preview = np.clip((depth - low) / (high - low), 0.0, 1.0)
    Image.fromarray(np.round(preview * 255.0).astype(np.uint8), mode="L").save(output_path)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    depth_dir = args.output_dir / "depths"
    depth_vis_dir = args.output_dir / "depth_vis"
    pose_c2w_dir = args.output_dir / "poses_c2w"
    pose_w2c_dir = args.output_dir / "poses_w2c"
    for path in (depth_dir, depth_vis_dir, pose_c2w_dir, pose_w2c_dir):
        path.mkdir(parents=True, exist_ok=True)

    image_paths = list_images(args.image_dir, args.max_frames)
    (args.output_dir / "selected_images.txt").write_text(
        "\n".join(str(path) for path in image_paths) + "\n",
        encoding="utf-8",
    )

    model = load_model(args.checkpoint, args.device)
    imgs = load_images_as_tensor(
        str(args.image_dir),
        interval=args.interval,
        PIXEL_LIMIT=args.pixel_limit,
        verbose=False,
    )
    if args.max_frames > 0:
        imgs = imgs[: args.max_frames]
    imgs = imgs.to(args.device)

    dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
    with torch.no_grad():
        with torch.amp.autocast("cuda", dtype=dtype):
            res = model(imgs[None])

    local_points = res["local_points"][0].detach().float().cpu()
    points = res["points"][0].detach().float().cpu()
    conf_logits = res["conf"][0].detach().float().cpu()
    conf = torch.sigmoid(conf_logits)
    edge = depth_edge(local_points[..., 2], rtol=0.03)
    conf[edge] = 0.0
    camera_poses_c2w = res["camera_poses"][0].detach().float().cpu()
    camera_poses_w2c = torch.inverse(camera_poses_c2w)
    rays_d = torch.nn.functional.normalize(local_points, dim=-1)
    intrinsic = recover_intrinsic_from_rays_d(rays_d[None], force_center_principal_point=True)[0].detach().float().cpu()

    masks = conf[..., 0] > 0.1
    ply_path = args.output_dir / "points.ply"
    write_ply(points[masks], imgs.permute(0, 2, 3, 1).cpu()[masks], str(ply_path))

    for image_path, depth, pose_c2w, pose_w2c in zip(image_paths, local_points[..., 2], camera_poses_c2w, camera_poses_w2c):
        stem = image_path.stem
        depth_np = depth.numpy().astype(np.float32)
        np.save(depth_dir / f"{stem}.npy", depth_np)
        save_depth_preview(depth_np, depth_vis_dir / f"{stem}.png")
        np.savetxt(pose_c2w_dir / f"{stem}.txt", pose_c2w.numpy(), fmt="%.8f")
        np.savetxt(pose_w2c_dir / f"{stem}.txt", pose_w2c.numpy(), fmt="%.8f")

    np.save(args.output_dir / "extrinsic_c2w.npy", camera_poses_c2w.numpy().astype(np.float32))
    np.save(args.output_dir / "extrinsic_w2c.npy", camera_poses_w2c.numpy().astype(np.float32))
    np.save(args.output_dir / "intrinsic.npy", intrinsic.numpy().astype(np.float32))
    np.save(args.output_dir / "camera_centers.npy", camera_poses_c2w[:, :3, 3].numpy().astype(np.float32))
    np.save(args.output_dir / "depth_conf.npy", conf[..., 0].numpy().astype(np.float32))
    np.savez_compressed(
        args.output_dir / "prediction_bundle.npz",
        points=points.numpy().astype(np.float32),
        local_points=local_points.numpy().astype(np.float32),
        conf=conf.numpy().astype(np.float32),
        camera_poses_c2w=camera_poses_c2w.numpy().astype(np.float32),
        camera_poses_w2c=camera_poses_w2c.numpy().astype(np.float32),
        intrinsic=intrinsic.numpy().astype(np.float32),
    )

    metadata = {
        "model_name": "Pi3X",
        "image_dir": str(args.image_dir.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "checkpoint": str(args.checkpoint),
        "frame_count": len(image_paths),
        "image_names": [path.name for path in image_paths],
        "prediction_shape": list(local_points.shape),
        "pixel_limit": args.pixel_limit,
        "device": args.device,
        "ply_path": str(ply_path),
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    del res
    del imgs
    torch.cuda.empty_cache()
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
