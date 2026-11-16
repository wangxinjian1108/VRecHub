# BGE-M3 GPU 推理镜像

基于 CUDA 12.4 和 PyTorch 2.5.1 cu124 的 BGE-M3 GPU 推理镜像。

```text
ghcr.io/wangxinjian1108/bge-m3-gpu:latest
```

与 CPU 镜像使用相同的模型、HTTP API 和 CLI；差异是：

- PyTorch 编译包含 CUDA 12.4。
- 默认 `BGE_M3_DEVICE=cuda`。
- 默认启用 FP16。
- 启动时如果没有可用 GPU，会直接失败，避免健康检查误报。

启动：

```bash
docker run --rm -d --name bge-m3-gpu \
  --gpus all -p 8000:8000 \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest
```

GPU 推理验证：

```bash
docker run --rm --gpus all \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest \
  python3 /app/gpu-smoke-test.py
```

完整说明见
[BGE-M3 GPU 使用指南](../../../docs/usage/bge-m3-gpu.md)。
