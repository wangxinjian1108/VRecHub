"""Check official checkpoints against inference architectures without datasets."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import argparse
from types import SimpleNamespace
import torch

parser = argparse.ArgumentParser()
parser.add_argument('model', choices=['chois', 'stage1', 'stage2'])
parser.add_argument('checkpoint')
args = parser.parse_args()
if args.model == 'chois':
    from manip.model.transformer_object_motion_cond_diffusion import ObjectCondGaussianDiffusion as Model
    dimensions = 3 + 9 + 24 * 3 + 22 * 6 + 4
    extra = dict(input_first_human_pose=True, use_object_keypoints=True)
else:
    if args.model == 'stage1':
        from manip.model.transformer_hand_foot_manip_cond_diffusion_model import CondGaussianDiffusion as Model
        dimensions = 6
    else:
        from manip.model.transformer_fullbody_cond_diffusion_model import CondGaussianDiffusion as Model
        dimensions = 24 * 3 + 22 * 6
    extra = dict(batch_size=1)
model = Model(SimpleNamespace(), d_feats=dimensions, d_model=512, n_dec_layers=4,
              n_head=4, d_k=256, d_v=256, max_timesteps=121, out_dim=dimensions,
              timesteps=1000, objective='pred_x0', loss_type='l1', **extra)
checkpoint = torch.load(args.checkpoint, map_location='cpu')
allowed_extra = {
    'body_shape_encoder.0.weight', 'body_shape_encoder.0.bias',
    'body_shape_encoder.2.weight', 'body_shape_encoder.2.bias',
    'contact_embedding.action_embedding',
} if args.model == 'chois' else set()

def check(state):
    result = model.load_state_dict(state, strict=False)
    assert not result.missing_keys, result.missing_keys
    assert set(result.unexpected_keys) <= allowed_extra, result.unexpected_keys
    if result.unexpected_keys:
        print('Unused training heads (also ignored by upstream inference):', result.unexpected_keys)

check(checkpoint['model'])
# Both trainers sample from the EMA copy rather than the raw training network.
ema = {key[len('ema_model.'):]: value for key, value in checkpoint['ema'].items()
       if key.startswith('ema_model.')}
assert ema, 'EMA inference weights are missing'
check(ema)
print('Training and EMA weights match inference architecture:', args.checkpoint)
