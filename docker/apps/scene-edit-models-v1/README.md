# scene-edit-models-v1

场景编辑聚合镜像：SkinTokens + Qwen3-VL + 独立 Blender 程序。
两个模型只安装源码和依赖，**不包含模型权重，也不在构建时下载模型配置**。

| 组件 | 环境 / 路径 | 版本 |
| --- | --- | --- |
| CUDA 基础环境 | Ubuntu 22.04 | CUDA 12.8.1 + cuDNN |
| SkinTokens | Conda `skintokens`，`/app/skintokens` | Python 3.11、PyTorch 2.7.0、Transformers 4.57.6 |
| Qwen3-VL | Conda `qwen3-vl`，`/app/qwen3-vl` | Python 3.11、PyTorch 2.8.0、Transformers 4.57.6、vLLM 0.11.0 |
| Blender | `/opt/blender/blender`，已加入 PATH | 4.5.3；SkinTokens 的 `bpy` 同版本 |

## 构建与拉取

构建上下文为仓库根目录。对应 Actions workflow 为
`.github/workflows/docker-scene-edit-models-v1.yml`，支持 master 路径触发、版本 tag、PR 和手动触发。
发布 runtime 镜像的 `latest` 和 `sha-<commit>` 标签；PR 只构建。

```bash
docker build -f docker/apps/scene-edit-models-v1/Dockerfile -t scene-edit-models-v1 .
docker pull ghcr.io/wangxinjian1108/scene-edit-models-v1:latest
docker run --rm -it --gpus all --shm-size=8g \
  -v /path/to/models:/opt/var/models \
  -v /path/to/work:/workspace \
  ghcr.io/wangxinjian1108/scene-edit-models-v1:latest
```

容器默认进入 Bash，通过 `conda activate skintokens` 或 `conda activate qwen3-vl` 切换环境。
也可以直接用 `conda run --no-capture-output -n <环境名> ...`。

## SkinTokens 权重挂载

按照 SkinTokens 的 `download.py --model` 在外部准备文件，并将两个目录分别挂到源码的预期位置：

```bash
docker run --rm --gpus all --shm-size=8g \
  -v /path/to/skintokens/experiments:/app/skintokens/experiments:ro \
  -v /path/to/skintokens/models:/app/skintokens/models:ro \
  -v /path/to/work:/workspace \
  -w /app/skintokens \
  ghcr.io/wangxinjian1108/scene-edit-models-v1:latest \
  conda run --no-capture-output -n skintokens python demo.py \
    --input /workspace/input.glb --output /workspace/rigged.glb
```

`experiments/` 需要包含 TokenRig 和 SkinVAE 的 checkpoint；
`models/Qwen3-0.6B/` 需要包含上游下载脚本准备的配置文件。

## Qwen3-VL 与 Blender

将所需 Qwen3-VL 权重挂载到 `/opt/var/models/qwen3-vl`，在 Python 中通过该路径加载，
或在容器内启动 vLLM：

```bash
conda run --no-capture-output -n qwen3-vl vllm serve /opt/var/models/qwen3-vl
blender --background --python /workspace/edit_scene.py
```

Blender 使用自身内置的 Python；要在模型环境中操作 Blender API，可用
`conda run -n skintokens python your_script.py` 并在脚本里 `import bpy`。

## 验证

`scene-edit-smoke-test` 在构建时自动执行，也可在容器内重新运行。
它检查两套环境的导入、PyTorch CPU 运算和 Blender 后台创建网格；无需 GPU 或模型权重。
实际模型推理需要额外挂载权重并提供 NVIDIA GPU。
