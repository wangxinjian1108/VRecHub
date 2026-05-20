#!/usr/bin/env python3
import argparse
import csv
import json
import math
from datetime import datetime
from html import escape
from pathlib import Path

import numpy as np
from PIL import Image
import yaml

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None


CARLA_DEPTH_FAR_METERS = 1000.0
CARLA_DEPTH_DENOM = float(256**3 - 1)
FRAME_TO_CAMERA = {
    "FRAME_CAMERA360_BLEFT": "CAM360_BLEFT",
    "FRAME_CAMERA360_BRIGHT": "CAM360_BRIGHT",
    "FRAME_CAMERA360_FRONT_LEFT": "CAM360_F_LEFT",
    "FRAME_CAMERA360_FRONT_RIGHT": "CAM360_F_RIGHT",
    "FRAME_CAMERA360_FLEFT": "CAM360_FLEFT",
    "FRAME_CAMERA360_FRIGHT": "CAM360_FRIGHT",
    "FRAME_CAMERA360_REAR": "CAM360_REAR",
}
METRIC_KEYS = ("abs_rel", "sq_rel", "mae", "rmse", "rmse_log", "delta1", "delta2", "delta3")
METRIC_LABELS = {
    "abs_rel": "AbsRel",
    "sq_rel": "SqRel",
    "mae": "MAE",
    "rmse": "RMSE",
    "rmse_log": "RMSE(log)",
    "delta1": "delta < 1.25",
    "delta2": "delta < 1.25^2",
    "delta3": "delta < 1.25^3",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate VGGT-Omega CARLA inference with Umeyama scale alignment."
    )
    dataset_root = Path("/root/carla_data/CARLA_1101_Town10HD_ClearNoon_v25_w30_r100.0")
    default_inference = dataset_root / "model_inference" / "VGGT-Omega"
    parser.add_argument("--inference-dir", type=Path, default=default_inference)
    parser.add_argument("--dataset-root", type=Path, default=dataset_root)
    parser.add_argument("--camera-name", default="CAM360_F_LEFT")
    parser.add_argument("--model-name", default="VGGT-Omega")
    parser.add_argument("--far-plane", type=float, default=CARLA_DEPTH_FAR_METERS)
    parser.add_argument("--min-depth", type=float, default=1e-3)
    parser.add_argument("--max-depth", type=float, default=CARLA_DEPTH_FAR_METERS)
    parser.add_argument("--far-plane-epsilon", type=float, default=1e-3)
    parser.add_argument(
        "--upsample-pred-to-gt",
        action="store_true",
        help="Resize predicted depth back to the original GT resolution before evaluation.",
    )
    parser.add_argument("--report-dir", type=Path, default=None)
    return parser.parse_args()


def load_manifest(manifest_path: Path) -> list[Path]:
    lines = [line.strip() for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [Path(line) for line in lines]


def decode_carla_depth(path: Path, far_plane: float) -> np.ndarray:
    image = np.asarray(Image.open(path))
    rgb = image[..., :3].astype(np.float32)
    depth = (rgb[..., 0] + rgb[..., 1] * 256.0 + rgb[..., 2] * 65536.0) / CARLA_DEPTH_DENOM
    return depth.astype(np.float32) * float(far_plane)


def resize_depth_nearest(depth: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    target_h, target_w = target_shape
    if depth.shape == (target_h, target_w):
        return depth.astype(np.float32, copy=False)
    pil_image = Image.fromarray(depth.astype(np.float32), mode="F")
    pil_image = pil_image.resize((target_w, target_h), Image.Resampling.NEAREST)
    return np.asarray(pil_image, dtype=np.float32)


def build_valid_mask(
    pred: np.ndarray,
    gt: np.ndarray,
    min_depth: float,
    max_depth: float,
    far_plane: float,
    far_plane_epsilon: float,
) -> np.ndarray:
    mask = (
        np.isfinite(pred)
        & np.isfinite(gt)
        & (pred > 0.0)
        & (gt >= float(min_depth))
        & (gt <= float(max_depth))
        & (gt < float(far_plane) - float(far_plane_epsilon))
    )
    return mask


def load_matrix4(path: Path) -> np.ndarray:
    matrix = np.loadtxt(path, dtype=np.float64)
    if matrix.shape != (4, 4):
        raise ValueError(f"Expected 4x4 matrix in {path}, got {matrix.shape}")
    return matrix


def euler_xyz_to_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]], dtype=np.float64)
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]], dtype=np.float64)
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    return rz @ ry @ rx


def transform_from_xyz_rpy(values: list[float]) -> np.ndarray:
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = euler_xyz_to_matrix(values[3], values[4], values[5])
    transform[:3, 3] = np.asarray(values[:3], dtype=np.float64)
    return transform


def load_camera_to_baselink(calib_yaml: Path) -> dict[str, np.ndarray]:
    payload = yaml.safe_load(calib_yaml.read_text(encoding="utf-8"))
    sensor_calibs = payload["vehicle"]["calibration"]["sensor_calibration"]
    camera_to_base: dict[str, np.ndarray] = {}
    for item in sensor_calibs:
        frame = item.get("source")
        if frame not in FRAME_TO_CAMERA:
            continue
        camera_to_base[FRAME_TO_CAMERA[frame]] = transform_from_xyz_rpy(item["transformation"])
    return camera_to_base


def estimate_similarity_transform(
    source_xyz: np.ndarray,
    target_xyz: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    source_mean = source_xyz.mean(axis=0)
    target_mean = target_xyz.mean(axis=0)
    source_centered = source_xyz - source_mean[None]
    target_centered = target_xyz - target_mean[None]
    covariance = (target_centered.T @ source_centered) / float(len(source_xyz))
    u, singular_values, v_t = np.linalg.svd(covariance)
    sign = np.eye(3, dtype=np.float64)
    if np.linalg.det(u) * np.linalg.det(v_t) < 0.0:
        sign[-1, -1] = -1.0
    rotation = u @ sign @ v_t
    source_var = float(np.mean(np.sum(source_centered**2, axis=1)))
    scale = float(np.trace(np.diag(singular_values) @ sign) / max(source_var, 1e-12))
    translation = target_mean - scale * (rotation @ source_mean)
    return rotation, translation, scale


def apply_sim3_to_c2w(
    pose: np.ndarray,
    rotation: np.ndarray,
    translation: np.ndarray,
    scale: float,
) -> np.ndarray:
    aligned = np.eye(4, dtype=np.float64)
    aligned[:3, :3] = rotation @ pose[:3, :3]
    aligned[:3, 3] = scale * (rotation @ pose[:3, 3]) + translation
    return aligned


def init_accumulator() -> dict[str, float]:
    return {
        "valid_pixels": 0.0,
        "abs_rel_sum": 0.0,
        "sq_rel_sum": 0.0,
        "mae_sum": 0.0,
        "rmse_sum": 0.0,
        "rmse_log_sum": 0.0,
        "delta1_sum": 0.0,
        "delta2_sum": 0.0,
        "delta3_sum": 0.0,
    }


def update_accumulator(acc: dict[str, float], pred: np.ndarray, gt: np.ndarray) -> dict[str, float]:
    abs_err = np.abs(pred - gt)
    sq_err = (pred - gt) ** 2
    log_err = np.log(pred) - np.log(gt)
    thresh = np.maximum(gt / pred, pred / gt)

    acc["valid_pixels"] += float(pred.size)
    acc["abs_rel_sum"] += float(np.sum(abs_err / gt))
    acc["sq_rel_sum"] += float(np.sum(sq_err / gt))
    acc["mae_sum"] += float(np.sum(abs_err))
    acc["rmse_sum"] += float(np.sum(sq_err))
    acc["rmse_log_sum"] += float(np.sum(log_err**2))
    acc["delta1_sum"] += float(np.sum(thresh < 1.25))
    acc["delta2_sum"] += float(np.sum(thresh < 1.25**2))
    acc["delta3_sum"] += float(np.sum(thresh < 1.25**3))
    return acc


def finalize_accumulator(acc: dict[str, float]) -> dict[str, float]:
    n = float(acc["valid_pixels"])
    if n <= 0.0:
        return {key: math.nan for key in ("abs_rel", "sq_rel", "mae", "rmse", "rmse_log", "delta1", "delta2", "delta3")} | {
            "valid_pixels": 0
        }
    return {
        "valid_pixels": int(n),
        "abs_rel": acc["abs_rel_sum"] / n,
        "sq_rel": acc["sq_rel_sum"] / n,
        "mae": acc["mae_sum"] / n,
        "rmse": math.sqrt(acc["rmse_sum"] / n),
        "rmse_log": math.sqrt(acc["rmse_log_sum"] / n),
        "delta1": acc["delta1_sum"] / n,
        "delta2": acc["delta2_sum"] / n,
        "delta3": acc["delta3_sum"] / n,
    }


def compute_frame_metrics(pred: np.ndarray, gt: np.ndarray) -> dict[str, float]:
    acc = init_accumulator()
    update_accumulator(acc, pred, gt)
    return finalize_accumulator(acc)


def fmt(value: object, digits: int = 6) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "nan"


def save_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_for_display(depth: np.ndarray, mask: np.ndarray) -> np.ndarray:
    preview = np.zeros(depth.shape, dtype=np.float32)
    if np.any(mask):
        low = float(np.percentile(depth[mask], 1.0))
        high = float(np.percentile(depth[mask], 99.0))
        if high <= low:
            high = low + 1e-6
        preview = np.clip((depth - low) / (high - low), 0.0, 1.0)
    return preview


def save_qualitative_panel(
    output_path: Path,
    rgb_path: Path,
    gt_depth: np.ndarray,
    pred_depth_aligned: np.ndarray,
    valid_mask: np.ndarray,
    title: str,
) -> None:
    if plt is None:
        return
    rgb = np.asarray(Image.open(rgb_path))[..., :3]
    gt_vis = normalize_for_display(gt_depth, valid_mask)
    pred_vis = normalize_for_display(pred_depth_aligned, valid_mask)
    abs_rel = np.zeros_like(gt_depth, dtype=np.float32)
    abs_rel[valid_mask] = np.abs(pred_depth_aligned[valid_mask] - gt_depth[valid_mask]) / np.maximum(gt_depth[valid_mask], 1e-6)
    vmax = 1.0
    if np.any(valid_mask):
        vmax = min(1.0, float(np.percentile(abs_rel[valid_mask], 99.0)))

    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
    axes[0].imshow(rgb)
    axes[0].set_title("RGB")
    axes[1].imshow(gt_vis, cmap="viridis")
    axes[1].set_title("GT Depth")
    axes[2].imshow(pred_vis, cmap="viridis")
    axes[2].set_title("Pred Depth x Umeyama Scale")
    axes[3].imshow(abs_rel, cmap="magma", vmin=0.0, vmax=vmax)
    axes[3].set_title("AbsRel")
    for ax in axes:
        ax.axis("off")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_pose_topdown(output_path: Path, pred_xyz: np.ndarray, gt_xyz: np.ndarray) -> None:
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    ax.plot(gt_xyz[:, 0], gt_xyz[:, 1], "-o", markersize=2.5, linewidth=1.2, label="GT")
    ax.plot(pred_xyz[:, 0], pred_xyz[:, 1], "-o", markersize=2.5, linewidth=1.2, label="Pred Aligned")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("Top-Down Camera Centers")
    ax.grid(alpha=0.3)
    ax.axis("equal")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_absrel_curve(output_path: Path, frame_rows: list[dict[str, object]]) -> None:
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(10, 4.0))
    x = [int(row["sequence_index"]) for row in frame_rows]
    y = [float(row["umeyama_abs_rel"]) for row in frame_rows]
    ax.plot(x, y, linewidth=1.2, color="#0f766e")
    ax.set_xlabel("Frame")
    ax.set_ylabel("AbsRel")
    ax.set_title("Per-Frame AbsRel After Umeyama Scale Alignment")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def render_html(
    report_path: Path,
    summary: dict[str, object],
    frame_rows: list[dict[str, object]],
    qualitative_relpaths: list[str],
) -> None:
    metric_header = "".join(f"<th>{escape(METRIC_LABELS[key])}</th>" for key in METRIC_KEYS)
    metrics_row = "".join(f"<td>{fmt(summary['umeyama_metrics'][key])}</td>" for key in METRIC_KEYS)
    worst_rows = "\n".join(
        "<tr>"
        f"<td>{int(row['sequence_index'])}</td>"
        f"<td>{escape(str(row['frame_name']))}</td>"
        f"<td>{fmt(row['pose_error_m'])}</td>"
        f"<td>{fmt(row['umeyama_abs_rel'])}</td>"
        f"<td>{int(row['valid_pixels'])}</td>"
        "</tr>"
        for row in sorted(frame_rows, key=lambda row: float(row["umeyama_abs_rel"]), reverse=True)[:12]
    )
    qualitative_html = "\n".join(
        f'<div class="qual"><img src="{escape(path)}" alt="{escape(path)}"></div>' for path in qualitative_relpaths
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(str(summary['model_name']))} CARLA Umeyama Evaluation</title>
  <style>
    body {{
      margin: 0;
      font-family: "Aptos", "Segoe UI", sans-serif;
      color: #172033;
      background:
        radial-gradient(circle at 15% 15%, rgba(15, 118, 110, .18), transparent 28%),
        radial-gradient(circle at 82% 18%, rgba(217, 119, 6, .18), transparent 30%),
        linear-gradient(135deg, #f8fafc, #eef4f7);
    }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 32px 18px 56px; }}
    .hero, .card {{
      background: rgba(255,255,255,.94);
      border: 1px solid #d8e0ea;
      border-radius: 22px;
      box-shadow: 0 18px 52px rgba(23,32,51,.08);
    }}
    .hero {{ padding: 28px; }}
    .card {{ margin-top: 18px; padding: 20px; overflow-x: auto; }}
    h1 {{ margin: 0 0 10px; font-size: clamp(30px, 4vw, 50px); letter-spacing: -0.04em; line-height: 1.02; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    p {{ color: #5f6f85; line-height: 1.5; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }}
    .stat {{ border: 1px solid #d8e0ea; border-radius: 18px; padding: 15px; background: #fbfdff; }}
    .label {{ color: #66768c; font-size: 13px; }}
    .value {{ margin-top: 6px; font-size: 24px; font-weight: 750; }}
    table {{ width: 100%; min-width: 900px; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #dbe3ef; padding: 10px 9px; text-align: left; white-space: nowrap; font-size: 14px; }}
    th {{ background: #f3f7fb; }}
    tr:last-child td, tr:last-child th {{ border-bottom: 0; }}
    code {{ background: #edf2f7; padding: 3px 7px; border-radius: 8px; }}
    .imgs {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
    .qual img {{ width: 100%; border-radius: 18px; border: 1px solid #d8e0ea; }}
    .plot img {{ width: 100%; border-radius: 18px; border: 1px solid #d8e0ea; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <h1>{escape(str(summary['model_name']))} CARLA Evaluation</h1>
    <p>Depth metrics are computed after removing CARLA far-plane pixels and aligning prediction scale with Umeyama estimated from predicted and GT camera centers.</p>
    <div class="grid">
      <div class="stat"><div class="label">Camera</div><div class="value">{escape(str(summary['camera_name']))}</div></div>
      <div class="stat"><div class="label">Frames</div><div class="value">{int(summary['frame_count'])}</div></div>
      <div class="stat"><div class="label">Umeyama Scale</div><div class="value">{fmt(summary['umeyama_scale'], 4)}</div></div>
      <div class="stat"><div class="label">Pose RMSE</div><div class="value">{fmt(summary['pose_rmse_m'], 3)} m</div></div>
    </div>
  </section>

  <section class="card">
    <h2>Inputs</h2>
    <p><strong>Inference dir:</strong> <code>{escape(str(summary['inference_dir']))}</code></p>
    <p><strong>Dataset root:</strong> <code>{escape(str(summary['dataset_root']))}</code></p>
    <p><strong>Eval mode:</strong> <code>{escape(str(summary['eval_mode']))}</code></p>
    <p><strong>Generated:</strong> <code>{escape(str(summary['generated_at']))}</code></p>
  </section>

  <section class="card">
    <h2>Overall Depth Metrics</h2>
    <table>
      <tr><th>Alignment</th>{metric_header}</tr>
      <tr><th>Umeyama Scale</th>{metrics_row}</tr>
    </table>
  </section>

  <section class="card plot">
    <h2>Plots</h2>
    <img src="pose_topdown.png" alt="pose_topdown">
    <img src="absrel_curve.png" alt="absrel_curve" style="margin-top:16px;">
  </section>

  <section class="card">
    <h2>Worst Frames</h2>
    <table>
      <tr><th>Seq</th><th>Frame</th><th>Pose Error m</th><th>AbsRel</th><th>Valid Pixels</th></tr>
      {worst_rows}
    </table>
  </section>

  <section class="card">
    <h2>Qualitative Frames</h2>
    <div class="imgs">
      {qualitative_html}
    </div>
  </section>
</main>
</body>
</html>
"""
    report_path.write_text(html, encoding="utf-8")


def main() -> int:
    args = parse_args()
    report_dir = args.report_dir or (args.inference_dir / "eval_umeyama")
    report_dir.mkdir(parents=True, exist_ok=True)
    qual_dir = report_dir / "qualitative"
    qual_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(args.inference_dir / "selected_images.txt")
    pred_poses = np.load(args.inference_dir / "extrinsic_c2w.npy").astype(np.float64)
    camera_to_base = load_camera_to_baselink(args.dataset_root / "PLANE_IMAGE_960_768" / "application.yaml")
    if args.camera_name not in camera_to_base:
        raise KeyError(f"Camera extrinsic not found for {args.camera_name}")

    gt_depth_dir = args.dataset_root / "PLANE_CARLADEPTH_960_768" / args.camera_name
    baselink_dir = args.dataset_root / "BASELINK_TO_MAP"

    rows: list[dict[str, object]] = []
    pred_centers = []
    gt_centers = []
    gt_poses = []
    for index, image_path in enumerate(manifest):
        stem = image_path.stem
        baselink_pose = load_matrix4(baselink_dir / f"{stem}.txt")
        gt_pose = baselink_pose @ camera_to_base[args.camera_name]
        gt_poses.append(gt_pose)
        pred_center = pred_poses[index, :3, 3]
        gt_center = gt_pose[:3, 3]
        pred_centers.append(pred_center)
        gt_centers.append(gt_center)
        rows.append(
            {
                "sequence_index": index,
                "frame_name": image_path.name,
                "frame_stem": stem,
                "rgb_path": str(image_path),
                "pred_center_x": pred_center[0],
                "pred_center_y": pred_center[1],
                "pred_center_z": pred_center[2],
                "gt_center_x": gt_center[0],
                "gt_center_y": gt_center[1],
                "gt_center_z": gt_center[2],
            }
        )

    pred_centers_np = np.asarray(pred_centers, dtype=np.float64)
    gt_centers_np = np.asarray(gt_centers, dtype=np.float64)
    rotation, translation, umeyama_scale = estimate_similarity_transform(pred_centers_np, gt_centers_np)
    aligned_poses = np.stack(
        [apply_sim3_to_c2w(pose, rotation, translation, umeyama_scale) for pose in pred_poses],
        axis=0,
    )
    aligned_centers = aligned_poses[:, :3, 3]
    pose_errors = np.linalg.norm(aligned_centers - gt_centers_np, axis=1)

    depth_acc = init_accumulator()
    frame_rows: list[dict[str, object]] = []
    frame_cache: list[dict[str, object]] = []
    for index, image_path in enumerate(manifest):
        stem = image_path.stem
        pred_depth_raw = np.load(args.inference_dir / "depths" / f"{stem}.npy").astype(np.float32)
        gt_depth_raw = decode_carla_depth(gt_depth_dir / f"{stem}.png", args.far_plane)
        if args.upsample_pred_to_gt:
            pred_depth_eval = resize_depth_nearest(pred_depth_raw, gt_depth_raw.shape)
            gt_depth_eval = gt_depth_raw
        else:
            pred_depth_eval = pred_depth_raw
            gt_depth_eval = resize_depth_nearest(gt_depth_raw, pred_depth_raw.shape)

        mask = build_valid_mask(
            pred_depth_eval,
            gt_depth_eval,
            args.min_depth,
            args.max_depth,
            args.far_plane,
            args.far_plane_epsilon,
        )
        aligned_depth = pred_depth_eval * float(umeyama_scale)
        if np.any(mask):
            metrics = compute_frame_metrics(aligned_depth[mask], gt_depth_eval[mask])
            update_accumulator(depth_acc, aligned_depth[mask], gt_depth_eval[mask])
        else:
            metrics = {key: math.nan for key in METRIC_KEYS} | {"valid_pixels": 0}
        row = {
            "sequence_index": index,
            "frame_name": image_path.name,
            "valid_pixels": int(metrics["valid_pixels"]),
            "pose_error_m": float(pose_errors[index]),
            "umeyama_abs_rel": float(metrics["abs_rel"]) if np.isfinite(metrics["abs_rel"]) else math.nan,
            "umeyama_rmse": float(metrics["rmse"]) if np.isfinite(metrics["rmse"]) else math.nan,
            "umeyama_delta1": float(metrics["delta1"]) if np.isfinite(metrics["delta1"]) else math.nan,
        }
        frame_rows.append(row)
        frame_cache.append(
            {
                "image_path": image_path,
                "gt_depth": gt_depth_eval,
                "aligned_depth": aligned_depth,
                "mask": mask,
                "pose_error_m": float(pose_errors[index]),
                "abs_rel": float(metrics["abs_rel"]) if np.isfinite(metrics["abs_rel"]) else math.inf,
            }
        )

    overall_metrics = finalize_accumulator(depth_acc)
    pose_rmse_m = float(np.sqrt(np.mean(pose_errors**2)))
    pose_median_m = float(np.median(pose_errors))

    save_csv(report_dir / "frame_metrics.csv", frame_rows)
    plot_pose_topdown(report_dir / "pose_topdown.png", aligned_centers, gt_centers_np)
    plot_absrel_curve(report_dir / "absrel_curve.png", frame_rows)

    qualitative_indices = []
    if frame_cache:
        qualitative_indices.append(0)
        qualitative_indices.append(len(frame_cache) // 2)
        worst_index = int(np.argmax([item["abs_rel"] for item in frame_cache]))
        qualitative_indices.append(worst_index)
    qualitative_indices = list(dict.fromkeys(qualitative_indices))
    qualitative_relpaths: list[str] = []
    for idx in qualitative_indices:
        item = frame_cache[idx]
        output_name = f"{idx:03d}_{item['image_path'].stem}.png"
        output_path = qual_dir / output_name
        title = (
            f"{item['image_path'].name} | pose_err={item['pose_error_m']:.3f} m | "
            f"AbsRel={item['abs_rel']:.4f}"
        )
        save_qualitative_panel(
            output_path,
            item["image_path"],
            item["gt_depth"],
            item["aligned_depth"],
            item["mask"],
            title,
        )
        qualitative_relpaths.append(str(Path("qualitative") / output_name))

    summary = {
        "model_name": args.model_name,
        "camera_name": args.camera_name,
        "frame_count": len(manifest),
        "umeyama_scale": float(umeyama_scale),
        "pose_rmse_m": pose_rmse_m,
        "pose_median_m": pose_median_m,
        "umeyama_metrics": overall_metrics,
        "eval_mode": "upsample_pred_to_gt" if args.upsample_pred_to_gt else "resize_gt_to_pred",
        "inference_dir": str(args.inference_dir.resolve()),
        "dataset_root": str(args.dataset_root.resolve()),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_json(report_dir / "summary.json", summary)
    render_html(report_dir / "report.html", summary, frame_rows, qualitative_relpaths)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
