# scene-edit-models-v4

聚合镜像：在 `scene-edit-models-v3` 的基础上加入 **TRELLIS.2**。

| 组件 | Conda 环境 | 说明 |
| --- | --- | --- |
| SkinTokens / Qwen3-VL / Blender | `skintokens`, `qwen3-vl` | 继承 v1 |
| GVHMR / Motion2MixamoRig | `gvhmr`, `m2mr` | 继承 v2 |
| Kimodo | `kimodo` | 继承 v3 |
| TRELLIS.2 | `trellis2` | torch 2.6.0+cu124 + flash-attn / nvdiffrast / nvdiffrec / CuMesh / FlexGEMM / o-voxel |

TRELLIS.2 权重（`microsoft/TRELLIS.2-4B`，约 24GB 显存需求）不在镜像内，
首次运行从 HuggingFace 下载或挂载缓存。

```bash
docker run --rm -it --gpus all --shm-size=8g \
  -v /host/hf-cache:/root/.cache/huggingface \
  ghcr.io/wangxinjian1108/scene-edit-models-v4:latest

# 容器内
trellis2-python example.py --help
```
