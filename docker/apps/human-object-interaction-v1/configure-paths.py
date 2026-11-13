"""Adapt upstream machine-specific paths inside the image only."""

import re
from pathlib import Path


def replace_assignment(path, name, expression):
    text = path.read_text()
    text, count = re.subn(r"^" + name + r"\s*=.*$", name + " = " + expression, text, flags=re.M)
    if count != 1:
        raise RuntimeError("Expected one {} assignment in {}, found {}".format(name, path, count))
    path.write_text(text)


def configure(root):
    # Both projects read the kinematic tree separately from their dataset's
    # SMPL-X/SMPL-H body files. Expose that additional SMPL-H path explicitly.
    dataset = "cano_traj_dataset.py" if root.name == "chois_release" else "hand_foot_dataset.py"
    replace_assignment(
        root / "manip/data" / dataset,
        "SMPLH_PATH",
        'os.environ.get("SMPLH_PATH", "/models/smplh_amass")',
    )
    vis = root / "manip/vis/blender_vis_mesh_motion.py"
    replace_assignment(vis, "BLENDER_PATH", 'os.environ.get("BLENDER_PATH", "/usr/local/bin/blender")')
    folder = "BLENDER_UTILS_ROOT_FOLDER" if root.name == "chois_release" else "BLENDER_SCRIPTS_FOLDER"
    replace_assignment(vis, folder, 'os.path.dirname(os.path.abspath(__file__))')


if __name__ == "__main__":
    for project in ("chois_release", "omomo_release"):
        configure(Path("/app") / project)

    trainer = Path("/app/chois_release/trainer_chois.py")
    text = trainer.read_text()
    old = "clip.load(clip_version, device='cuda',"
    new = 'clip.load(os.environ.get("CLIP_MODEL_PATH", clip_version), device=\'cuda\', download_root=os.environ.get("CLIP_DOWNLOAD_ROOT", "/models/clip"),'
    if text.count(old) != 1:
        raise RuntimeError("CHOIS CLIP loader changed; review the offline model path patch")
    trainer.write_text(text.replace(old, new))

    vis = Path("/app/omomo_release/manip/vis/blender_vis_mesh_motion.py")
    text = vis.read_text()
    old = 'scene_blend_path = os.path.join(BLENDER_SCRIPTS_FOLDER, "floor_colorful_mat.blend")'
    new = 'scene_blend_path = scene_blend_path or os.environ.get("OMOMO_BLENDER_SCENE", "/app/omomo_release/data/blender_files/floor_colorful_mat.blend")'
    if text.count(old) != 1:
        raise RuntimeError("OMOMO Blender scene loader changed; review the asset path patch")
    vis.write_text(text.replace(old, new))
