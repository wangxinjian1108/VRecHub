"""Load LIGHT's three real checkpoints and run offline CPU denoiser forwards.

Run from /app/LIGHT in the light environment. Inputs are synthetic; this does
not validate dataset preparation, body-model fitting, or complete generation.
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.getcwd())
import torch
from model.light import LIGHT

torch.set_num_threads(4)
root = Path("/models/light/save")
for folder in ["omomo_pretrained", "behave_pretrained", "interact_pretrained"]:
    args = json.loads((root / folder / "args.json").read_text())
    model = LIGHT(
        njoints=195, nfeats=1, translation=True,
        latent_dim=args["latent_dim"], num_layers=args["layers"],
        data_rep="hml_vec", cond_mode="text", arch=args["arch"],
        foot=args["foot"], cond_mask_prob=args["cond_mask_prob"],
        cond_mask_uniform=args["cond_mask_uniform"], mask_frames=args["mask_frames"],
    )
    checkpoint = next((root / folder).glob("*.pt"))
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    state = state.get("model_avg", state.get("model", state))
    # The upstream loader regenerates these fixed positional embeddings.
    for key in ["sequence_pos_encoder.pe", "embed_timestep.sequence_pos_encoder.pe"]:
        state.pop(key, None)
    result = model.load_state_dict(state, strict=False)
    assert not result.unexpected_keys, result.unexpected_keys
    assert all(k.startswith("clip_model.") or "sequence_pos_encoder" in k
               for k in result.missing_keys), result.missing_keys
    model.eval()
    frames = 4
    with torch.inference_mode():
        condition = {
            "text": ["a person pushes a box"],
            "obj_bps": torch.zeros(1, 6145), "beta": torch.zeros(1, 13),
            "mask": torch.ones(1, 1, 1, frames, dtype=torch.bool),
            "lengths": torch.tensor([frames]),
        }
        output = model(
            torch.zeros(1, 66, 1, frames),
            torch.full((1, frames * 3), 100, dtype=torch.long), y=condition,
            x2=torch.zeros(1, 9, 1, frames), x3=torch.zeros(1, 120, 1, frames),
        )
    assert output.shape == (1, 195, 1, frames) and torch.isfinite(output).all()
    print(folder, "real checkpoint + DistilBERT offline forward passed",
          tuple(output.shape), flush=True)
    del model, state, output
