"""Run both OMOMO diffusion stages with real weights and synthetic inputs.

Run from /app/omomo_release in the weighted HOI image. This tests the
handoff described by gen_fullbody_from_predicted_hand_foot, not the upstream
dataset preprocessing, body-model reconstruction, or visual quality.
"""
import argparse
import os
import sys
from types import SimpleNamespace

import torch

sys.path.insert(0, os.getcwd())
from manip.model.transformer_fullbody_cond_diffusion_model import CondGaussianDiffusion as FullBody
from manip.model.transformer_hand_foot_manip_cond_diffusion_model import CondGaussianDiffusion as Hands


def load_model(model_type, features, checkpoint):
    model = model_type(
        SimpleNamespace(), d_feats=features, d_model=512, n_dec_layers=4,
        n_head=4, d_k=256, d_v=256, max_timesteps=121, out_dim=features,
        timesteps=1000, objective='pred_x0', loss_type='l1', batch_size=1,
    )
    weights = torch.load(checkpoint, map_location='cpu')['ema']
    weights = {key[len('ema_model.'):]: value for key, value in weights.items()
               if key.startswith('ema_model.')}
    assert weights, 'checkpoint contains no EMA model weights'
    model.load_state_dict(weights, strict=True)
    return model.cuda().eval()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage1_checkpoint')
    parser.add_argument('stage2_checkpoint')
    parser.add_argument('--frames', type=int, default=120, choices=range(1, 121))
    args = parser.parse_args()
    assert torch.cuda.is_available(), 'CUDA is required'
    torch.manual_seed(17)
    with torch.inference_mode():
        hands_model = load_model(Hands, 6, args.stage1_checkpoint)
        hand_seed = torch.zeros(1, args.frames, 6, device='cuda')
        geometry = torch.randn(1, args.frames, 3 + 3072, device='cuda')
        hands = hands_model.sample(hand_seed, geometry)
        assert hands.shape == hand_seed.shape and torch.isfinite(hands).all()
        del hands_model, hand_seed, geometry
        torch.cuda.empty_cache()

        # Mirrors upstream convert_hand_foot_jpos_to_data_input and
        # prep_joint_condition_mask: palm joint positions are 22 and 23.
        body_seed = torch.zeros(1, args.frames, 204, device='cuda')
        body_seed[:, :, 66:72] = hands
        cond_mask = torch.ones_like(body_seed)
        cond_mask[:, :, 66:72] = 0
        assert torch.equal(body_seed[:, :, 66:72], hands)
        body_model = load_model(FullBody, 204, args.stage2_checkpoint)
        body = body_model.sample(body_seed, cond_mask=cond_mask)
        torch.cuda.synchronize()
        assert body.shape == body_seed.shape and torch.isfinite(body).all()
    print(f'OMOMO two-stage, full 1000-step schedules: hands={tuple(hands.shape)}, '
          f'body={tuple(body.shape)}, finite=True, GPU={torch.cuda.get_device_name(0)}')


if __name__ == '__main__':
    main()
