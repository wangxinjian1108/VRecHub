# BGE-M3 Embedding 与相似度检索服务指南

本文说明如何把现有的 BGE-M3 embedding 镜像用于文本向量化，以及如何扩展成
“用户输入 prompt，与数据库中的 N 条 embedding 计算相似度并返回结果”的检索
服务。

## 1. 结论

当前已经交付的 CPU/GPU 镜像是**无状态 embedding 推理服务**：

- 输入一条或多条文本。
- 用镜像内置的 `BAAI/bge-m3` 生成 dense 向量。
- 可选生成 sparse lexical weights 和 ColBERT token vectors。
- 默认返回 1024 维 dense embedding。
- 不包含业务数据库、向量索引、`/search` 接口或结果排序逻辑。

因此，它可以直接作为检索系统的“向量生成器”，但还不能单独完成
`prompt -> 与 N 个向量比较 -> 返回 top-k`。

可以做成一个 `bge-m3-search` 服务镜像，但建议采用下面的组件划分：

```text
用户 prompt
    |
    v
Search API（新增服务镜像）
    |
    +--> BGE-M3 /embed（现有 CPU 或 GPU 镜像）
    |
    +--> pgvector / Qdrant / Milvus / FAISS（向量存储）
    |
    v
按相似度降序返回 top-k 结果
```

推荐先实现 dense-only 的检索链路。BGE-M3 的 sparse 和 ColBERT 适合后续增加
混合检索或重排，不建议第一版就把全部 ColBERT token vectors 放进 HTTP 响应。

## 2. 先使用现有 BGE-M3 镜像

### 2.1 CPU 镜像

```bash
docker pull repo-volc.zelostech.com.cn/zcloud/bge-m3:latest

docker run --rm -d \
  --name bge-m3 \
  -p 8000:8000 \
  repo-volc.zelostech.com.cn/zcloud/bge-m3:latest
```

### 2.2 GPU 镜像

GPU 主机需要安装 NVIDIA Container Toolkit：

```bash
docker pull repo-volc.zelostech.com.cn/zcloud/bge-m3-gpu:latest

docker run --rm -d \
  --name bge-m3-gpu \
  --gpus all \
  --shm-size=8g \
  -p 8000:8000 \
  repo-volc.zelostech.com.cn/zcloud/bge-m3-gpu:latest
```

检查服务：

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/info
```

GPU 镜像的 `/health` 应包含 `"device":"cuda"`。如果没有传入 `--gpus all`，GPU
镜像会在模型初始化时失败，而不会在 CUDA 不可用的情况下继续处理请求。

完整的启动参数和接口说明见：

- [CPU BGE-M3 使用指南](bge-m3.md)
- [GPU BGE-M3 使用指南](bge-m3-gpu.md)

### 2.3 生成一维 query embedding

```bash
curl -sS http://127.0.0.1:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "一个人推着黑色行李箱",
    "max_length": 512
  }'
```

返回结构：

```json
{
  "model": "BAAI/bge-m3",
  "count": 1,
  "dense_dimension": 1024,
  "dense_vecs": [[0.0123, -0.0045, "... 共 1024 个数 ..."]]
}
```

服务端批量编码时，应一次提交多条文本，例如：

```json
{
  "texts": [
    "行李箱的黑色顶部把手",
    "银色金属直杆",
    "婴儿车把手"
  ],
  "batch_size": 16,
  "max_length": 512
}
```

不要为数据库中的每一行单独发起一次 `/embed` 请求。批量请求可以显著降低
HTTP、Python 和 GPU 调度开销。

## 3. 查询 N 条 embedding 的两种实现方式

### 3.1 小规模 N：应用内存中的精确计算

当 N 很小，例如几千条到几万条，并且更新频率较低时，可以把预先计算好的
embedding 放在进程内存中：

```python
import numpy as np

query = np.asarray(query_embedding, dtype=np.float32)
matrix = np.asarray(all_embeddings, dtype=np.float32)  # shape: (N, 1024)

# BGE-M3 输出已经归一化时，点积等价于 cosine similarity。
scores = matrix @ query
top_k = min(requested_top_k, len(scores))
indices = np.argsort(-scores)[:top_k]
```

这里的 `query_embedding` 和 `all_embeddings` 必须由同一个 BGE-M3 模型和同一
套预处理参数生成。应用仍应调用 BGE-M3，不能使用其他编码器临时生成 query
向量后再与 BGE-M3 索引混合。

这种方式简单、结果精确，但 N 增大后会占用大量内存，并且每次查询都要扫描
全部向量。N 达到几十万或以上时，应改用向量索引。

### 3.2 中大规模 N：数据库或向量索引

常用方案如下：

| 方案 | 适合场景 | 优点 | 注意点 |
| --- | --- | --- | --- |
| PostgreSQL + pgvector | 已有 PostgreSQL，N 为中等规模 | 事务、元数据过滤和向量查询统一 | 需要安装 `vector` 扩展，索引和表一起维护 |
| Qdrant | 独立向量检索服务 | 过滤、快照和多租户能力较清晰 | 多一个有状态服务 |
| Milvus | 大规模、数据增长较快 | 横向扩展能力强 | 运维复杂度较高 |
| FAISS | 固定离线数据或单进程小服务 | 部署简单、查询快 | 索引更新、持久化和多副本需要自行处理 |

如果只是为现有业务加一个 prompt 搜索接口，优先推荐 PostgreSQL + pgvector。
如果已经有向量数据库，直接复用现有基础设施即可，不需要为了本项目另建一套。

## 4. 推荐的整体服务方案

### 4.1 推荐：Embedding 服务与 Search API 分开

```text
                    +--------------------------+
prompt -----------> | bge-m3-search            |
                    | FastAPI / your API       |
                    +------------+-------------+
                                 |
                    POST /embed  |  1. 生成 query embedding
                                 v
                    +--------------------------+
                    | bge-m3-cpu or bge-m3-gpu |
                    | 现有 embedding 镜像       |
                    +--------------------------+
                                 |
                                 | 1024-d float32 vector
                                 v
                    +--------------------------+
                    | PostgreSQL + pgvector    |
                    | 或 Qdrant / Milvus       |
                    +--------------------------+
                                 |
                                 | top-k id、score、payload
                                 v
                              用户
```

这种拆分最适合生产：

- BGE-M3 GPU 服务可以独立扩缩容。
- 数据库和索引由数据库团队维护。
- Search API 只负责鉴权、参数校验、召回和返回格式。
- 更换索引或增加 sparse/ColBERT 重排时，不需要重建整个模型镜像。

`bge-m3-search` 本身可以做成独立镜像，数据库不应放进同一个容器。容器只保存
连接配置，数据库通过外部服务、持久化 volume 或托管服务提供。

### 4.2 可选：一个聚合镜像

也可以构建一个包含 BGE-M3、FastAPI 和 pgvector/Qdrant 客户端的镜像：

```text
bge-m3-search:latest
    = BGE-M3 模型 + Search API + 向量数据库客户端
```

它适合演示、单机小规模部署和离线批处理，但上线时仍建议把 PostgreSQL 或
Qdrant 放在独立容器/服务中。原因是索引需要持久化，数据库升级、备份和扩容
也不应该与模型进程绑定。

如果希望镜像体积和维护成本较低，可以基于现有镜像增加一个 Search API 层：

```dockerfile
FROM ghcr.io/wangxinjian1108/bge-m3-gpu:latest

# 这里复制新增的 search API 代码和数据库客户端依赖。
# 模型权重和 BGE-M3 HTTP 服务沿用 base image。
COPY docker/apps/bge-m3-search/app /app/search
COPY docker/apps/bge-m3-search/requirements.txt /app/search/requirements.txt

WORKDIR /app/search
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

正式镜像仍应通过 GitHub Actions 构建，使用仓库中的 Dockerfile，由 workflow
登录 GHCR 后构建并推送；如果还需要发布到 Zelos，再由同一 workflow 登录 Zelos
并推送同一个镜像。可以在 Zelos 侧使用 `skopeo copy` 或 `docker buildx imagetools`
复制已构建的 multi-platform manifest。搜索服务的数据库密码和连接串应通过部署
环境的 secret 注入，不能写入 Dockerfile 或镜像层。

## 5. 建议的 Search API

### 5.1 查询接口

```http
POST /search
Content-Type: application/json
```

请求：

```json
{
  "prompt": "一个人推着黑色行李箱",
  "top_k": 10,
  "filters": {
    "category": "suitcase"
  }
}
```

字段建议：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `prompt` | `string` | 查询文本，必须限制长度 |
| `top_k` | `integer` | 返回数量，建议限制为 1–100 |
| `filters` | `object` | 可选的业务元数据过滤条件 |
| `max_length` | `integer` | 可选，必须与入库配置一致，建议固定为 512 |

返回：

```json
{
  "query": "一个人推着黑色行李箱",
  "model": "BAAI/bge-m3",
  "model_revision": "5617a9f61b028005a4858fdac845db406aefb181",
  "results": [
    {
      "id": "asset-123",
      "score": 0.8921,
      "payload": {
        "category": "suitcase",
        "source": "mesh-library"
      }
    }
  ],
  "took_ms": 18
}
```

`score` 建议统一为“越大越相似”。如果数据库返回的是距离，应在 API 层转换，
避免调用方需要理解 `<=>`、`<#>` 等运算符的差异。

### 5.2 入库接口

入库和查询必须使用同一套向量配置。建议提供一个批量导入接口：

```http
POST /index/upsert
Content-Type: application/json
```

```json
{
  "documents": [
    {
      "id": "asset-123",
      "text": "黑色行李箱，顶部有可伸缩拉杆和黑色把手",
      "metadata": {
        "category": "suitcase"
      }
    },
    {
      "id": "asset-456",
      "text": "银色金属长杆，适合行人手持",
      "metadata": {
        "category": "pole"
      }
    }
  ]
}
```

服务内部应先批量调用 BGE-M3 `/embed`，再把 `id`、原文、embedding 和 metadata
一次性写入数据库。重复写入同一个 `id` 时使用 upsert，保证更新不会产生重复
记录。

## 6. PostgreSQL + pgvector 落地示例

### 6.1 建表

假设 BGE-M3 返回归一化的 1024 维 dense vector，pgvector 的 `vector(1024)`
可以直接存储；部署前应确认当前 pgvector 版本支持该维度的 HNSW 索引。

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_embeddings (
    id          text PRIMARY KEY,
    content     text NOT NULL,
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    embedding   vector(1024) NOT NULL,
    model_name  text NOT NULL,
    model_revision text NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- 数据稳定后创建 HNSW 索引。没有足够数据时先不建，避免写入变慢。
CREATE INDEX IF NOT EXISTS document_embeddings_embedding_hnsw
    ON document_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

如果已确认向量全部做了 L2 归一化，也可以使用 inner-product 索引：

```sql
CREATE INDEX document_embeddings_embedding_ip
    ON document_embeddings
    USING hnsw (embedding vector_ip_ops);
```

不同索引类型的距离运算符必须与查询对应；生产环境不要在同一列上同时创建多种
索引来“试探”，应先根据数据规模和 benchmark 选择一种。

### 6.2 写入向量

向量必须以参数传给数据库，不能拼接 SQL 字符串：

```python
# 伪代码
embedding = call_bge_m3(text, max_length=512)

cursor.execute(
    """
    INSERT INTO document_embeddings
        (id, content, metadata, embedding, model_name, model_revision)
    VALUES (%s, %s, %s::jsonb, %s::vector, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        content = EXCLUDED.content,
        metadata = EXCLUDED.metadata,
        embedding = EXCLUDED.embedding,
        model_name = EXCLUDED.model_name,
        model_revision = EXCLUDED.model_revision,
        updated_at = now()
    """,
    (
        document_id,
        text,
        json.dumps(metadata, ensure_ascii=False),
        embedding,
        "BAAI/bge-m3",
        MODEL_REVISION,
    ),
)
```

批量导入时应使用事务或批量 upsert，并限制每批大小，避免一次性占满模型显存、
数据库连接和网络带宽。

### 6.3 查询 top-k

使用 cosine distance 的示例：

```sql
SELECT
    id,
    metadata,
    1 - (embedding <=> %s::vector) AS score
FROM document_embeddings
WHERE (%s::jsonb = '{}'::jsonb OR metadata @> %s::jsonb)
ORDER BY embedding <=> %s::vector
LIMIT %s;
```

其中：

- `<=>` 是 pgvector 的 cosine distance。
- `1 - distance` 得到越大越相似的 cosine score。
- 参数化 `top_k`，不要直接拼接用户输入。
- metadata 过滤条件要在服务端做字段白名单和参数化，不能把客户端 JSON 当成
  SQL 片段执行。

如果 N 很小，也可以不用 ANN 索引，直接做 exact scan；如果 N 很大，应先
用 `EXPLAIN ANALYZE` 验证索引是否生效。

## 7. Search API 的业务流程

一个请求的推荐处理顺序：

1. 校验 prompt 非空、长度不超过配置上限。
2. 校验 `top_k`、filters 和请求频率。
3. 调用 BGE-M3 生成 query dense embedding。
4. 在 pgvector/Qdrant 中执行一次 top-k 查询。
5. 把距离转换为统一 score，并附上 ID 和业务 payload。
6. 记录耗时、模型版本、索引版本；不要记录完整敏感 prompt，除非有明确的审计策略。

搜索服务不应为 N 条记录分别调用 BGE-M3；数据库中的 embedding 应在入库时
预计算，query 每次只计算一次。

## 8. CPU / GPU 选择

- 没有 GPU、请求量不大：使用 `bge-m3:latest`，配合异步队列或批处理。
- 需要较低单次延迟或批量编码：使用 `bge-m3-gpu:latest`。
- GPU 部署必须使用 `--gpus all`，并根据显存设置 `BGE_M3_BATCH_SIZE` 和
  `BGE_M3_MAX_LENGTH`。
- CPU 与 GPU 镜像应固定同一个模型 revision；入库时记录模型版本，查询时检查
  索引的模型版本是否与当前服务一致。
- 不建议把 CPU 和 GPU 生成的向量无标记地混在同一个索引里。即使 dense 维度
  相同，也应以同一模型、revision、归一化方式和 max-length 配置为准。

## 9. 相似度、混合检索和 ColBERT

第一版建议只使用 dense 1024 维向量：

```text
BGE-M3 dense embedding -> pgvector cosine similarity -> top-k
```

后续可以按以下顺序增强：

1. 用 sparse lexical weights 做关键词召回，与 dense 结果加权融合。
2. 对 dense/sparse 召回的较小候选集使用 ColBERT late interaction 重排。
3. 只用 ColBERT 处理 top 50–200 个候选，不要把全库 ColBERT vectors 通过 HTTP
   传给下游。

Sparse 权重对编号、名称和精确词更有效；ColBERT 的质量收益通常要用更高存储
和延迟换取。是否启用应由离线评测决定。

## 10. 推荐部署形态

### 模式 A：现有镜像 + 外部数据库（推荐）

```text
bge-m3 / bge-m3-gpu  (现有镜像)
        +
bge-m3-search        (新增 Search API 镜像)
        +
PostgreSQL + pgvector / Qdrant / Milvus
```

适合生产使用。数据库连接使用部署环境的 secret，索引数据落在数据库持久化
存储中。

### 模式 B：Search API 镜像内使用 FAISS

适合固定的中小数据集：

```text
bge-m3-search:latest
    ├── BGE-M3
    ├── FAISS 索引
    └── FastAPI
```

优点是部署简单；缺点是索引更新、快照、重建和多副本一致性需要自行实现。容器
重建前必须把 FAISS index 和 ID 映射放到持久化目录。

### 模式 C：纯离线批处理

用现有 CPU/GPU 镜像和 `bge-m3-embed` 批量生成 JSON embedding，然后把结果导入
数据库或离线计算文件。这个模式适合一次性构建数据集，不是在线搜索服务。

## 11. 安全与运维注意事项

当前 embedding 镜像没有内置鉴权、TLS 和限流，不能直接暴露到公网。生产部署至少应：

- 在 API 网关或 Search API 层增加身份认证和 per-user rate limit。
- 限制 prompt 最大长度、`top_k`、filters 的字段和值域。
- 为 BGE-M3 和数据库查询设置超时，并区分 `400/422/429/503`。
- 不在日志中输出完整 prompt、用户 token 或数据库连接串。
- 不要把模型权重、数据库密码或 Zelos 凭据写进 Dockerfile、镜像层或 Git。
- 对 pgvector/Qdrant 做备份、版本升级演练和索引重建流程。
- 在索引 metadata 中保存 `model_name`、`model_revision`、`dense_dimension`、
  `normalized`、`max_length`，防止模型升级后新旧向量混用。
- 监控 embedding 延迟、数据库查询延迟、top-k 空结果率、QPS、GPU 显存和
  错误率。

## 12. 最小验收建议

上线前至少验证：

- 同一个文本在 CPU/GPU 各自生成 1024 维 vector。
- 查询向量和入库向量来自同一模型 revision。
- N=1、N=100、N=10,000 时 top-k 顺序正确。
- 重复 upsert 不会产生重复记录。
- `top_k` 和 `prompt` 超限返回明确错误。
- 数据库故障时 Search API 返回可识别的 `503`，不会误报成功。
- GPU 镜像没有 GPU 时直接失败，CPU 镜像不会尝试加载 CUDA。
- 索引重建期间旧服务仍可查询，切换后分数和结果稳定。

## 13. 实施顺序

建议按以下顺序实现：

1. 保留现有 `bge-m3` 和 `bge-m3-gpu` 镜像作为 embedding 服务。
2. 新增 `docker/apps/bge-m3-search/`，实现 `/health`、`/search` 和
   `/index/upsert`。
3. 先接 PostgreSQL + pgvector，只存储 dense vector 和基础 metadata。
4. 用固定测试集校验入库、更新、查询和重复写入。
5. 再评估 sparse、ColBERT 混合检索，以及 Qdrant/Milvus 的迁移需求。
6. 继续通过 GitHub Actions 构建 `bge-m3-search` 镜像并推送到 GHCR 和 Zelos。

这样既能复用已经验证的 BGE-M3 权重和推理环境，又能把数据库连接、业务过滤
和检索策略放在可控的 Search API 层，不需要把 N 条向量或模型权重塞进用户请求
或模型服务的响应中。
