"""Exercise CUDA and selected compiled extensions in an HOI environment.

Run inside the image with a GPU. This does not load pretrained models, start
Isaac Sim, or replace full inference on real assets.
"""
import argparse

import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('environment', choices=['hoi', 'light', 'interact', 'haic', 'grail'])
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError(f'CUDA is unavailable for {args.environment}: torch={torch.__version__}, '
                           f'torch CUDA={torch.version.cuda}')

    points = torch.tensor([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]], device='cuda')
    assert torch.equal((points * points).sum(dim=-1).cpu(), torch.tensor([[0., 1., 1.]]))

    if args.environment in ('hoi', 'light', 'interact'):
        from pytorch3d.ops import knn_points

        nearest = knn_points(points, points, K=1)
        assert torch.equal(nearest.idx[..., 0].cpu(), torch.tensor([[0, 1, 2]]))
        assert torch.equal(nearest.dists.cpu(), torch.zeros(1, 3, 1))
        print('PyTorch3D CUDA nearest-neighbour check passed')

    if args.environment == 'interact':
        from pointnet2_ops.pointnet2_utils import furthest_point_sample

        sampled = furthest_point_sample(points.contiguous(), 2)
        assert sampled.shape == (1, 2)
        assert bool(((sampled >= 0) & (sampled < 3)).all())
        print('PointNet2 CUDA sampling check passed')

    if args.environment == 'grail':
        import nvdiffrast.torch as dr

        dr.RasterizeCudaContext()
        print('GRAIL nvdiffrast CUDA context created')

    torch.cuda.synchronize()
    print(f'{args.environment}: GPU={torch.cuda.get_device_name(0)}, '
          f'torch={torch.__version__}, CUDA={torch.version.cuda}')


if __name__ == '__main__':
    main()
