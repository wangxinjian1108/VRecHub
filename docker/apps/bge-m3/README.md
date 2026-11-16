# BGE-M3 CPU 推理镜像

小型 CPU-only BGE-M3 embedding 镜像，内置官方 PyTorch 权重，支持：

- Dense embedding，1024 维。
- Sparse lexical weights。
- ColBERT multi-vector embedding。
- 默认 HTTP 推理服务。
- `bge-m3-embed` 命令行入口。

镜像通过 [GitHub Actions](../../../.github/workflows/docker-bge-m3.yml) 构建：

```text
ghcr.io/wangxinjian1108/bge-m3:latest
```

模型版本固定为 `BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181`。
镜像只包含 PyTorch 推理所需文件，不包含仓库中的 ONNX、示例图片等冗余资产。

快速启动：

```bash
docker run --rm -p 8000:8000 \
  ghcr.io/wangxinjian1108/bge-m3:latest
```

请求 embedding：

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": ["A person pushes a suitcase.", "行人推动一个行李箱。"],
    "max_length": 512
  }'
```

完整接口、CLI 和部署说明见
[BGE-M3 使用与推理指南](../../../docs/usage/bge-m3.md)。
