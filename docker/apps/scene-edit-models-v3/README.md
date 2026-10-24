# scene-edit-models-v3

`scene-edit-models-v2` + Kimodo。

| 组件 | Conda 环境 | 路径 |
| --- | --- | --- |
| SkinTokens / Qwen3-VL / Blender | `skintokens`, `qwen3-vl` | 继承自 v1 |
| GVHMR / Motion2MixamoRig | `gvhmr`, `m2mr` | 继承自 v2 |
| Kimodo | `kimodo` (Python 3.10) | `/app/kimodo` |

Kimodo 依赖 `transformers==5.1.0`、torch 2.5.1+cu124，与 v2 中的其他环境互不干扰。
镜像不预置模型权重，Kimodo 权重从 HuggingFace `nvidia/Kimodo-*` 下载或挂载缓存。

```bash
docker run --rm -it --gpus all --shm-size=8g \
  -v /host/hf-cache:/root/.cache/huggingface \
  ghcr.io/wangxinjian1108/scene-edit-models-v3:latest

kimodo-gen --help
```
