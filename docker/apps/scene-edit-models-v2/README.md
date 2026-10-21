# scene-edit-models-v2

`scene-edit-models-v1` + GVHMR 推理环境 + Motion2MixamoRig。

## 镜像内容

| 组件 | Conda 环境 | 路径 | 说明 |
| --- | --- | --- | --- |
| SkinTokens / Qwen3-VL / Blender | `skintokens`, `qwen3-vl` | 继承自 v1 | 与 v1 完全相同 |
| GVHMR 研究代码 | `gvhmr` (Python 3.10) | `/app/GVHMR` | `hmr4d` 包，torch 2.3.0+cu121 |
| Motion2MixamoRig | `m2mr` (Python 3.11) | `/app/Motion2MixamoRig` | 依赖 PyPI `gvhmr>=1.6` |

两个 GVHMR 相关环境分开：仓库版是研究代码（`import hmr4d`），
Motion2MixamoRig 依赖的是 PyPI 上重构后的 `gvhmr>=1.6` 包，二者不能共用一个环境。

## 权重和资产

镜像不预置任何模型权重：

- GVHMR 权重放到 `/app/GVHMR/inputs/checkpoints/`（挂载）。
- Motion2MixamoRig 首次 `m2mr run` 会自动下载约 5 GB 权重到
  `/app/Motion2MixamoRig/weights/`；SMPL-X 和 Mixamo FBX 需要用户自备，
  分别放到 `assets/body_models/smplx/SMPLX_NEUTRAL.npz` 和 `assets/mixamo/`。

```bash
docker run --rm -it --gpus all --shm-size=8g \
  -v /host/m2mr/assets:/app/Motion2MixamoRig/assets \
  -v /host/m2mr/weights:/app/Motion2MixamoRig/weights \
  -v /host/m2mr/outputs:/app/Motion2MixamoRig/outputs \
  ghcr.io/wangxinjian1108/scene-edit-models-v2:latest
```

## 用法

```bash
m2mr doctor
m2mr run --video assets/video/clip.mp4 --rig assets/mixamo/Y_Bot.fbx

gvhmr-demo --video /data/clip.mp4 -s
```

`m2mr` / `gvhmr-demo` 是封装脚本，会自动切到对应 conda 环境。
