"""Load InterAct weights and exercise its evaluator text encoder offline.

Run from /app/InterAct/text2interaction in interact with a GPU: the upstream
constructor deserializes evaluator tensors on CUDA without map_location.
This does not exercise full motion sampling or SMPL-H fitting.
"""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, os.getcwd())
import torch
from model.hoi_diff import HOIDiff

torch.set_num_threads(4)
root = Path("/models/interact/save/pretrained")
args = SimpleNamespace(**json.loads((root / "args.json").read_text()))
model = HOIDiff(
    modeltype="", njoints=476 + 18 + 78 * 6, nfeats=1, num_actions=1,
    translation=True, pose_rep="rot6d", glob=True, glob_rot=True,
    latent_dim=512, ff_size=1024, num_layers=8, num_heads=4,
    dropout=.1, data_rep="hml_vec", cond_mode="text", cond_mask_prob=.1,
    arch="trans_enc", emb_trans_dec=False, clip_version="ViT-B/32",
    dataset="interact", args=args,
)
state = torch.load(root / "model.pt", map_location="cpu")
state = state.get("model_avg", state.get("model", state))
result = model.load_state_dict(state, strict=False)
assert not result.unexpected_keys, result.unexpected_keys
assert all(k.startswith("textencoder.") for k in result.missing_keys), result.missing_keys
model.eval()
with torch.inference_mode():
    output = model.textencoder(["a person pushes a box"])
assert output.loc.shape == (1, 256) and torch.isfinite(output.loc).all()
print("InterAct generator loaded; evaluator text encoder + DistilBERT offline forward passed",
      tuple(output.loc.shape), flush=True)
