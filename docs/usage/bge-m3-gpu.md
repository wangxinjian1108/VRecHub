# BGE-M3 GPU 使用与推理指南

GPU 镜像：

```text
ghcr.io/wangxinjian1108/bge-m3-gpu:latest
```

CPU 镜像见 [bge-m3.md](bge-m3.md)。

## 1. 环境

- CUDA base：12.4.1 cuDNN runtime。
- PyTorch：`2.6.0+cu124`。
- 默认设备：`cuda`。
- 默认精度：FP16。
- 模型：`BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181`。
- 权重位置：`/models/bge-m3`。

主机需要 NVIDIA Container Toolkit，并且 GPU 显存建议不少于 4 GB。

检查 GPU：

```bash
nvidia-smi

docker run --rm --gpus all \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest \
  python3 -c "import torch; print(torch.cuda.is_available(), torch.version.cuda, torch.cuda.get_device_name(0))"
```

预期输出类似：

```text
True 12.4 NVIDIA L4
```

## 2. 启动服务

```bash
docker run --rm -d \
  --name bge-m3-gpu \
  --gpus all \
  --shm-size=8g \
  -p 8000:8000 \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest
```

健康检查：

```bash
curl -sS http://127.0.0.1:8000/health
```

返回示例：

```json
{
  "status": "ok",
  "model": "BAAI/bge-m3",
  "device": "cuda",
  "fp16": true
}
```

如果没有通过 `--gpus all` 暴露 GPU，容器会在模型初始化阶段直接失败。
不会再出现“健康检查通过但推理时发现 CUDA 不可用”的情况。

## 3. GPU 推理自检

```bash
docker run --rm --gpus all \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest \
  python3 /app/gpu-smoke-test.py
```

该测试会实际执行 dense、sparse 和 ColBERT 三种 GPU embedding。

## 4. HTTP API

请求格式与 CPU 镜像相同：

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": [
      "A person pushes a suitcase.",
      "行人推动一个行李箱。"
    ],
    "max_length": 512
  }'
```

Sparse：

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": ["multilingual text retrieval"],
    "return_sparse": true,
    "max_length": 512
  }'
```

ColBERT：

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": ["A short passage."],
    "return_colbert_vecs": true,
    "max_length": 256
  }'
```

CPU 和 GPU 镜像返回相同的 dense 1024 维向量、sparse lexical weights 和
ColBERT token vectors。

## 5. CLI

```bash
docker run --rm --gpus all \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest \
  bge-m3-embed \
  'A person pushes a suitcase.' \
  '行人推动一个行李箱。' \
  --max-length 512
```

同时返回 sparse 和 ColBERT：

```bash
docker run --rm --gpus all \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest \
  bge-m3-embed \
  'multilingual retrieval' \
  --sparse \
  --colbert \
  --max-length 256
```

## 6. 参数

| 环境变量 | GPU 镜像默认值 | 说明 |
| --- | --- | --- |
| `BGE_M3_DEVICE` | `cuda` | CUDA 设备 |
| `BGE_M3_USE_FP16` | `true` | 启用 FP16 |
| `BGE_M3_BATCH_SIZE` | `16` | 默认 batch size |
| `BGE_M3_MAX_LENGTH` | `8192` | 默认最大 token 数 |
| `BGE_M3_MAX_TEXTS` | `128` | 单次请求文本上限 |
| `BGE_M3_PORT` | `8000` | HTTP 端口 |

显存不足时可以降低：

```bash
-e BGE_M3_BATCH_SIZE=4
-e BGE_M3_MAX_LENGTH=1024
```

指定其他 GPU：

```bash
docker run --rm --gpus '"device=1"' \
  -e BGE_M3_DEVICE=cuda:0 \
  ghcr.io/wangxinjian1108/bge-m3-gpu:latest
```

容器内看到的第一个可见 GPU 仍然是 `cuda:0`。

## 7. CPU / GPU 选择

- 中小吞吐、没有 GPU：使用 `bge-m3:latest`。
- 批量编码、需要低延迟：使用 `bge-m3-gpu:latest`。
- 多副本部署时应根据显存、最大 token 长度和 batch size 评估并发。

## 8. 验证记录

本次 GitHub Actions 构建镜像：

```text
ghcr.io/wangxinjian1108/bge-m3-gpu:latest
digest: sha256:d183bb60792b260f68e5ca2c0485e2b6b43428645210a113782d0a00152ceb20
```

已在 NVIDIA L4 上完成：

- `torch.cuda.is_available() == true`。
- PyTorch 编译 CUDA 版本为 12.4。
- Dense、sparse 和 ColBERT GPU embedding 全部通过。
- GPU HTTP `/health` 和 `/embed` 请求通过。
- 中文文本返回 1024 维 embedding，L2 范数约为 1。
