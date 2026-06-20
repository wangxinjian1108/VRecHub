# sam3-train — 训练镜像

**状态**: 已批准，待实现
**日期**: 2026-06-20

## 1. 目标

提供 `ghcr.io/wangxinjian1108/sam3-train` 镜像，在现有 `sam3:latest` 基础上叠加 sam3 的 `[train]` extras（hydra-core / submitit / tensorboard / zstandard / scipy / torchmetrics / fvcore / fairscale / scikit-image / scikit-learn）。镜像同时具备推理与训练能力（推理来自继承的 base，训练来自新增 extras）。

产出 tag：
- `ghcr.io/wangxinjian1108/sam3-train:latest` — runtime，CMD = `bash`
- `ghcr.io/wangxinjian1108/sam3-train:dev` — dev 层（s6 + SSH + JupyterLab）

## 2. 仓库布局

```
docker/sam3-train/
├── Dockerfile        # FROM sam3:latest + [train] extras
└── Dockerfile.dev    # FROM sam3-train:latest + s6+SSH+Jupyter (复用模板)
.github/workflows/
└── docker-sam3-train.yml
docs/superpowers/specs/
└── 2026-06-20-sam3-train-design.md
```

`docker/sam3-train/` 与 `docker/sam3/` 平级，是单 repo 镜像族下的派生镜像。命名约定：当一个 repo 需要多种 image variant 时（推理 vs 训练 vs 其他），用 `<repo>-<variant>` 子目录。

## 3. Base 镜像

`ghcr.io/wangxinjian1108/sam3:latest`

由 `docker-sam3.yml` 维护和发布。`sam3-train` 不重做 CUDA / conda / sam3 源码编辑安装这些重活，全部继承自上游。

依赖于 base 镜像意味着：上游修改时（pyproject、CUDA、torch 等），`sam3-train` 必须 rebuild 才能跟上。这通过 workflow_run 串联自动处理（见 §6）。

## 4. 镜像内容

继承自 base：
- CUDA 12.8.1 + Python 3.12 + torch 2.10.0+cu128 + torchvision 0.25.0
- conda env `sam3` + flash-attn-3
- sam3 源码于 `/sam3`（editable 安装；upstream `docker/sam3/Dockerfile` 用 `WORKDIR /sam3` + `COPY thirdparty/sam3 .`）
- 已装的 sam3 extras: `[notebooks]`
- 权重于 `/opt/var/models/sam3`（构建时通过 HF_TOKEN 下载好）

新增：
- sam3 `[train]` extras 的 10 个包

权重不变 —— `[train]` 不带任何额外模型下载。如果训练需要其他 checkpoint，运行时挂载。

## 5. Runtime Dockerfile

```dockerfile
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/sam3:latest
FROM ${BASE_IMAGE}

RUN cd /sam3 && conda run -n sam3 pip install --no-cache-dir -e ".[train]"

CMD ["/bin/bash"]
```

`cd /sam3 && pip install -e ".[train]"` —— pip 不接受 `pip install <abs-path>[extra]`（解析成 path glob），也不接受 `pip install -e <abs-path>[extra]`（拒绝 "not a valid editable requirement"）。需要先 `cd` 进源码目录，再用相对 `.` 调用，这是 upstream `docker/sam3/Dockerfile` 已验证的写法。

## 6. CI workflow

`docker-sam3-train.yml` 关键差异（与现有 docker-sam3.yml 对比）：

```yaml
on:
  workflow_run:
    workflows: ["Docker – sam3"]
    types: [completed]
    branches: [master]
  push:
    branches: [master]
    paths:
      - "docker/sam3-train/**"
      - ".github/workflows/docker-sam3-train.yml"
  pull_request:
    branches: [master]
    paths:
      - "docker/sam3-train/**"
      - ".github/workflows/docker-sam3-train.yml"
  workflow_dispatch:

jobs:
  build-and-push:
    if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      # 不需要 init 任何 submodule —— 镜像不 COPY 任何 thirdparty 源码
      - name: Free disk space
        run: |
          ...
      - name: Set up Docker Buildx
        ...
      # Login Docker Hub / GHCR
      # docker metadata for runtime
      # Set runtime base tag
      # Build runtime image (file: docker/sam3-train/Dockerfile, no hf_token)
      # docker metadata for dev
      # Build dev image (file: docker/sam3-train/Dockerfile.dev)
```

要点：
- `workflow_run` 触发的 job 必须显式 `if` 检查 `conclusion == 'success'`（GHA 默认即使上游失败也会触发）
- `paths` filter 不含 `thirdparty/sam3`：源码改动由 `docker-sam3.yml` 触发，传导过来
- runtime build 不需要 `hf_token`（权重在 base 中已 baked）
- checkout 用 `actions/checkout@v4` 后**不**做 `git submodule update`（这个 image 完全不需要 submodule）
- 镜像名空间：`ghcr.io/wangxinjian1108/sam3-train` + `${{ secrets.DOCKERHUB_USERNAME }}/sam3-train`

## 7. Dockerfile.dev

`Dockerfile.dev` 严格复用现有模板（s6-overlay + SSH + JupyterLab + jovyan + root password ShARC），仅改 `ARG BASE_IMAGE` 默认指向 `ghcr.io/wangxinjian1108/sam3-train:latest`。

## 8. 运行示例

```bash
# 拉镜像
docker pull ghcr.io/wangxinjian1108/sam3-train:latest

# 跑训练（数据挂载、权重已自带）
docker run --gpus all --rm -it \
  -v /path/to/dataset:/data \
  -v /path/to/exp_output:/output \
  ghcr.io/wangxinjian1108/sam3-train:latest \
  bash -lc "cd /sam3 && python -m train ..."

# dev（SSH+Jupyter，长跑训练 + 调参）
docker run --gpus all -d \
  -p 2222:22 -p 8888:8888 \
  -v /path/to/dataset:/data \
  ghcr.io/wangxinjian1108/sam3-train:dev
```

## 9. 不在范围内

- `[dev]` extras（pytest / black / ruff —— 不属于训练运行依赖）
- 多机分布式所需的额外系统包（MPI / NCCL CLI 工具，单机训练用不上；future task）
- 训练入口脚本封装（`docker run` 直接 bash + 用户命令组合）
- 权重打包（base 已自带 sam3.1 权重；其他 ckpt 由运行时挂载）

## 10. 验收标准

- `docker pull ghcr.io/wangxinjian1108/sam3-train:latest` 成功
- 镜像内 `conda run -n sam3 python -c "import hydra, submitit, fvcore, fairscale, torchmetrics; print('train deps ok')"` 通过
- 镜像内 `conda run -n sam3 python -c "import torch, sam3; print('inference still ok')"` 通过（推理能力保留）
- `:dev` 镜像可 SSH（root:ShARC）+ JupyterLab(:8888)
- `docker-sam3.yml` 跑完成功后，`docker-sam3-train.yml` 自动触发并最终成功
