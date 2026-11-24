"""Exercise CHOIS or OMOMO EMA denoisers on CUDA with synthetic inputs.

This verifies model execution, not dataset-dependent end-to-end generation.
Run from the matching upstream project directory in the weighted HOI image.
"""
import argparse
import os
import sys
sys.path.insert(0, os.getcwd())
from types import SimpleNamespace
import torch

parser = argparse.ArgumentParser()
parser.add_argument('model', choices=['chois', 'stage1', 'stage2'])
parser.add_argument('checkpoint')
parser.add_argument('--sample-steps', type=int, default=0,
                    help='Also exercise the sampler on synthetic inputs (1000 = full schedule)')
parser.add_argument('--frames', type=int, default=8,
                    help='Synthetic sequence length, up to the 120-frame model window')
args = parser.parse_args()
if not 1 <= args.frames <= 120:
    parser.error('--frames must be between 1 and 120')
if args.model == 'chois':
    from manip.model.transformer_object_motion_cond_diffusion import ObjectCondGaussianDiffusion as Model
    dim, cond_dim = 220, 220 + 256
    extra = dict(input_first_human_pose=True, use_object_keypoints=True)
elif args.model == 'stage1':
    from manip.model.transformer_hand_foot_manip_cond_diffusion_model import CondGaussianDiffusion as Model
    dim, cond_dim = 6, 3 + 256
    extra = dict(batch_size=1)
else:
    from manip.model.transformer_fullbody_cond_diffusion_model import CondGaussianDiffusion as Model
    dim, cond_dim = 204, 204
    extra = dict(batch_size=1)
model = Model(SimpleNamespace(), d_feats=dim, d_model=512, n_dec_layers=4, n_head=4,
              d_k=256, d_v=256, max_timesteps=121, out_dim=dim, timesteps=1000,
              objective='pred_x0', loss_type='l1', **extra)
checkpoint = torch.load(args.checkpoint, map_location='cpu')
state = {k[len('ema_model.'):]: v for k, v in checkpoint['ema'].items()
         if k.startswith('ema_model.')}
assert state
load_result = model.load_state_dict(state, strict=False)
allowed = {'body_shape_encoder.0.weight', 'body_shape_encoder.0.bias',
           'body_shape_encoder.2.weight', 'body_shape_encoder.2.bias',
           'contact_embedding.action_embedding'} if args.model == 'chois' else set()
assert not load_result.missing_keys and set(load_result.unexpected_keys) <= allowed
assert torch.cuda.is_available()
torch.manual_seed(17)
model = model.cuda().eval()
with torch.inference_mode():
    x = torch.randn(1, args.frames, dim, device='cuda')
    condition = torch.randn(1, args.frames, cond_dim, device='cuda')
    t = torch.tensor([500], device='cuda')
    y = model.denoise_fn(x, t, condition)
    torch.cuda.synchronize()
assert y.shape == x.shape and torch.isfinite(y).all()
print(f'{args.model} EMA denoiser: {tuple(y.shape)}, finite=True, GPU={torch.cuda.get_device_name(0)}')

if args.sample_steps:
    if not 1 <= args.sample_steps <= model.num_timesteps:
        raise ValueError('sample steps must be within the checkpoint diffusion schedule')
    # Limiting the checkpoint's 1,000-step loop tests the sampling code, but
    # does not produce a sample from the original diffusion schedule.
    full_schedule = args.sample_steps == model.num_timesteps
    model.num_timesteps = args.sample_steps
    with torch.inference_mode():
        if args.model == 'chois':
            import clip
            clip_model, _ = clip.load('/models/clip/ViT-B-32.pt', device='cuda', jit=False)
            tokens = clip.tokenize(['a person carries a box']).cuda()
            language = clip_model.encode_text(tokens).float()
            model.seq_len = x.shape[1]
            result = model.sample(x, torch.randn(1, 1, 3072, device='cuda'),
                                  cond_mask=torch.ones_like(x), language_input=language)
        elif args.model == 'stage1':
            geometry = torch.randn(1, x.shape[1], 3 + 3072, device='cuda')
            result = model.sample(x, geometry)
        else:
            result = model.sample(x, cond_mask=torch.ones_like(x))
        torch.cuda.synchronize()
    assert result.shape == x.shape and torch.isfinite(result).all()
    schedule = 'full' if full_schedule else 'shortened'
    print(f'{args.model} {schedule} sampler: {args.sample_steps} steps, {tuple(result.shape)}, finite=True')
