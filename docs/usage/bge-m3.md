# BGE-M3 使用与推理指南

本文档对应 CPU-only BGE-M3 独立推理镜像：

```text
ghcr.io/wangxinjian1108/bge-m3:latest
```

镜像内置 `BAAI/bge-m3` 的 PyTorch 权重，无需运行时下载模型，也不需要
vLLM、GPU 或 NVIDIA Container Toolkit。

## 1. 支持能力

BGE-M3 可以返回三种表示：

- Dense embedding：1024 维归一化向量，适合向量数据库和语义检索。
- Sparse lexical weights：按 token 的稀疏权重，适合词汇匹配和混合检索。
- ColBERT multi-vector：每个 token 的 1024 维向量，适合 late interaction 重排。

默认 HTTP 接口只返回 dense embedding，以控制响应体和 CPU 计算量。Sparse 和
ColBERT 可以按请求开启。

## 2. 镜像内容

| 内容 | 路径 |
| --- | --- |
| 模型权重 | `/models/bge-m3` |
| 模型服务 | `/app/server.py` |
| CLI | `bge-m3-embed` |
| 服务入口 | `bge-m3-server` |
| 默认端口 | `8000` |

模型固定为：

```text
BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181
```

镜像只包含 PyTorch 推理所需资产，不包含 ONNX 模型、示例图片和其他无关文件。
权重约为 2.3 GB，建议容器至少有 8 GB 内存。

## 3. 拉取与启动

```bash
docker pull ghcr.io/wangxinjian1108/bge-m3:latest

docker run --rm -d \
  --name bge-m3 \
  -p 8000:8000 \
  ghcr.io/wangxinjian1108/bge-m3:latest
```

健康检查：

```bash
curl -sS http://127.0.0.1:8000/health
```

返回：

```json
{"status":"ok","model":"BAAI/bge-m3"}
```

查看模型信息：

```bash
curl -sS http://127.0.0.1:8000/info
```

## 4. HTTP API

### 4.1 只生成 dense embedding

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

返回：

```json
{
  "model": "BAAI/bge-m3",
  "count": 2,
  "dense_dimension": 1024,
  "dense_vecs": [[...], [...]]
}
```

### 4.2 Sparse weights

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": ["multilingual text retrieval"],
    "return_dense": true,
    "return_sparse": true,
    "max_length": 512
  }'
```

返回会额外包含：

```json
{
  "lexical_weights": [
    {
      "multi": 0.12,
      "text": 0.08
    }
  ]
}
```

实际 token 和权值由模型生成。

### 4.3 ColBERT vectors

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": ["A short passage."],
    "return_dense": true,
    "return_colbert_vecs": true,
    "max_length": 256
  }'
```

ColBERT 返回形状为 `(token 数, 1024)` 的向量。长文本开启 ColBERT 会产生很大的
JSON 响应，批量服务中通常建议关闭 HTTP 返回，改为在应用内直接调用模型。

### 4.4 单条文本

`text` 是 `texts` 的单条快捷写法：

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello world","max_length":128}'
```

### 4.5 请求字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `texts` | `list[str]` | 必填 | 每批最多 128 条 |
| `text` | `str` | 无 | 单条文本快捷方式 |
| `return_dense` | `bool` | `true` | 返回 1024 维 dense vector |
| `return_sparse` | `bool` | `false` | 返回 lexical weights |
| `return_colbert_vecs` | `bool` | `false` | 返回 token vectors |
| `batch_size` | `int` | 环境配置，默认 8 | 单次内部 batch 大小 |
| `max_length` | `int` | 8192 | 最大 token 数，范围 1–8192 |

HTTP 请求体最大 16 MiB。

## 5. 命令行推理

生成 dense embedding：

```bash
docker run --rm \
  ghcr.io/wangxinjian1108/bge-m3:latest \
  bge-m3-embed \
  'A person pushes a suitcase.' \
  '行人推动一个行李箱。' \
  --max-length 512
```

输出为 JSON。

同时生成 sparse 和 ColBERT：

```bash
docker run --rm \
  ghcr.io/wangxinjian1108/bge-m3:latest \
  bge-m3-embed \
  'multilingual text retrieval' \
  --sparse \
  --colbert \
  --max-length 256
```

从文件读取，每行一条文本，并写入 JSON：

```bash
docker run --rm \
  -v "$PWD:/work" \
  ghcr.io/wangxinjian1108/bge-m3:latest \
  bge-m3-embed \
  --input /work/corpus.txt \
  --output /work/embeddings.json \
  --max-length 512 \
  --sparse
```

从标准输入读取：

```bash
printf 'first text\nsecond text\n' | \
docker run --rm -i \
  ghcr.io/wangxinjian1108/bge-m3:latest \
  bge-m3-embed --input -
```

## 6. 运行参数

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BGE_M3_MODEL_PATH` | `/models/bge-m3` | 本地模型路径 |
| `BGE_M3_DEVICE` | `cpu` | 当前 CPU 镜像只支持 `cpu` |
| `BGE_M3_BATCH_SIZE` | `8` | 默认 batch size |
| `BGE_M3_MAX_LENGTH` | `8192` | 默认最大 token 数 |
| `BGE_M3_MAX_TEXTS` | `128` | 单次请求文本上限 |
| `BGE_M3_PORT` | `8000` | HTTP 端口 |
| `OMP_NUM_THREADS` | `4` | CPU 推理线程数 |

CPU 推理时，`max_length=8192` 会显著增加延迟和内存。普通段落检索建议从
`512` 或 `1024` 开始；只有确实需要长文档时才使用更大值。

## 7. Docker Compose 示例

```yaml
services:
  bge-m3:
    image: ghcr.io/wangxinjian1108/bge-m3:latest
    ports:
      - "8000:8000"
    environment:
      BGE_M3_BATCH_SIZE: "8"
      BGE_M3_MAX_LENGTH: "1024"
      OMP_NUM_THREADS: "8"
    restart: unless-stopped
```

## 8. 输出使用建议

### Dense

把 `dense_vecs` 写入 pgvector、Milvus、Qdrant、FAISS 或其他向量索引。
向量已经归一化，可以使用 cosine similarity 或 inner product。

### Sparse

把 `lexical_weights` 保存为 token 到权重的映射，与 dense 分数做加权混合。
适合精确术语、编号、人名和跨语言关键词检索。

### ColBERT

`colbert_vecs` 是每个 token 的向量，存储量远高于 dense。通常用于候选集重排，
不建议把完整 ColBERT 向量作为 HTTP JSON 批量传输到下游服务。

## 9. 安全与部署

- 服务默认监听 `0.0.0.0:8000`，镜像内没有鉴权。
- 仅在内网或受控网关后暴露；公网部署时应在反向代理层增加鉴权、限流和 TLS。
- CPU 推理适合中小吞吐和异步任务；高 QPS 或多副本场景应横向扩容。
- 镜像不包含 GPU PyTorch，不支持 `BGE_M3_DEVICE=cuda`。

## 10. 常见问题

### 容器启动后立即退出

查看日志：

```bash
docker logs bge-m3
```

首次启动需要加载约 2.3 GB 权重，耐心等待健康检查通过。

### 内存不足

降低：

```text
BGE_M3_BATCH_SIZE
BGE_M3_MAX_LENGTH
```

并减少同时运行的服务副本。

### 响应过大

关闭 `return_colbert_vecs`，按需要开启 `return_sparse`。Dense-only 响应最小。

### 想要 GPU 加速

当前镜像为了控制体积使用 CPU-only PyTorch。GPU 版本需要改用 CUDA 基础镜像和
对应 PyTorch wheel，可另建 `bge-m3-gpu` 镜像。
