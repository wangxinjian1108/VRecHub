# Docker Images

| 项目 | Docker 镜像 | CUDA | PyTorch | 论文 | 描述 |
|------|------------|------|---------|------|------|
| FoundationStereo | `ghcr.io/wangxinjian1108/foundationstereo` | 12.4 | 2.4.1 | [arXiv:2501.09898](https://arxiv.org/abs/2501.09898) | 立体匹配基础模型，CVPR 2025 Oral (Best Paper Nomination) |
| colmap | `ghcr.io/wangxinjian1108/colmap` | 12.6 | latest | [CVPR 2016](https://demuc.de/papers/schoenberger2016sfm.pdf) | Structure-from-Motion 和 Multi-View Stereo 管道 |
| hierarchical-3d-gaussians | `ghcr.io/wangxinjian1108/hierarchical-3d-gaussians` | 11.8 | 2.0.1 | [SIGGRAPH 2024](https://repo-sam.inria.fr/fungraph/hierarchical-3d-gaussians/) | 层次化 3D 高斯表示，超大规模场景实时渲染 |
| lingbot-map | `ghcr.io/wangxinjian1108/lingbot-map` | 12.8 | 2.8.0 | [arXiv:2604.14141](https://arxiv.org/abs/2604.14141) | 语言引导的建图方法 |
| LoGeR | `ghcr.io/wangxinjian1108/loger` | 12.6 | 2.6.0 | [arXiv:2603.03269](https://arxiv.org/abs/2603.03269) | 长上下文几何重建，混合记忆机制 |
| map-anything | `ghcr.io/wangxinjian1108/map-anything` | 12.6 | latest | [arXiv:2509.13414](https://arxiv.org/abs/2509.13414) | 通用语义建图 (Meta Research) |
| Pi3 | `ghcr.io/wangxinjian1108/pi3` | 12.4 | 2.5.1 | [arXiv:2507.13347](https://arxiv.org/abs/2507.13347) | 可扩展的置换等变视觉几何学习 |
| Pi-Long | `ghcr.io/wangxinjian1108/pi-long` | 11.8 | 2.5.1 | 无独立论文，参考 [VGGT-Long](https://arxiv.org/abs/2507.16443) + [Pi3](https://arxiv.org/abs/2507.13347) | 基于 VGGT-Long 和 Pi3 的长序列重建 |
| sam3 | `ghcr.io/wangxinjian1108/sam3` | 12.8 | 2.10.0 | [arXiv:2511.16719](https://arxiv.org/abs/2511.16719) | Segment Anything with Concepts (Meta AI) |
| Scal3R | `ghcr.io/wangxinjian1108/scal3r` | 12.8 | latest | [arXiv:2604.08542](https://arxiv.org/abs/2604.08542) | 可扩展 3D 重建，CVPR 2026 Highlight |
| StreamVGGT | `ghcr.io/wangxinjian1108/streamvggt` | 12.1 | 2.3.1 | [arXiv:2507.11539](https://arxiv.org/abs/2507.11539) | 实时流式 4D 视觉几何感知 |
| vggt | `ghcr.io/wangxinjian1108/vggt` | 12.1 | 2.3.1 | [arXiv:2503.11651](https://arxiv.org/abs/2503.11651) | Visual Geometry Grounded Transformer (Oxford VGG + Meta AI) |
| VGGT-Long | `ghcr.io/wangxinjian1108/vggt-long` | 11.8 | 2.5.1 | [arXiv:2507.16443](https://arxiv.org/abs/2507.16443) | 将 VGGT 扩展到公里级长 RGB 序列 |
| vggt-omega | `ghcr.io/wangxinjian1108/vggt-omega` | 12.6 | 2.6.0 | [arXiv:2605.15195](https://arxiv.org/abs/2605.15195) | VGGT-Ω：前馈式相机与深度重建 (Oxford VGG + Meta AI), CVPR 2026 |
| ZipMap | `ghcr.io/wangxinjian1108/zipmap` | 12.6 | 2.6.0 | [arXiv:2603.04385](https://arxiv.org/abs/2603.04385) | 线性时间有状态 3D 重建 (Google Research) |

共 15 个镜像，14 篇独立论文。
