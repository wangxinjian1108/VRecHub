# human-motion-gen-v1

四个文本/交互驱动的人体动作生成模型，各自独立 conda 环境：

| 模型 | 环境 | 路径 | 关键版本 |
| --- | --- | --- | --- |
| HY-Motion 1.0 | `hy-motion` (Python 3.10) | `/app/HY-Motion-1.0` | torch 2.5.1 / transformers 4.53.3 / diffusers 0.26.3 |
| ARDY | `ardy` (Python 3.11) | `/app/ardy` | torch 2.5.1 cu124 / transformers 5.8.1 |
| Kimodo | `kimodo` (Python 3.10) | `/app/kimodo` | torch 2.5.1 cu124 / transformers 5.1.0 |
| DART | `dart` (Python 3.8) | `/app/DART` | torch 2.1 cu118 / pytorch3d 0.7.5 |

三个模型的 `transformers` 分别是 4.53.3 / 5.8.1 / 5.1.0，DART 还需要 Python 3.8
和 torch 2.1，因此无法合并环境；DART 使用仓库自带的 `environment.yml`。

## 权重

镜像不预置任何权重，模型首次运行/手动下载后挂载到对应目录：

- HY-Motion：`/app/HY-Motion-1.0/ckpts/`
- ARDY：按 README 下载后放到 `/app/ardy/ckpts/`（或 `HF_HOME` 缓存）
- Kimodo：HuggingFace `nvidia/Kimodo-*`，建议挂载 `HF_HOME`
- DART：`/app/DART/` 下的 checkpoint 与 `data/` 目录

```bash
docker run --rm -it --gpus all --shm-size=8g \
  -v /host/hy-motion-ckpts:/app/HY-Motion-1.0/ckpts \
  -v /host/hf-cache:/root/.cache/huggingface \
  ghcr.io/wangxinjian1108/human-motion-gen-v1:latest
```

## 用法

```bash
hy-motion-infer --model_path ckpts/tencent/HY-Motion-1.0
ardy-generate "A person walks in a circle." --model soma
kimodo-gen --help

conda run -n dart python -m ...   # DART 按仓库 demos/ 使用
```
